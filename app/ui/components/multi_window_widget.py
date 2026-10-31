"""Multi-Window Bot Widget: 3-window simultaneous game monitor and analyzer on macOS."""

from __future__ import annotations
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import cv2
import numpy as np
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.automation.gesture_manager import AutoBinhWorker, GestureManager
from app.automation.move_planner import MovePlanner
from app.core.card import Card
from app.core.collaborative_analyzer import (
    CollaborativeTableAnalyzer,
    CollaborativeTableResult,
    WindowCounterStrategy,
)
from app.core.solver import HandArrangement, Solver
from app.services.multi_window_service import MultiWindowWorker
from app.services.vision_service import recognize_cards_pipeline
from app.ui.components.card_reference_manager import CardReferenceManagerDialog
from app.ui.components.card_widget import CardWidget
from app.ui.components.zoomable_viewer import ZoomableImageViewer
from app.vision.card_detector import CardDetector
from app.vision.card_recognizer import CardRecognizer
from app.vision.card_reference_library import CardReferenceLibrary
from app.vision.card_state import CardStateManager, WindowCardState
from app.vision.roi_manager import WindowROI
from app.vision.screen_capture import ScreenCapture
from app.vision.window_manager import WindowItem, WindowManager


class SingleWindowPanel(QGroupBox):
    """Panel displaying live camera ROI, detected cards, and optimal 3-chi arrangement for one game window."""

    auto_binh_clicked = Signal(int)

    def __init__(self, window_idx: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(f"Cửa sổ #{window_idx}", parent)
        self.window_idx = window_idx
        self.last_partition: Optional[HandArrangement] = None
        self.last_detected_cards: List[Any] = []
        self.last_frame: Optional[np.ndarray] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header status badge
        header = QHBoxLayout()
        self.lbl_status = QLabel("Chưa kết nối")
        self.lbl_status.setStyleSheet("color: #8E8E93; font-weight: 600; font-size: 11px;")
        header.addWidget(self.lbl_status)
        header.addStretch()

        self.lbl_round_badge = QLabel("Ván: —")
        self.lbl_round_badge.setStyleSheet(
            "color: #8E8E93; font-weight: bold; font-size: 11px; background: rgba(142,142,147,0.15); padding: 2px 6px; border-radius: 4px;"
        )
        header.addWidget(self.lbl_round_badge)
        layout.addLayout(header)

        # Live Image Viewer
        self.viewer = ZoomableImageViewer()
        self.viewer.setMinimumHeight(180)
        self.viewer.setMaximumHeight(240)
        layout.addWidget(self.viewer)

        # Detected Cards Scroll Area
        lbl_detected = QLabel("Lá bài phát hiện:")
        lbl_detected.setStyleSheet("font-size: 11px; color: #8E8E93;")
        layout.addWidget(lbl_detected)

        self.scroll_cards = QScrollArea()
        self.scroll_cards.setFixedHeight(85)
        self.scroll_cards.setWidgetResizable(True)
        self.scroll_cards.setStyleSheet("background: #141414; border: none; border-radius: 4px;")
        self.cards_container = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(4)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll_cards.setWidget(self.cards_container)
        layout.addWidget(self.scroll_cards)

        # Recommendation / Solver Result Area
        self.box_solution = QGroupBox("Gợi ý xếp bài tối ưu")
        self.box_solution.setStyleSheet("font-size: 11px;")
        sol_layout = QVBoxLayout(self.box_solution)
        sol_layout.setSpacing(4)
        sol_layout.setContentsMargins(6, 6, 6, 6)

        self.lbl_chi_front = QLabel("Chi Đầu (3 lá): —")
        self.lbl_chi_middle = QLabel("Chi Giữa (5 lá): —")
        self.lbl_chi_back = QLabel("Chi Cuối (5 lá): —")

        for lbl in (self.lbl_chi_front, self.lbl_chi_middle, self.lbl_chi_back):
            lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
            sol_layout.addWidget(lbl)

        layout.addWidget(self.box_solution)

        # Matchup / Counter-strategy box vs deduced 4th opponent
        self.box_vs_opp = QGroupBox("⚔️ Khắc chế đối thủ #4")
        self.box_vs_opp.setStyleSheet("font-size: 11px;")
        opp_box_layout = QVBoxLayout(self.box_vs_opp)
        opp_box_layout.setSpacing(2)
        opp_box_layout.setContentsMargins(6, 6, 6, 6)

        self.lbl_opp_outcome = QLabel("Đang chờ đủ 3 cửa sổ...")
        self.lbl_opp_outcome.setStyleSheet("font-size: 11px; font-weight: 600; color: #8E8E93;")
        self.lbl_opp_breakdown = QLabel("—")
        self.lbl_opp_breakdown.setStyleSheet("font-size: 10px; color: #A0A0A0;")

        opp_box_layout.addWidget(self.lbl_opp_outcome)
        opp_box_layout.addWidget(self.lbl_opp_breakdown)
        layout.addWidget(self.box_vs_opp)

        # Auto-Binh Action Button
        self.btn_auto_binh = QPushButton("⚡ Tự Động Binh Bài (Auto-Binh)", objectName="PrimaryBtn")
        self.btn_auto_binh.setStyleSheet("background-color: #30D158; color: white; font-weight: bold; border-radius: 6px; padding: 6px 12px;")
        self.btn_auto_binh.setEnabled(False)
        self.btn_auto_binh.setToolTip("Tự động dùng chuột kéo xếp 13 lá bài theo thế bài tối ưu")
        self.btn_auto_binh.clicked.connect(lambda: self.auto_binh_clicked.emit(self.window_idx))
        layout.addWidget(self.btn_auto_binh)

    def update_state(self, state: WindowCardState, crop_img: Optional[np.ndarray]) -> None:
        """Updates live preview and card list."""
        self.last_detected_cards = list(state.detected_cards)
        if state.status == "OCCLUDED":
            self.lbl_status.setText("⚠️ Cửa sổ bị che (Occluded)")
            self.lbl_status.setStyleSheet("color: #FF453A; font-weight: 600;")
        elif state.status == "MOVED_NO_RECALCULATE":
            self.lbl_status.setText(f"✓ {len(state.detected_cards)} lá (Bài di chuyển - Không tính lại)")
            self.lbl_status.setStyleSheet("color: #0A84FF; font-weight: 600;")
        elif state.status == "CONFIRMED_13" or len(state.detected_cards) == 13:
            self.lbl_status.setText("★ Đủ 13 lá bài — Đã tối ưu")
            self.lbl_status.setStyleSheet("color: #30D158; font-weight: 600;")
        elif len(state.detected_cards) > 0:
            self.lbl_status.setText(f"Đang phát hiện: {len(state.detected_cards)} lá (Cần 13 lá)")
            self.lbl_status.setStyleSheet("color: #FF9F0A; font-weight: 600;")
        else:
            self.lbl_status.setText("Đang theo dõi cửa sổ (Chưa thấy bài)")
            self.lbl_status.setStyleSheet("color: #8E8E93; font-weight: 600;")

        if crop_img is not None and crop_img.size > 0:
            self.last_frame = crop_img
            self.viewer.set_image(crop_img, state.detected_cards)

        # Update card thumbnails
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.hide()
                w.deleteLater()

        for det in state.detected_cards:
            w = CardWidget(card=det.card, width=36, height=52, selectable=False)
            self.cards_layout.addWidget(w)
        self.cards_layout.addStretch()

    def update_solution(self, partition: HandArrangement) -> None:
        """Displays solved 3-chi hand breakdown."""
        self.last_partition = partition
        self.btn_auto_binh.setEnabled(partition is not None and len(self.last_detected_cards) == 13)

        f_names = " ".join(c.unicode_name for c in partition.front)
        m_names = " ".join(c.unicode_name for c in partition.middle)
        b_names = " ".join(c.unicode_name for c in partition.back)

        f_type = partition.front_eval.description
        m_type = partition.middle_eval.description
        b_type = partition.back_eval.description

        self.lbl_chi_front.setText(f"Chi Đầu: {f_names} ({f_type})")
        self.lbl_chi_middle.setText(f"Chi Giữa: {m_names} ({m_type})")
        self.lbl_chi_back.setText(f"Chi Cuối: {b_names} ({b_type})")

    def update_counter_strategy(self, strat: WindowCounterStrategy) -> None:
        """Updates matchup display and arrangement vs Opponent."""
        self.update_solution(strat.optimal_arrangement)
        self.lbl_opp_outcome.setText(strat.outcome_summary)
        self.lbl_opp_breakdown.setText(strat.chi_breakdown)

        if strat.matchup.is_scoop:
            self.lbl_opp_outcome.setStyleSheet("font-size: 11px; font-weight: 700; color: #30D158;")
            self.box_solution.setTitle("Gợi ý xếp bài (🏆 Thế bài BẮT SẬP đối thủ)")
        elif strat.matchup.total_points > 0:
            self.lbl_opp_outcome.setStyleSheet("font-size: 11px; font-weight: 700; color: #0A84FF;")
            self.box_solution.setTitle("Gợi ý xếp bài (✓ Khắc chế thắng đối thủ)")
        elif strat.matchup.is_scooped:
            self.lbl_opp_outcome.setStyleSheet("font-size: 11px; font-weight: 700; color: #FF453A;")
            self.box_solution.setTitle("Gợi ý xếp bài tối ưu")
        else:
            self.lbl_opp_outcome.setStyleSheet("font-size: 11px; font-weight: 600; color: #FF9F0A;")
            self.box_solution.setTitle("Gợi ý xếp bài tối ưu")

    def set_round(self, round_num: int, is_new: bool = False, is_completed: bool = False) -> None:
        """Updates round badge visual indicator for this window."""
        if is_new:
            self.lbl_round_badge.setText(f"Ván #{round_num} (MỚI)")
            self.lbl_round_badge.setStyleSheet(
                "color: #64D2FF; font-weight: bold; font-size: 11px; background: rgba(100,210,255,0.22); padding: 2px 6px; border-radius: 4px; border: 1px solid #64D2FF;"
            )
        elif is_completed:
            self.lbl_round_badge.setText(f"Ván #{round_num} (Đã binh)")
            self.lbl_round_badge.setStyleSheet(
                "color: #30D158; font-weight: bold; font-size: 11px; background: rgba(48,209,88,0.22); padding: 2px 6px; border-radius: 4px;"
            )
        else:
            self.lbl_round_badge.setText(f"Ván #{round_num}")
            self.lbl_round_badge.setStyleSheet(
                "color: #FF9F0A; font-weight: bold; font-size: 11px; background: rgba(255,159,10,0.18); padding: 2px 6px; border-radius: 4px;"
            )


class OpponentDeductionPanel(QGroupBox):
    """Visual panel displaying deduced 13 cards of Opponent (Player 4) and team counter-strategy."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("🎯 ĐỐI THỦ — NHÀ THỨ 4 (13 LÁ SUY LUẬN TỪ BỘ BÀI 52 CÂY)", parent)
        self.setStyleSheet("""
            QGroupBox {
                background-color: #1A1A1C;
                border: 1px solid #3A3A3C;
                border-radius: 8px;
                font-weight: 600;
                font-size: 12px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                color: #FFD60A;
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
        """)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 8, 10, 8)

        # Header status bar
        self.lbl_status = QLabel("Chưa phát hiện đủ bài: Hãy kết nối 3 cửa sổ game để hệ thống suy luận 13 lá đối thủ.")
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #8E8E93;")
        layout.addWidget(self.lbl_status)

        # Content split: Left (13 cards thumbnails), Right (Opponent 3-chi breakdown)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # Left: Opponent Cards Scroll Area
        left_box = QVBoxLayout()
        lbl_cards = QLabel("13 Quân bài đối thủ đang cầm (Loại trừ từ 3 cửa sổ):")
        lbl_cards.setStyleSheet("font-size: 11px; color: #A0A0A0; font-weight: 500;")
        left_box.addWidget(lbl_cards)

        self.scroll_cards = QScrollArea()
        self.scroll_cards.setFixedHeight(65)
        self.scroll_cards.setWidgetResizable(True)
        self.scroll_cards.setStyleSheet("background: #141414; border: 1px solid #2C2C2E; border-radius: 4px;")
        self.cards_container = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(3)
        self.cards_layout.setContentsMargins(4, 2, 4, 2)
        self.scroll_cards.setWidget(self.cards_container)
        left_box.addWidget(self.scroll_cards)
        content_layout.addLayout(left_box, 3)

        # Right: Opponent optimal arrangement
        right_box = QVBoxLayout()
        lbl_opp_sol = QLabel("Thế bài tối ưu nhất đối thủ sẽ xếp:")
        lbl_opp_sol.setStyleSheet("font-size: 11px; color: #A0A0A0; font-weight: 500;")
        right_box.addWidget(lbl_opp_sol)

        self.lbl_chi_front = QLabel("Chi Đầu (3 lá): —")
        self.lbl_chi_middle = QLabel("Chi Giữa (5 lá): —")
        self.lbl_chi_back = QLabel("Chi Cuối (5 lá): —")

        for lbl in (self.lbl_chi_front, self.lbl_chi_middle, self.lbl_chi_back):
            lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #FFFFFF;")
            right_box.addWidget(lbl)

        content_layout.addLayout(right_box, 2)
        layout.addLayout(content_layout)

    def update_result(self, result: CollaborativeTableResult) -> None:
        """Updates opponent deduced cards, arrangement, and team strategy summary."""
        self.lbl_status.setText(result.summary_message)

        if result.cross_duplicates:
            self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #FF453A;")
        elif result.is_opponent_fully_deduced:
            self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 700; color: #30D158;")
        else:
            self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #FF9F0A;")

        # Update opponent cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.hide()
                w.deleteLater()

        for card in result.remaining_cards:
            w = CardWidget(card=card, width=32, height=48, selectable=False)
            self.cards_layout.addWidget(w)
        self.cards_layout.addStretch()

        # Update opponent optimal arrangement
        if result.opponent_best_arrangement is not None:
            part = result.opponent_best_arrangement
            f_names = " ".join(c.unicode_name for c in part.front)
            m_names = " ".join(c.unicode_name for c in part.middle)
            b_names = " ".join(c.unicode_name for c in part.back)

            self.lbl_chi_front.setText(f"Chi Đầu: {f_names} ({part.front_eval.description})")
            self.lbl_chi_middle.setText(f"Chi Giữa: {m_names} ({part.middle_eval.description})")
            self.lbl_chi_back.setText(f"Chi Cuối: {b_names} ({part.back_eval.description})")
        else:
            self.lbl_chi_front.setText("Chi Đầu (3 lá): —")
            self.lbl_chi_middle.setText("Chi Giữa (5 lá): —")
            self.lbl_chi_back.setText("Chi Cuối (5 lá): —")


class MultiWindowWidget(QWidget):
    """Widget orchestrating simultaneous 3-window game detection on macOS."""

    def __init__(
        self,
        detector: Optional[CardDetector] = None,
        recognizer: Optional[CardRecognizer] = None,
        reference_library: Optional[CardReferenceLibrary] = None,
        gesture_manager: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.window_manager = WindowManager()
        self.reference_library = reference_library or (recognizer.reference_library if recognizer else CardReferenceLibrary())
        self.detector = detector or CardDetector()
        self.recognizer = recognizer or CardRecognizer(reference_library=self.reference_library)
        from app.automation.gesture_manager import GestureManager
        self.gesture_manager = gesture_manager or GestureManager()
        self.solver = Solver()
        self.table_analyzer = CollaborativeTableAnalyzer()
        self.window_cards: Dict[int, List[Card]] = {1: [], 2: [], 3: []}
        self._last_table_hash: Optional[tuple] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[MultiWindowWorker] = None
        self.discovered_windows: List[WindowItem] = []
        self._auto_binh_workers: Dict[int, Any] = {}
        self._pending_alternating_windows: List[int] = []

        # Round Tracking & Continuous Auto-Loop state
        self.is_auto_loop_enabled: bool = False
        self.window_round_counters: Dict[int, int] = {1: 0, 2: 0, 3: 0}
        self.last_binned_hashes: Dict[int, str] = {1: "", 2: "", 3: ""}
        self.window_stable_hashes: Dict[int, Tuple[str, int]] = {1: ("", 0), 2: ("", 0), 3: ("", 0)}
        self.window_current_hashes: Dict[int, str] = {1: "", 2: "", 3: ""}
        self.is_auto_binh_executing: bool = False
        self.auto_loop_queue: List[int] = []
        self.total_binned_rounds: int = 0

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Top Control Bar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.btn_refresh_wins = QPushButton("🔄 Quét cửa sổ macOS", objectName="SecondaryBtn")
        self.btn_refresh_wins.clicked.connect(self._refresh_window_list)
        toolbar.addWidget(self.btn_refresh_wins)

        toolbar.addWidget(QLabel("Cửa sổ 1:"))
        self.combo_w1 = QComboBox()
        self.combo_w1.currentIndexChanged.connect(lambda: self._on_window_selected(1))
        toolbar.addWidget(self.combo_w1)

        toolbar.addWidget(QLabel("Cửa sổ 2:"))
        self.combo_w2 = QComboBox()
        self.combo_w2.currentIndexChanged.connect(lambda: self._on_window_selected(2))
        toolbar.addWidget(self.combo_w2)

        toolbar.addWidget(QLabel("Cửa sổ 3:"))
        self.combo_w3 = QComboBox()
        self.combo_w3.currentIndexChanged.connect(lambda: self._on_window_selected(3))
        toolbar.addWidget(self.combo_w3)

        self.btn_ref_manager = QPushButton("📚 Thư viện ảnh mẫu", objectName="SecondaryBtn")
        self.btn_ref_manager.setToolTip("Quản lý 52 lá bài và các ảnh mẫu đã xác nhận")
        self.btn_ref_manager.clicked.connect(self._open_reference_manager)
        toolbar.addWidget(self.btn_ref_manager)

        toolbar.addStretch()

        self.lbl_fps = QLabel("FPS: —")
        self.lbl_fps.setStyleSheet("color: #30D158; font-weight: 600; padding: 4px 8px; background: rgba(48,209,88,0.12); border-radius: 4px;")
        toolbar.addWidget(self.lbl_fps)

        self.btn_start = QPushButton("▶ Bắt đầu quét 3 cửa sổ")
        self.btn_start.setFixedHeight(32)
        self.btn_start.clicked.connect(self._toggle_bot)
        toolbar.addWidget(self.btn_start)

        self.btn_auto_binh_all = QPushButton("⚡ Binh bài cả 3 bàn (Luân phiên)")
        self.btn_auto_binh_all.setFixedHeight(32)
        self.btn_auto_binh_all.setStyleSheet(
            "background-color: #5E5CE6; color: white; font-weight: bold; padding: 4px 12px; border-radius: 6px;"
        )
        self.btn_auto_binh_all.setToolTip(
            "Tự động luân phiên xếp bài trên cả 3 cửa sổ/tab: Hoàn tất bàn 1 -> chuyển bàn 2 -> chuyển bàn 3"
        )
        self.btn_auto_binh_all.clicked.connect(self._on_auto_binh_all_clicked)
        toolbar.addWidget(self.btn_auto_binh_all)

        self.btn_auto_loop = QPushButton("🔄 Tự động binh liên tục: TẮT")
        self.btn_auto_loop.setFixedHeight(32)
        self.btn_auto_loop.setStyleSheet(
            "background-color: #3A3A3C; color: #E5E5EA; font-weight: bold; padding: 4px 12px; border-radius: 6px;"
        )
        self.btn_auto_loop.setToolTip(
            "BẬT/TẮT chế độ tự động chạy liên tục: Tự động phát hiện ván bài mới và xếp bài liên tục ván này qua ván khác trên cả 3 bàn"
        )
        self.btn_auto_loop.clicked.connect(self._toggle_auto_loop)
        toolbar.addWidget(self.btn_auto_loop)

        self.lbl_loop_counter = QLabel("Đã binh: 0 ván")
        self.lbl_loop_counter.setStyleSheet(
            "color: #FF9F0A; font-weight: bold; font-size: 11px; padding: 4px 8px; background: rgba(255,159,10,0.12); border-radius: 4px;"
        )
        toolbar.addWidget(self.lbl_loop_counter)

        main_layout.addLayout(toolbar)

        # 3 Side-by-side or Grid Panels
        grid = QGridLayout()
        grid.setSpacing(10)

        self.panels: Dict[int, SingleWindowPanel] = {}
        for i in range(1, 4):
            panel = SingleWindowPanel(window_idx=i, parent=self)
            panel.auto_binh_clicked.connect(self._on_auto_binh_clicked)
            self.panels[i] = panel
            grid.addWidget(panel, 0, i - 1)

        main_layout.addLayout(grid)

        # Deduced Opponent & Collaborative Counter-Strategy Panel
        self.opponent_panel = OpponentDeductionPanel(parent=self)
        main_layout.addWidget(self.opponent_panel)

        # Initial window scan
        self._refresh_window_list()

    def _refresh_window_list(self) -> None:
        """Finds on-screen windows and populates combo boxes."""
        self.discovered_windows = self.window_manager.list_windows()
        for combo in (self.combo_w1, self.combo_w2, self.combo_w3):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("-- Chọn cửa sổ game --", None)
            for win in self.discovered_windows:
                combo.addItem(win.display_label, win.window_id)
            combo.blockSignals(False)

    def _open_reference_manager(self) -> None:
        """Opens Card Reference Library Manager dialog to manage confirmed card templates."""
        dlg = CardReferenceManagerDialog(reference_library=self.reference_library, parent=self)
        if dlg.exec():
            self.reference_library.reload_cache()

    def _on_window_selected(self, window_idx: int) -> None:
        """Immediately captures the selected window, verifies it, displays it in live preview,
        detects cards, and shows optimal solution if available."""
        combo = [self.combo_w1, self.combo_w2, self.combo_w3][window_idx - 1]
        wid = combo.currentData()
        panel = self.panels.get(window_idx)
        if not panel:
            return

        if not wid:
            panel.lbl_status.setText("Chưa kết nối")
            panel.lbl_status.setStyleSheet("color: #8E8E93; font-weight: 600; font-size: 11px;")
            return

        match = next((w for w in self.discovered_windows if w.window_id == wid), None)
        win_title = match.title or match.owner_name if match else f"Cửa sổ #{wid}"

        # Capture selected window directly
        img = ScreenCapture.capture_window_by_id(wid)
        if img is None or img.size == 0:
            panel.lbl_status.setText(f"⚠️ Không thể chụp [{win_title}] (Đã đóng/Thu nhỏ)")
            panel.lbl_status.setStyleSheet("color: #FF453A; font-weight: 600;")
            return

        # Run Unified Card Recognition Pipeline (identical to Tab 2 Quét màn hình CV)
        detected_cards, _ = recognize_cards_pipeline(
            img,
            detector=self.detector,
            recognizer=self.recognizer,
        )

        # Create WindowCardState
        state = WindowCardState(
            window_id=window_idx,
            detected_cards=detected_cards,
            status=f"DETECTED_{len(detected_cards)}_CARDS",
        )
        panel.update_state(state, img)

        # Check for 13 unique cards
        valid_cards: List[Card] = []
        seen_codes = set()
        for d in sorted(detected_cards, key=lambda x: x.confidence, reverse=True):
            if d.card is not None and d.card_code not in seen_codes:
                seen_codes.add(d.card_code)
                valid_cards.append(d.card)
                if len(valid_cards) == 13:
                    break

        self.window_cards[window_idx] = valid_cards

        if len(valid_cards) == 13:
            try:
                arrangements = self.solver.solve_heuristic(valid_cards)
                if arrangements:
                    panel.update_solution(arrangements[0])
                    panel.lbl_status.setText(f"✓ Đã xác nhận [{win_title}]: 13 lá — Đã có gợi ý tối ưu")
                    panel.lbl_status.setStyleSheet("color: #30D158; font-weight: 600;")
                else:
                    panel.lbl_status.setText(f"✓ Đã xác nhận [{win_title}]: 13 lá — Không tìm thấy bộ hợp lệ")
                    panel.lbl_status.setStyleSheet("color: #FF9F0A; font-weight: 600;")
            except Exception as e:
                panel.lbl_status.setText(f"Lỗi tính toán: {e}")
                panel.lbl_status.setStyleSheet("color: #FF453A; font-weight: 600;")
        elif detected_cards:
            panel.lbl_status.setText(f"✓ Đã kết nối [{win_title}]: Phát hiện {len(detected_cards)} lá (Cần 13 lá)")
            panel.lbl_status.setStyleSheet("color: #0A84FF; font-weight: 600;")
        else:
            panel.lbl_status.setText(f"✓ Đã kết nối [{win_title}]: Đang chờ chia bài...")
            panel.lbl_status.setStyleSheet("color: #FF9F0A; font-weight: 600;")

        # Run table-wide collaborative deduction & counter-strategy
        self._evaluate_table_strategy()

    def _toggle_bot(self) -> None:
        if self._worker and self._worker._is_running:
            self._stop_bot()
        else:
            self._start_bot()

    def _start_bot(self) -> None:
        # Collect chosen ROIs
        rois: List[WindowROI] = []
        combos = [self.combo_w1, self.combo_w2, self.combo_w3]

        for idx, combo in enumerate(combos, start=1):
            wid = combo.currentData()
            if wid:
                # Find matching window
                match = next((w for w in self.discovered_windows if w.window_id == wid), None)
                if match:
                    rois.append(
                        WindowROI(
                            window_id=idx,
                            name=match.title or match.owner_name,
                            bounds_pts=match.bounds,
                            titlebar_inset_pts=28,
                            is_active=True,
                            cg_window_id=match.window_id,
                        )
                    )

        if not rois:
            QMessageBox.warning(self, "Chưa chọn cửa sổ", "Vui lòng chọn ít nhất 1 cửa sổ game để bắt đầu.")
            return

        self.btn_start.setText("⏹ Dừng quét")
        self.btn_start.setStyleSheet("background-color: #FF453A;")
        self.btn_refresh_wins.setEnabled(False)

        self._thread = QThread()
        self._worker = MultiWindowWorker(
            rois=rois,
            detector=self.detector,
            recognizer=self.recognizer,
            poll_interval_sec=0.15,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.start_loop)
        self._worker.frame_processed.connect(self._on_frame_processed)
        self._worker.solution_found.connect(self._on_solution_found)
        self._worker.fps_updated.connect(lambda fps: self.lbl_fps.setText(f"FPS: {fps}"))

        self._thread.start()

    def _stop_bot(self) -> None:
        if self._worker:
            self._worker.stop_loop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

        self._worker = None
        self._thread = None
        self.btn_start.setText("▶ Bắt đầu quét 3 cửa sổ")
        self.btn_start.setStyleSheet("")
        self.btn_refresh_wins.setEnabled(True)
        self.lbl_fps.setText("FPS: —")
        self.is_auto_binh_executing = False
        self.auto_loop_queue.clear()
        if self.is_auto_loop_enabled:
            self.is_auto_loop_enabled = False
            self.btn_auto_loop.setText("🔄 Tự động binh liên tục: TẮT")
            self.btn_auto_loop.setStyleSheet(
                "background-color: #3A3A3C; color: #E5E5EA; font-weight: bold; padding: 4px 12px; border-radius: 6px;"
            )

    def _toggle_auto_loop(self) -> None:
        """Toggles continuous auto-loop mode: automatically detects new rounds and arranges cards."""
        self.is_auto_loop_enabled = not self.is_auto_loop_enabled
        if self.is_auto_loop_enabled:
            self.btn_auto_loop.setText("🔄 Tự động binh liên tục: ĐANG BẬT")
            self.btn_auto_loop.setStyleSheet(
                "background-color: #30D158; color: white; font-weight: bold; padding: 4px 12px; border-radius: 6px;"
            )
            # Auto-start scanner if windows are selected and bot not running
            has_selected_windows = any(
                getattr(self, f"combo_w{i}").currentData() for i in (1, 2, 3)
                if hasattr(self, f"combo_w{i}")
            )
            if has_selected_windows and (not self._worker or not self._worker._is_running):
                self._start_bot()

            # Queue any window that already has an unbinned new hand
            for wid in (1, 2, 3):
                p = self.panels.get(wid)
                if p and p.last_partition and len(p.last_detected_cards) == 13:
                    curr_hash = CardStateManager.compute_position_invariant_hash(p.last_detected_cards)
                    if curr_hash and curr_hash != self.last_binned_hashes.get(wid, ""):
                        if wid not in self.auto_loop_queue:
                            self.auto_loop_queue.append(wid)
            self._process_auto_loop_queue()
        else:
            self.btn_auto_loop.setText("🔄 Tự động binh liên tục: TẮT")
            self.btn_auto_loop.setStyleSheet(
                "background-color: #3A3A3C; color: #E5E5EA; font-weight: bold; padding: 4px 12px; border-radius: 6px;"
            )
            self.auto_loop_queue.clear()

    def _process_auto_loop_queue(self) -> None:
        """Processes the next pending window in auto-loop queue for continuous hand arrangement."""
        if not self.is_auto_loop_enabled:
            return
        if self.is_auto_binh_executing:
            return
        if not self.auto_loop_queue:
            return

        window_idx = self.auto_loop_queue.pop(0)
        panel = self.panels.get(window_idx)
        if not panel or not panel.last_partition or len(panel.last_detected_cards) != 13:
            return

        curr_hash = CardStateManager.compute_position_invariant_hash(panel.last_detected_cards)
        if not curr_hash or curr_hash == self.last_binned_hashes.get(window_idx, ""):
            # Already binned this hand
            return

        self.is_auto_binh_executing = True

        def on_done(success: bool, msg: str) -> None:
            self.is_auto_binh_executing = False
            if success:
                self.last_binned_hashes[window_idx] = curr_hash
                self.total_binned_rounds += 1
                self.lbl_loop_counter.setText(f"Đã binh: {self.total_binned_rounds} ván")
                r_num = self.window_round_counters.get(window_idx, 1)
                panel.set_round(r_num, is_completed=True)
                panel.lbl_status.setText(f"✅ Đã xếp xong ván #{r_num} — Đang chờ ván mới...")
                panel.lbl_status.setStyleSheet("color: #30D158; font-weight: bold;")

            # Short natural delay before processing next window in queue
            if self.is_auto_loop_enabled and self.auto_loop_queue:
                QTimer.singleShot(400, self._process_auto_loop_queue)

        self._start_auto_binh_for_window(window_idx, on_done_callback=on_done)

    def _on_frame_processed(self, window_id: int, state: WindowCardState, crop_img: Optional[np.ndarray]) -> None:
        panel = self.panels.get(window_id)
        if panel:
            panel.update_state(state, crop_img)

        # Collect detected cards for window_id
        valid_cards: List[Card] = []
        seen_codes = set()
        for d in sorted(
            state.detected_cards,
            key=lambda x: getattr(x, "confidence", getattr(x, "detection_confidence", 1.0)),
            reverse=True,
        ):
            code = str(getattr(d, "card_code", d.card.short_name if d.card else ""))
            if d.card is not None and code not in seen_codes:
                seen_codes.add(code)
                valid_cards.append(d.card)
                if len(valid_cards) == 13:
                    break

        self.window_cards[window_id] = valid_cards
        self._evaluate_table_strategy()

        if not panel:
            return

        # 1. Round cleared / Inter-round waiting state
        if len(valid_cards) < 8:
            if self.last_binned_hashes.get(window_id, ""):
                panel.lbl_status.setText("⏳ Ván cũ đã xong — Đang chờ chia bài ván mới...")
                panel.lbl_status.setStyleSheet("color: #FF9F0A; font-weight: 600;")
            self.window_stable_hashes[window_id] = ("", 0)
            return

        # 2. Check for 13 unique confirmed cards (New Hand Detection)
        if len(valid_cards) == 13:
            curr_hash = CardStateManager.compute_position_invariant_hash(state.detected_cards)
            last_binned = self.last_binned_hashes.get(window_id, "")

            # If this is a new hand that hasn't been binned yet
            if curr_hash and curr_hash != last_binned:
                prev_cand, stable_cnt = self.window_stable_hashes.get(window_id, ("", 0))
                if curr_hash == prev_cand:
                    stable_cnt += 1
                else:
                    stable_cnt = 1
                self.window_stable_hashes[window_id] = (curr_hash, stable_cnt)

                # Require at least 2 stable frames (~300ms) to ensure cards have settled
                if stable_cnt >= 2:
                    if self.window_current_hashes.get(window_id, "") != curr_hash:
                        self.window_current_hashes[window_id] = curr_hash
                        self.window_round_counters[window_id] = self.window_round_counters.get(window_id, 0) + 1
                        r_num = self.window_round_counters[window_id]
                        panel.set_round(r_num, is_new=True)
                        panel.lbl_status.setText(f"🎯 Phát hiện Ván mới #{r_num}! Đã nhận diện đủ 13 lá")
                        panel.lbl_status.setStyleSheet("color: #64D2FF; font-weight: bold;")

                    # If Auto-Loop is active and solution is already ready, queue it!
                    if self.is_auto_loop_enabled and panel.last_partition is not None:
                        if window_id not in self.auto_loop_queue:
                            self.auto_loop_queue.append(window_id)
                        self._process_auto_loop_queue()

    def _evaluate_table_strategy(self) -> None:
        """Executes table-wide collaborative deduction of 4th opponent hand and counter-strategy."""
        current_hash = tuple((w, tuple(c.card_id for c in cards)) for w, cards in sorted(self.window_cards.items()))
        if current_hash == self._last_table_hash:
            return
        self._last_table_hash = current_hash

        result = self.table_analyzer.analyze_table(self.window_cards)
        self.opponent_panel.update_result(result)

        for win_idx, panel in self.panels.items():
            if win_idx in result.window_strategies:
                panel.update_counter_strategy(result.window_strategies[win_idx])

    def _on_solution_found(self, window_id: int, solution: HandArrangement) -> None:
        if window_id in self.panels:
            panel = self.panels[window_id]
            # Only update standard solution if not in active counter-adapted mode
            if not hasattr(panel, "lbl_opp_outcome") or "BẮT SẬP" not in panel.lbl_opp_outcome.text():
                panel.update_solution(solution)

            # In Auto-Loop mode: check if this window has an un-binned new hand ready
            if self.is_auto_loop_enabled:
                curr_hash = self.window_current_hashes.get(window_id, "")
                last_binned = self.last_binned_hashes.get(window_id, "")
                if curr_hash and curr_hash != last_binned:
                    if window_id not in self.auto_loop_queue:
                        self.auto_loop_queue.append(window_id)
                    self._process_auto_loop_queue()

    def _on_auto_binh_clicked(self, window_idx: int) -> None:
        """Executes auto-binh arrangement moves on a single window."""
        self._start_auto_binh_for_window(window_idx, on_done_callback=None)

    def _on_auto_binh_all_clicked(self) -> None:
        """Sequentially executes auto-binh across all active windows in alternating order (1 -> 2 -> 3)."""
        ready_indices: List[int] = []
        for i in (1, 2, 3):
            p = self.panels.get(i)
            if p and p.last_partition and len(p.last_detected_cards) == 13:
                ready_indices.append(i)

        if not ready_indices:
            QMessageBox.warning(
                self,
                "Chưa đủ dữ liệu",
                "Chưa có bàn chơi nào nhận diện đủ 13 lá và có gợi ý xếp bài để tự động binh!\n\nHãy đảm bảo các bàn chơi đã chia bài và quét nhận diện thành công.",
            )
            return

        self.btn_auto_binh_all.setEnabled(False)
        self.btn_auto_binh_all.setText("⏳ Đang luân phiên binh 3 bàn...")
        self._pending_alternating_windows = list(ready_indices)
        self._execute_next_alternating_window()

    def _execute_next_alternating_window(self) -> None:
        if not self._pending_alternating_windows:
            self.btn_auto_binh_all.setEnabled(True)
            self.btn_auto_binh_all.setText("⚡ Binh bài cả 3 bàn (Luân phiên)")
            return

        window_idx = self._pending_alternating_windows.pop(0)

        def on_window_done(success: bool, msg: str) -> None:
            if self._pending_alternating_windows:
                # 400ms pause before activating next window to simulate natural delay
                QTimer.singleShot(400, self._execute_next_alternating_window)
            else:
                self.btn_auto_binh_all.setEnabled(True)
                self.btn_auto_binh_all.setText("⚡ Binh bài cả 3 bàn (Luân phiên)")

        self._start_auto_binh_for_window(window_idx, on_done_callback=on_window_done)

    def _start_auto_binh_for_window(
        self, window_idx: int, on_done_callback: Optional[Callable[[bool, str], None]] = None
    ) -> None:
        """Executes auto-binh arrangement moves on the selected game window using GestureManager."""
        panel = self.panels.get(window_idx)
        if not panel or not panel.last_partition or not panel.last_detected_cards:
            if on_done_callback is None:
                QMessageBox.warning(self, "Chưa đủ dữ liệu", "Cần phát hiện đủ 13 lá bài và có kết quả xếp bài để tự động binh!")
            else:
                on_done_callback(False, "Chưa đủ dữ liệu")
            return

        existing_worker = self._auto_binh_workers.get(window_idx)
        if existing_worker and existing_worker.isRunning():
            panel.lbl_status.setText("⏳ Đang thực hiện xếp bài, vui lòng chờ...")
            return

        if len(panel.last_detected_cards) < 13:
            if on_done_callback is None:
                QMessageBox.warning(self, "Chưa đủ 13 lá", f"Cửa sổ #{window_idx} mới nhận diện được {len(panel.last_detected_cards)}/13 lá!")
            else:
                on_done_callback(False, "Chưa đủ 13 lá")
            return

        # 1. Map detected cards to slots 1..13
        sorted_dets = sorted(panel.last_detected_cards, key=lambda d: d.bbox[1])
        front_dets = sorted(sorted_dets[0:3], key=lambda d: d.bbox[0])
        mid_dets = sorted(sorted_dets[3:8], key=lambda d: d.bbox[0])
        back_dets = sorted(sorted_dets[8:13], key=lambda d: d.bbox[0])

        current_slots: Dict[int, Card] = {}
        for idx, d in enumerate(front_dets, start=1):
            current_slots[idx] = d.card
        for idx, d in enumerate(mid_dets, start=4):
            current_slots[idx] = d.card
        for idx, d in enumerate(back_dets, start=9):
            current_slots[idx] = d.card

        # 2. Plan minimal swaps
        from app.automation.move_planner import MovePlanner
        plan = MovePlanner.plan_moves(current_slots, panel.last_partition)

        if plan.is_already_optimal or plan.total_swaps == 0:
            panel.lbl_status.setText("Bài đã ở vị trí tối ưu, không cần xếp thêm!")
            panel.lbl_status.setStyleSheet("color: #30D158; font-weight: bold;")
            curr_hash = CardStateManager.compute_position_invariant_hash(panel.last_detected_cards)
            self.last_binned_hashes[window_idx] = curr_hash
            r_num = self.window_round_counters.get(window_idx, 1)
            panel.set_round(r_num, is_completed=True)
            if on_done_callback:
                on_done_callback(True, "Bài đã ở vị trí tối ưu")
            return

        # 3. Determine real-time live window bounds and activate game window
        combo = getattr(self, f"combo_w{window_idx}", None)
        selected_id = combo.currentData() if combo else None
        if selected_id:
            self.window_manager.activate_window(selected_id)
            time.sleep(0.18)

        live_bounds = self.window_manager.get_window_bounds(selected_id) if selected_id else None
        if live_bounds:
            win_bounds = live_bounds
        else:
            win_item = next((w for w in self.discovered_windows if w.window_id == selected_id), None)
            if win_item and isinstance(win_item.bounds, (tuple, list)) and len(win_item.bounds) == 4:
                win_bounds = (int(win_item.bounds[0]), int(win_item.bounds[1]), int(win_item.bounds[2]), int(win_item.bounds[3]))
            else:
                win_bounds = (100, 100, 1200, 800)

        # 4. Extract real-time card slot coordinates from detected card bounding boxes
        frame_w = 0
        frame_h = 0
        if hasattr(panel, "last_frame") and panel.last_frame is not None and panel.last_frame.size > 0:
            frame_h, frame_w = panel.last_frame.shape[0], panel.last_frame.shape[1]
        elif hasattr(panel.viewer, "_current_image") and panel.viewer._current_image is not None:
            frame_h, frame_w = panel.viewer._current_image.shape[0], panel.viewer._current_image.shape[1]

        live_slot_coords: Dict[int, Tuple[float, float]] = {}
        if frame_w > 0 and frame_h > 0:
            for idx, d in enumerate(front_dets, start=1):
                bx, by, bw, bh = d.bbox
                live_slot_coords[idx] = (round((bx + bw / 2.0) / frame_w, 4), round((by + bh / 2.0) / frame_h, 4))
            for idx, d in enumerate(mid_dets, start=4):
                bx, by, bw, bh = d.bbox
                live_slot_coords[idx] = (round((bx + bw / 2.0) / frame_w, 4), round((by + bh / 2.0) / frame_h, 4))
            for idx, d in enumerate(back_dets, start=9):
                bx, by, bw, bh = d.bbox
                live_slot_coords[idx] = (round((bx + bw / 2.0) / frame_w, 4), round((by + bh / 2.0) / frame_h, 4))

        # 5. Run AutoBinhWorker on QThread with dynamic live trajectory adaptation
        from app.automation.gesture_manager import AutoBinhWorker
        panel.btn_auto_binh.setEnabled(False)
        panel.btn_auto_binh.setText("Đang tự động binh bài...")

        worker = AutoBinhWorker(
            manager=self.gesture_manager,
            plan=plan,
            win_bounds=win_bounds,
            config=self.gesture_manager.config,
            live_slot_coords=live_slot_coords if live_slot_coords else None,
            parent=self,
        )
        self._auto_binh_workers[window_idx] = worker

        def on_step(idx: int, total: int, desc: str) -> None:
            panel.lbl_status.setText(f"⚡ Binh bài: {idx}/{total} - {desc}")
            panel.lbl_status.setStyleSheet("color: #64D2FF; font-weight: bold;")

        def on_finished(success: bool, msg: str) -> None:
            panel.btn_auto_binh.setEnabled(True)
            panel.btn_auto_binh.setText("⚡ Tự Động Binh Bài")
            panel.lbl_status.setText(msg)
            panel.lbl_status.setStyleSheet("color: #30D158; font-weight: bold;" if success else "color: #FF453A; font-weight: bold;")
            if success:
                curr_hash = CardStateManager.compute_position_invariant_hash(panel.last_detected_cards)
                self.last_binned_hashes[window_idx] = curr_hash
                r_num = self.window_round_counters.get(window_idx, 1)
                panel.set_round(r_num, is_completed=True)
            if on_done_callback:
                on_done_callback(success, msg)

        worker.step_started.connect(on_step)
        worker.finished_result.connect(on_finished)
        worker.start()

    def closeEvent(self, event) -> None:
        """Ensures all scanning loops and gesture workers are stopped before widget destruction."""
        self._stop_bot()
        self.is_auto_loop_enabled = False
        self.auto_loop_queue.clear()
        for worker in list(self._auto_binh_workers.values()):
            if worker and worker.isRunning():
                worker.stop()
                worker.wait(800)
        self._auto_binh_workers.clear()
        super().closeEvent(event)
