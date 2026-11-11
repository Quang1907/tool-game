"""Multi-Window Bot Widget: 3-window simultaneous game monitor and analyzer on macOS."""

from __future__ import annotations
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import cv2
import numpy as np
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
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

    def set_counter_strategy_visible(self, visible: bool) -> None:
        """Shows or hides the opponent counter-strategy box to avoid clutter in 1 or 2 screen mode."""
        self.box_vs_opp.setVisible(visible)

    def set_expanded_mode(self, expanded: bool) -> None:
        """Expands viewer height for single-screen focus mode."""
        if expanded:
            self.viewer.setMinimumHeight(240)
            self.viewer.setMaximumHeight(340)
        else:
            self.viewer.setMinimumHeight(180)
            self.viewer.setMaximumHeight(240)

    def clear_solution(self) -> None:
        """Clears arrangement solution and locks Auto-Binh button to prevent misplays."""
        self.last_partition = None
        if not self.btn_auto_binh.text().startswith("⏳ Chờ ván mới"):
            self.btn_auto_binh.setEnabled(False)
            self.btn_auto_binh.setText("⚡ Tự Động Binh Bài")
            self.btn_auto_binh.setStyleSheet("background-color: #30D158; color: white; font-weight: bold; border-radius: 6px; padding: 6px 12px;")
        self.lbl_chi_front.setText("Chi Đầu: (Chưa đủ 13 lá — Đã khóa binh)")
        self.lbl_chi_middle.setText("Chi Giữa: (Chưa đủ 13 lá — Đã khóa binh)")
        self.lbl_chi_back.setText("Chi Cuối: (Chưa đủ 13 lá — Đã khóa binh)")
        self.lbl_opp_outcome.setText("Chưa đủ 13 lá để tính đối đầu")
        self.lbl_opp_breakdown.setText("")
        self.box_solution.setTitle("Gợi ý xếp bài tối ưu")

    def update_state(self, state: WindowCardState, crop_img: Optional[np.ndarray]) -> None:
        """Updates live preview and card list."""
        self.last_detected_cards = list(state.detected_cards)
        if state.status == "OCCLUDED":
            self.lbl_status.setText("⚠️ Cửa sổ bị che (Occluded)")
            self.lbl_status.setStyleSheet("color: #FF453A; font-weight: 600;")
            self.clear_solution()
        elif state.status == "MOVED_NO_RECALCULATE":
            self.lbl_status.setText(f"✓ {len(state.detected_cards)} lá (Bài di chuyển - Không tính lại)")
            self.lbl_status.setStyleSheet("color: #0A84FF; font-weight: 600;")
        elif state.status == "CONFIRMED_13" or len(state.detected_cards) == 13:
            self.lbl_status.setText("★ Đủ 13 lá bài — Đã tối ưu")
            self.lbl_status.setStyleSheet("color: #30D158; font-weight: 600;")
        elif len(state.detected_cards) > 0:
            self.lbl_status.setText(f"⛔ Phát hiện: {len(state.detected_cards)}/13 lá — KHÓA BINH CHỐNG BINH LỦNG")
            self.lbl_status.setStyleSheet("color: #FF453A; font-weight: 600;")
            self.clear_solution()
        else:
            self.lbl_status.setText("Đang theo dõi cửa sổ (Chưa thấy bài)")
            self.lbl_status.setStyleSheet("color: #8E8E93; font-weight: 600;")
            self.clear_solution()

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
        if not self.btn_auto_binh.text().startswith("⏳ Chờ ván mới"):
            self.btn_auto_binh.setEnabled(partition is not None and len(self.last_detected_cards) == 13)
            self.btn_auto_binh.setText("⚡ Tự Động Binh Bài")
            self.btn_auto_binh.setStyleSheet("background-color: #30D158; color: white; font-weight: bold; border-radius: 6px; padding: 6px 12px;")

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


class ScreenSelectionCard(QFrame):
    """Interactive visual card representing 1, 2, or 3 screen mode."""

    clicked = Signal(int)

    def __init__(
        self,
        num_screens: int,
        icon: str,
        title: str,
        subtitle: str,
        features: List[str],
        accent_color: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.num_screens = num_screens
        self.accent_color = accent_color
        self._init_ui(icon, title, subtitle, features, accent_color)

    def _init_ui(
        self, icon: str, title: str, subtitle: str, features: List[str], accent_color: str
    ) -> None:
        self.setObjectName("ScreenCard")
        self.setStyleSheet(f"""
            QFrame#ScreenCard {{
                background-color: #1C1C1E;
                border: 2px solid #2C2C2E;
                border-radius: 12px;
                padding: 14px;
            }}
            QFrame#ScreenCard:hover {{
                border: 2px solid {accent_color};
                background-color: #242428;
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 18, 16, 16)

        # Icon
        lbl_icon = QLabel(icon)
        lbl_icon.setAlignment(Qt.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 38px; background: transparent; border: none;")
        layout.addWidget(lbl_icon)

        # Title
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {accent_color}; background: transparent; border: none;")
        layout.addWidget(lbl_title)

        # Subtitle
        lbl_sub = QLabel(subtitle)
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet("font-size: 11px; color: #8E8E93; background: transparent; border: none;")
        layout.addWidget(lbl_sub)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #2C2C2E; max-height: 1px; border: none; margin: 4px 0;")
        layout.addWidget(divider)

        # Features list
        features_box = QVBoxLayout()
        features_box.setSpacing(6)
        for feat in features:
            lbl_f = QLabel(feat)
            lbl_f.setWordWrap(True)
            lbl_f.setStyleSheet("font-size: 11px; color: #D1D1D6; background: transparent; border: none; line-height: 1.3;")
            features_box.addWidget(lbl_f)
        layout.addLayout(features_box)

        layout.addStretch()

        # Action button
        self.btn_select = QPushButton(f"🚀 Chọn {title}")
        self.btn_select.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent_color};
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
                border-radius: 8px;
                padding: 10px 14px;
                border: none;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        self.btn_select.setCursor(Qt.PointingHandCursor)
        self.btn_select.clicked.connect(lambda: self.clicked.emit(self.num_screens))
        layout.addWidget(self.btn_select)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.num_screens)
        super().mousePressEvent(event)


class ScreenSelectionWidget(QWidget):
    """Clean selection page to choose 1, 2, or 3 screens before revealing the uncluttered interface."""

    screen_mode_selected = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(24, 20, 24, 20)
        outer_layout.setSpacing(12)

        outer_layout.addStretch(1)

        # Header Box
        header_box = QVBoxLayout()
        header_box.setSpacing(6)

        lbl_badge = QLabel("🎮 TÙY CHỌN GIAO DIỆN CHỐNG RỐI MẮT")
        lbl_badge.setAlignment(Qt.AlignCenter)
        lbl_badge.setStyleSheet(
            "color: #64D2FF; font-weight: bold; font-size: 11px; letter-spacing: 1px;"
        )
        header_box.addWidget(lbl_badge)

        lbl_title = QLabel("BẠN MUỐN CHƠI / THEO DÕI MẤY MÀN HÌNH?")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("color: #FFFFFF; font-size: 21px; font-weight: 800;")
        header_box.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Chọn số lượng bàn chơi bên dưới để hệ thống tối ưu hóa giao diện trực quan, loại bỏ hoàn toàn các khung thừa chống rối mắt:"
        )
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setStyleSheet("color: #8E8E93; font-size: 12px;")
        header_box.addWidget(lbl_desc)

        outer_layout.addLayout(header_box)
        outer_layout.addSpacing(16)

        # Cards Container
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        # Card 1: 1 Màn Hình
        self.card1 = ScreenSelectionCard(
            num_screens=1,
            icon="🖥️",
            title="1 Màn Hình",
            subtitle="Chế độ tập trung 1 bàn duy nhất",
            features=[
                "✓ Giao diện cực rộng, không bị chia nhỏ",
                "✓ Phóng to hình ảnh và quân bài tối đa",
                "✓ Chống rối mắt, ẩn toàn bộ khung thừa",
                "✓ Tự động xếp bài & cảnh báo binh lủng",
            ],
            accent_color="#0A84FF",
            parent=self,
        )
        self.card1.clicked.connect(self.screen_mode_selected.emit)
        cards_layout.addWidget(self.card1)

        # Card 2: 2 Màn Hình
        self.card2 = ScreenSelectionCard(
            num_screens=2,
            icon="🖥️ 🖥️",
            title="2 Màn Hình",
            subtitle="Chế độ chơi 2 bàn song song",
            features=[
                "✓ Giao diện chia đôi 50/50 cân đối, dễ nhìn",
                "✓ Luân phiên tự động xếp bài giữa 2 bàn",
                "✓ Ẩn bàn thứ 3 và bảng đối thủ chống rối",
                "✓ Quản lý chu kỳ ván bài độc lập từng bàn",
            ],
            accent_color="#30D158",
            parent=self,
        )
        self.card2.clicked.connect(self.screen_mode_selected.emit)
        cards_layout.addWidget(self.card2)

        # Card 3: 3 Màn Hình
        self.card3 = ScreenSelectionCard(
            num_screens=3,
            icon="🖥️ 🖥️ 🖥️",
            title="3 Màn Hình",
            subtitle="Chế độ tối đa 3 bàn + Đoán bài đối thủ",
            features=[
                "✓ Giám sát đồng thời cả 3 cửa sổ game",
                "✓ Tự động suy luận 13 lá đối thủ #4",
                "✓ Tối ưu hóa thế bài khắc chế bắt sập",
                "✓ Tự động binh liên tục cả 3 bàn",
            ],
            accent_color="#BF5AF2",
            parent=self,
        )
        self.card3.clicked.connect(self.screen_mode_selected.emit)
        cards_layout.addWidget(self.card3)

        outer_layout.addLayout(cards_layout)

        # Bottom Tip
        lbl_hint = QLabel(
            "💡 Mẹo: Bạn có thể nhanh chóng đổi lại số màn hình (1, 2 hoặc 3) bất cứ lúc nào ngay trên thanh công cụ."
        )
        lbl_hint.setAlignment(Qt.AlignCenter)
        lbl_hint.setStyleSheet("color: #636366; font-size: 11px; margin-top: 12px;")
        outer_layout.addWidget(lbl_hint)

        outer_layout.addStretch(1)


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

        # Round Timing & Cooldown Wait
        self.window_cooldown_remaining: Dict[int, int] = {1: 0, 2: 0, 3: 0}
        self.window_round_start_times: Dict[int, float] = {1: 0.0, 2: 0.0, 3: 0.0}
        self.has_seen_table_cleared: Dict[int, bool] = {1: True, 2: True, 3: True}

        # Screen Mode (1, 2, or 3 screens)
        self.active_screen_count: int = 3
        self.has_selected_screen_mode: bool = False

        # Cooldown countdown timer (1Hz)
        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.setInterval(1000)
        self._cooldown_timer.timeout.connect(self._on_cooldown_tick)
        self._cooldown_timer.start()

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.stacked_widget = QStackedWidget(self)
        main_layout.addWidget(self.stacked_widget)

        # Page 0: Screen Selection Landing Page (chống rối mắt)
        self.selection_page = ScreenSelectionWidget(parent=self)
        self.selection_page.screen_mode_selected.connect(self.set_screen_mode)
        self.stacked_widget.addWidget(self.selection_page)

        # Page 1: Main Dashboard Page
        self.dashboard_page = QWidget(self)
        self._init_dashboard_ui(self.dashboard_page)
        self.stacked_widget.addWidget(self.dashboard_page)

        # Apply default layout for 3 screens internally so all child widgets are wired
        self._apply_screen_mode_layout(3)

        # Show selection page initially to let user choose 1, 2, or 3 screens
        self.stacked_widget.setCurrentIndex(0)

    def _init_dashboard_ui(self, container: QWidget) -> None:
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Top Control Bar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # Screen Mode Controls
        self.btn_back_to_selection = QPushButton("🔙 Đổi số màn", objectName="SecondaryBtn")
        self.btn_back_to_selection.setToolTip("Quay lại màn hình lựa chọn 1, 2 hoặc 3 màn hình")
        self.btn_back_to_selection.setFixedHeight(28)
        self.btn_back_to_selection.clicked.connect(self.reset_screen_selection)
        toolbar.addWidget(self.btn_back_to_selection)

        self.btn_mode_1 = QPushButton("1 Màn")
        self.btn_mode_1.setFixedHeight(28)
        self.btn_mode_1.setToolTip("Chế độ 1 màn hình: Giao diện cực rộng, tập trung 1 bàn duy nhất")
        self.btn_mode_1.clicked.connect(lambda: self.set_screen_mode(1))
        toolbar.addWidget(self.btn_mode_1)

        self.btn_mode_2 = QPushButton("2 Màn")
        self.btn_mode_2.setFixedHeight(28)
        self.btn_mode_2.setToolTip("Chế độ 2 màn hình: Chia đôi cân đối 50/50, binh 2 bàn song song")
        self.btn_mode_2.clicked.connect(lambda: self.set_screen_mode(2))
        toolbar.addWidget(self.btn_mode_2)

        self.btn_mode_3 = QPushButton("3 Màn")
        self.btn_mode_3.setFixedHeight(28)
        self.btn_mode_3.setToolTip("Chế độ 3 màn hình: Tối đa 3 bàn + Tự động suy luận bài đối thủ #4")
        self.btn_mode_3.clicked.connect(lambda: self.set_screen_mode(3))
        toolbar.addWidget(self.btn_mode_3)

        sep_mode = QFrame()
        sep_mode.setFrameShape(QFrame.VLine)
        sep_mode.setStyleSheet("color: #3A3A3C;")
        toolbar.addWidget(sep_mode)

        self.btn_refresh_wins = QPushButton("🔄 Quét cửa sổ macOS", objectName="SecondaryBtn")
        self.btn_refresh_wins.clicked.connect(self._refresh_window_list)
        toolbar.addWidget(self.btn_refresh_wins)

        self.lbl_w1 = QLabel("Cửa sổ 1:")
        self.lbl_w1.setStyleSheet("font-weight: 600; font-size: 11px;")
        toolbar.addWidget(self.lbl_w1)
        self.combo_w1 = QComboBox()
        self.combo_w1.currentIndexChanged.connect(lambda: self._on_window_selected(1))
        toolbar.addWidget(self.combo_w1)

        self.lbl_w2 = QLabel("Cửa sổ 2:")
        self.lbl_w2.setStyleSheet("font-weight: 600; font-size: 11px;")
        toolbar.addWidget(self.lbl_w2)
        self.combo_w2 = QComboBox()
        self.combo_w2.currentIndexChanged.connect(lambda: self._on_window_selected(2))
        toolbar.addWidget(self.combo_w2)

        self.lbl_w3 = QLabel("Cửa sổ 3:")
        self.lbl_w3.setStyleSheet("font-weight: 600; font-size: 11px;")
        toolbar.addWidget(self.lbl_w3)
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
            "Tự động luân phiên xếp bài trên các cửa sổ/tab đã chọn"
        )
        self.btn_auto_binh_all.clicked.connect(self._on_auto_binh_all_clicked)
        toolbar.addWidget(self.btn_auto_binh_all)

        self.btn_auto_loop = QPushButton("🔄 Tự động binh liên tục: TẮT")
        self.btn_auto_loop.setFixedHeight(32)
        self.btn_auto_loop.setStyleSheet(
            "background-color: #3A3A3C; color: #E5E5EA; font-weight: bold; padding: 4px 12px; border-radius: 6px;"
        )
        self.btn_auto_loop.setToolTip(
            "BẬT/TẮT chế độ tự động chạy liên tục: Tự động phát hiện ván bài mới và xếp bài liên tục ván này qua ván khác trên các bàn đã chọn"
        )
        self.btn_auto_loop.clicked.connect(self._toggle_auto_loop)
        toolbar.addWidget(self.btn_auto_loop)

        self.lbl_loop_counter = QLabel("Đã binh: 0 ván")
        self.lbl_loop_counter.setStyleSheet(
            "color: #FF9F0A; font-weight: bold; font-size: 11px; padding: 4px 8px; background: rgba(255,159,10,0.12); border-radius: 4px;"
        )
        toolbar.addWidget(self.lbl_loop_counter)

        main_layout.addLayout(toolbar)

        # Second Bar: Game Round Timing & Cooldown Configuration
        timing_bar = QHBoxLayout()
        timing_bar.setSpacing(10)

        self.chk_auto_game_timing = QCheckBox("⚡ Tự động theo nhịp game (Binh ngay khi có bài mới)")
        self.chk_auto_game_timing.setChecked(True)
        self.chk_auto_game_timing.setToolTip(
            "Tự động nhận diện khi game tính toán + tiền xong và chia đủ 13 lá bài mới để tự động binh bài ngay lập tức, không cần chờ đếm lùi thời gian thủ công."
        )
        self.chk_auto_game_timing.setStyleSheet(
            "QCheckBox { color: #32D74B; font-weight: bold; font-size: 11px; } "
            "QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; } "
            "QCheckBox::indicator:checked { background-color: #30D158; border: 1px solid #30D158; }"
        )
        self.chk_auto_game_timing.toggled.connect(self._on_auto_game_timing_toggled)
        timing_bar.addWidget(self.chk_auto_game_timing)

        lbl_round_icon = QLabel("⏱ Thời gian ván:")
        lbl_round_icon.setStyleSheet("color: #8E8E93; font-weight: 600; font-size: 11px;")
        timing_bar.addWidget(lbl_round_icon)

        self.spin_round_time = QSpinBox()
        self.spin_round_time.setRange(10, 180)
        self.spin_round_time.setValue(45)
        self.spin_round_time.setSuffix(" s")
        self.spin_round_time.setToolTip("Thời gian 1 hiệp binh bài của ván chơi trong game (khi tắt chế độ tự động theo nhịp game).")
        self.spin_round_time.setEnabled(False)
        self.spin_round_time.setStyleSheet(
            "background-color: #2C2C2E; color: #64D2FF; font-weight: bold; padding: 2px 6px; border-radius: 4px; border: 1px solid #3A3A3C;"
        )
        timing_bar.addWidget(self.spin_round_time)

        lbl_wait_icon = QLabel("⏳ Chờ ván mới:")
        lbl_wait_icon.setStyleSheet("color: #8E8E93; font-weight: 600; font-size: 11px;")
        timing_bar.addWidget(lbl_wait_icon)

        self.spin_cooldown = QSpinBox()
        self.spin_cooldown.setRange(5, 120)
        self.spin_cooldown.setValue(20)
        self.spin_cooldown.setSuffix(" s")
        self.spin_cooldown.setToolTip("Thời gian game so bài, trả thưởng và dọn bàn (khi tắt chế độ tự động theo nhịp game).")
        self.spin_cooldown.setEnabled(False)
        self.spin_cooldown.setStyleSheet(
            "background-color: #2C2C2E; color: #FF9F0A; font-weight: bold; padding: 2px 6px; border-radius: 4px; border: 1px solid #3A3A3C;"
        )
        timing_bar.addWidget(self.spin_cooldown)

        self.lbl_cooldown_summary = QLabel("Chế độ: Tự động theo nhịp game (Real-time)")
        self.lbl_cooldown_summary.setStyleSheet("color: #32D74B; font-weight: bold; font-size: 11px; padding: 2px 8px;")
        timing_bar.addWidget(self.lbl_cooldown_summary)

        timing_bar.addStretch()

        self.btn_reset_wait = QPushButton("🔓 Mở khóa tất cả chờ", objectName="SecondaryBtn")
        self.btn_reset_wait.setToolTip("Mở khóa cưỡng chế ngay lập tức nếu không muốn đợi hết thời gian chờ.")
        self.btn_reset_wait.setFixedHeight(26)
        self.btn_reset_wait.clicked.connect(self._unlock_all_cooldowns)
        timing_bar.addWidget(self.btn_reset_wait)

        main_layout.addLayout(timing_bar)

        # 3 Side-by-side or Grid Panels
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

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

    def _get_auto_binh_all_text(self) -> str:
        """Generates dynamic action button label matching current screen mode."""
        if self.active_screen_count == 1:
            return "⚡ Tự Động Binh Bài"
        elif self.active_screen_count == 2:
            return "⚡ Binh bài cả 2 bàn (Luân phiên)"
        else:
            return "⚡ Binh bài cả 3 bàn (Luân phiên)"

    def set_screen_mode(self, num_screens: int) -> None:
        """Switches dashboard view to 1, 2, or 3 screens, eliminating visual clutter."""
        if num_screens not in (1, 2, 3):
            return

        if self._worker and self._worker._is_running:
            self._stop_bot()

        self.active_screen_count = num_screens
        self.has_selected_screen_mode = True
        self._apply_screen_mode_layout(num_screens)
        self.stacked_widget.setCurrentIndex(1)

    def reset_screen_selection(self) -> None:
        """Returns to the initial screen selection page."""
        if self._worker and self._worker._is_running:
            self._stop_bot()
        self.stacked_widget.setCurrentIndex(0)

    def _apply_screen_mode_layout(self, num_screens: int) -> None:
        """Applies visibility and layout adaptations according to the selected number of screens."""
        # 1. Update toolbar mode buttons
        for n, btn in ((1, self.btn_mode_1), (2, self.btn_mode_2), (3, self.btn_mode_3)):
            if n == num_screens:
                color = "#0A84FF" if n == 1 else ("#30D158" if n == 2 else "#5E5CE6")
                btn.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold; padding: 2px 8px; border-radius: 4px;")
            else:
                btn.setStyleSheet("background-color: #2C2C2E; color: #8E8E93; padding: 2px 8px; border-radius: 4px;")

        # 2. Update window labels and combo boxes
        self.lbl_w1.setText("Cửa sổ game:" if num_screens == 1 else "Cửa sổ 1:")
        self.lbl_w1.setVisible(True)
        self.combo_w1.setVisible(True)

        self.lbl_w2.setText("Cửa sổ 2:")
        self.lbl_w2.setVisible(num_screens >= 2)
        self.combo_w2.setVisible(num_screens >= 2)

        self.lbl_w3.setText("Cửa sổ 3:")
        self.lbl_w3.setVisible(num_screens >= 3)
        self.combo_w3.setVisible(num_screens >= 3)

        # 3. Update Panels
        self.panels[1].setVisible(True)
        self.panels[1].setTitle("Bàn Chơi" if num_screens == 1 else "Cửa sổ #1")
        self.panels[1].set_counter_strategy_visible(num_screens == 3)
        self.panels[1].set_expanded_mode(num_screens == 1)

        self.panels[2].setVisible(num_screens >= 2)
        self.panels[2].setTitle("Cửa sổ #2")
        self.panels[2].set_counter_strategy_visible(num_screens == 3)
        self.panels[2].set_expanded_mode(False)

        self.panels[3].setVisible(num_screens >= 3)
        self.panels[3].setTitle("Cửa sổ #3")
        self.panels[3].set_counter_strategy_visible(num_screens == 3)
        self.panels[3].set_expanded_mode(False)

        # 4. Update Opponent Panel
        self.opponent_panel.setVisible(num_screens == 3)

        # 5. Update Action Buttons text
        if self._worker and self._worker._is_running:
            self.btn_start.setText("⏹ Dừng quét")
            self.btn_start.setStyleSheet("background-color: #FF453A;")
        else:
            self.btn_start.setText(
                "▶ Bắt đầu quét 1 cửa sổ" if num_screens == 1
                else f"▶ Bắt đầu quét {num_screens} cửa sổ"
            )
            self.btn_start.setStyleSheet("")

        self.btn_auto_binh_all.setText(self._get_auto_binh_all_text())

    def _on_auto_game_timing_toggled(self, checked: bool) -> None:
        """Toggles between real-time game rhythm auto-detection and fixed countdown timer mode."""
        self.spin_round_time.setEnabled(not checked)
        self.spin_cooldown.setEnabled(not checked)
        if checked:
            self.lbl_cooldown_summary.setText("Chế độ: Tự động theo nhịp game (Real-time)")
            self.lbl_cooldown_summary.setStyleSheet("color: #32D74B; font-weight: bold; font-size: 11px; padding: 2px 8px;")
            self._unlock_all_cooldowns()
        else:
            self.lbl_cooldown_summary.setText("Chế độ: Đếm lùi thời gian cố định")
            self.lbl_cooldown_summary.setStyleSheet("color: #FF9F0A; font-size: 11px; padding: 2px 8px;")

    def _on_cooldown_tick(self) -> None:
        """Decrements cooldown countdown for any window that recently completed auto-binh in manual timer mode."""
        is_auto_game = hasattr(self, "chk_auto_game_timing") and self.chk_auto_game_timing.isChecked()
        if is_auto_game:
            self.lbl_cooldown_summary.setText("Chế độ: Tự động theo nhịp game (Real-time)")
            self.lbl_cooldown_summary.setStyleSheet("color: #32D74B; font-weight: bold; font-size: 11px; padding: 2px 8px;")
            return

        active_cooldowns = 0
        for wid in range(1, self.active_screen_count + 1):
            rem = self.window_cooldown_remaining.get(wid, 0)
            panel = self.panels.get(wid)
            if rem > 0:
                rem -= 1
                self.window_cooldown_remaining[wid] = rem
                active_cooldowns += 1
                if panel:
                    r_num = self.window_round_counters.get(wid, 1)
                    panel.btn_auto_binh.setEnabled(False)
                    panel.btn_auto_binh.setText(f"⏳ Chờ ván mới ({rem}s)")
                    panel.btn_auto_binh.setStyleSheet("background-color: #3A3A3C; color: #8E8E93;")
                    panel.lbl_status.setText(f"⏳ ĐÃ BINH XONG VÁN #{r_num} — Khóa đợi ván mới (còn {rem}s)...")
                    panel.lbl_status.setStyleSheet("color: #FF9F0A; font-weight: bold;")
            elif rem == 0 and panel and panel.btn_auto_binh.text().startswith("⏳ Chờ ván mới"):
                panel.btn_auto_binh.setText("⚡ Tự Động Binh Bài")
                panel.btn_auto_binh.setStyleSheet("")
                panel.lbl_status.setText("⏳ Hết thời gian chờ — Đang đợi bàn chia bài ván mới...")
                panel.lbl_status.setStyleSheet("color: #64D2FF; font-weight: 600;")
                self.has_seen_table_cleared[wid] = False

        if active_cooldowns > 0:
            self.lbl_cooldown_summary.setText(f"Đang khóa chờ ván mới trên {active_cooldowns} bàn...")
            self.lbl_cooldown_summary.setStyleSheet("color: #FF9F0A; font-size: 11px;")
        else:
            self.lbl_cooldown_summary.setText("Trạng thái: Sẵn sàng nhận diện ván mới")
            self.lbl_cooldown_summary.setStyleSheet("color: #30D158; font-size: 11px;")

    def _unlock_all_cooldowns(self) -> None:
        """Manually unlocks any active cooldown wait times."""
        for wid in range(1, self.active_screen_count + 1):
            self.window_cooldown_remaining[wid] = 0
            self.has_seen_table_cleared[wid] = True
            panel = self.panels.get(wid)
            if panel:
                panel.btn_auto_binh.setText("⚡ Tự Động Binh Bài")
                panel.btn_auto_binh.setStyleSheet("")
                if panel.last_partition and len(panel.last_detected_cards) == 13:
                    panel.btn_auto_binh.setEnabled(True)
                    panel.lbl_status.setText("★ Đủ 13 lá bài — Đã tối ưu (Đã mở khóa)")
                    panel.lbl_status.setStyleSheet("color: #30D158; font-weight: 600;")
                else:
                    panel.lbl_status.setText("Đã mở khóa chờ — Đang quét bài...")
                    panel.lbl_status.setStyleSheet("color: #64D2FF; font-weight: 600;")
        self.lbl_cooldown_summary.setText("Đã mở khóa tất cả các bàn")
        self.lbl_cooldown_summary.setStyleSheet("color: #30D158; font-size: 11px;")

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
        for d in sorted(detected_cards, key=lambda x: getattr(x, "confidence", getattr(x, "detection_confidence", 1.0)), reverse=True):
            code = getattr(d, "card_code", f"{d.card.rank.char}{d.card.suit.char.upper()}" if d.card else "")
            if d.card is not None and code not in seen_codes:
                seen_codes.add(code)
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
                    panel.clear_solution()
                    panel.lbl_status.setText(f"✓ Đã xác nhận [{win_title}]: 13 lá — Không tìm thấy bộ hợp lệ")
                    panel.lbl_status.setStyleSheet("color: #FF9F0A; font-weight: 600;")
            except Exception as e:
                panel.clear_solution()
                panel.lbl_status.setText(f"Lỗi tính toán: {e}")
                panel.lbl_status.setStyleSheet("color: #FF453A; font-weight: 600;")
        elif detected_cards:
            panel.clear_solution()
            panel.lbl_status.setText(f"⛔ [{win_title}]: Phát hiện {len(detected_cards)}/13 lá — ĐÃ KHÓA BINH CHỐNG BINH LỦNG")
            panel.lbl_status.setStyleSheet("color: #FF453A; font-weight: 600;")
        else:
            panel.clear_solution()
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
        # Collect chosen ROIs up to active screen count
        rois: List[WindowROI] = []
        combos = [self.combo_w1, self.combo_w2, self.combo_w3][:self.active_screen_count]

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
            target_str = "cửa sổ game" if self.active_screen_count == 1 else f"ít nhất 1 cửa sổ game trong {self.active_screen_count} màn hình"
            QMessageBox.warning(self, "Chưa chọn cửa sổ", f"Vui lòng chọn {target_str} để bắt đầu.")
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
        self.btn_start.setText(
            "▶ Bắt đầu quét 1 cửa sổ" if self.active_screen_count == 1
            else f"▶ Bắt đầu quét {self.active_screen_count} cửa sổ"
        )
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
                getattr(self, f"combo_w{i}").currentData() for i in range(1, self.active_screen_count + 1)
                if hasattr(self, f"combo_w{i}")
            )
            if has_selected_windows and (not self._worker or not self._worker._is_running):
                self._start_bot()

            # Queue any window that already has an unbinned new hand
            for wid in range(1, self.active_screen_count + 1):
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

        # STRICT LOCK CHECK: Do not process window if currently in manual cooldown countdown
        is_auto_game = hasattr(self, "chk_auto_game_timing") and self.chk_auto_game_timing.isChecked()
        if not is_auto_game and self.window_cooldown_remaining.get(window_idx, 0) > 0:
            return

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
            # Clean up queue of any accidental duplicates of this window
            self.auto_loop_queue = [w for w in self.auto_loop_queue if w != window_idx]
            if success and curr_hash != self.last_binned_hashes.get(window_idx, ""):
                self.last_binned_hashes[window_idx] = curr_hash
                self.total_binned_rounds += 1
                self.lbl_loop_counter.setText(f"Đã binh: {self.total_binned_rounds} ván")
                r_num = self.window_round_counters.get(window_idx, 1)
                panel.set_round(r_num, is_completed=True)

            # Short natural delay before processing next window in queue
            if self.is_auto_loop_enabled and self.auto_loop_queue:
                QTimer.singleShot(400, self._process_auto_loop_queue)

        self._start_auto_binh_for_window(window_idx, on_done_callback=on_done)

    def _on_frame_processed(self, window_id: int, state: WindowCardState, crop_img: Optional[np.ndarray]) -> None:
        if window_id > self.active_screen_count:
            return

        # ABSOLUTE HARD LOCK: If mouse is actively moving or window is in cooldown, DO NOT re-trigger!
        if self.is_auto_binh_executing:
            panel = self.panels.get(window_id)
            if panel and crop_img is not None and crop_img.size > 0:
                panel.viewer.set_image(crop_img, [])
            return

        is_auto_game = hasattr(self, "chk_auto_game_timing") and self.chk_auto_game_timing.isChecked()
        if not is_auto_game:
            rem_cooldown = self.window_cooldown_remaining.get(window_id, 0)
            if rem_cooldown > 0:
                panel = self.panels.get(window_id)
                if panel and crop_img is not None and crop_img.size > 0:
                    panel.viewer.set_image(crop_img, [])
                return

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

        # 1. Round cleared / Inter-round waiting state (Game is settling payout, comparing hands, or sweeping table)
        if len(valid_cards) < 10:
            self.has_seen_table_cleared[window_id] = True
            if self.last_binned_hashes.get(window_id, ""):
                panel.lbl_status.setText("⏳ Ván cũ đã dọn (Game đã tính tiền / dọn bàn xong) — Đang chờ chia bài ván mới...")
                panel.lbl_status.setStyleSheet("color: #FF9F0A; font-weight: 600;")
                panel.btn_auto_binh.setText("⏳ Đang chờ chia bài mới...")
                panel.btn_auto_binh.setStyleSheet("background-color: #3A3A3C; color: #8E8E93;")
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

                # Trigger condition:
                # Either we observed inter-round clearing (< 10 cards) + 2 stable frames,
                # OR table stabilized on 13 brand-new cards across >= 3 frames
                can_trigger = (self.has_seen_table_cleared.get(window_id, False) and stable_cnt >= 2) or (stable_cnt >= 3)
                if can_trigger:
                    if self.window_current_hashes.get(window_id, "") != curr_hash:
                        self.window_current_hashes[window_id] = curr_hash
                        self.window_round_counters[window_id] = self.window_round_counters.get(window_id, 0) + 1
                        self.window_round_start_times[window_id] = time.time()
                        r_num = self.window_round_counters[window_id]
                        panel.set_round(r_num, is_new=True)
                        panel.lbl_status.setText(f"🎯 Phát hiện Ván mới #{r_num}! Đã nhận diện đủ 13 lá — Binh bài ngay!")
                        panel.lbl_status.setStyleSheet("color: #64D2FF; font-weight: bold;")

                    # Enable button for manual or visual confirmation
                    r_num = self.window_round_counters.get(window_id, 1)
                    panel.btn_auto_binh.setEnabled(True)
                    panel.btn_auto_binh.setText(f"⚡ Tự Động Binh Bài (Ván #{r_num})")
                    panel.btn_auto_binh.setStyleSheet(
                        "background-color: #30D158; color: #000000; font-weight: bold; font-size: 12px; border-radius: 6px; padding: 6px;"
                    )

                    # If Auto-Loop is active and solution is already ready, queue it!
                    if self.is_auto_loop_enabled and panel.last_partition is not None:
                        if window_id not in self.auto_loop_queue:
                            self.auto_loop_queue.append(window_id)
                        self._process_auto_loop_queue()

    def _evaluate_table_strategy(self) -> None:
        """Executes table-wide collaborative deduction of 4th opponent hand and counter-strategy."""
        if self.active_screen_count < 3:
            return

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
        if window_id > self.active_screen_count:
            return
        if self.is_auto_binh_executing:
            return
        is_auto_game = hasattr(self, "chk_auto_game_timing") and self.chk_auto_game_timing.isChecked()
        if not is_auto_game and self.window_cooldown_remaining.get(window_id, 0) > 0:
            return

        if window_id in self.panels:
            panel = self.panels[window_id]
            # Only update standard solution if not in active counter-adapted mode
            if not hasattr(panel, "lbl_opp_outcome") or "BẮT SẬP" not in panel.lbl_opp_outcome.text():
                panel.update_solution(solution)

            # In Auto-Loop mode: check if this window has an un-binned new hand ready
            curr_hash = self.window_current_hashes.get(window_id, "")
            last_binned = self.last_binned_hashes.get(window_id, "")
            if curr_hash and curr_hash != last_binned:
                if self.is_auto_loop_enabled:
                    if window_id not in self.auto_loop_queue:
                        self.auto_loop_queue.append(window_id)
                    self._process_auto_loop_queue()

    def _on_auto_binh_clicked(self, window_idx: int) -> None:
        """Executes auto-binh arrangement moves on a single window."""
        self._start_auto_binh_for_window(window_idx, on_done_callback=None)

    def _on_auto_binh_all_clicked(self) -> None:
        """Sequentially executes auto-binh across all active windows in alternating order (1 -> 2 -> 3)."""
        ready_indices: List[int] = []
        for i in range(1, self.active_screen_count + 1):
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
        if len(ready_indices) == 1:
            self.btn_auto_binh_all.setText("⏳ Đang tự động binh bài...")
        else:
            self.btn_auto_binh_all.setText(f"⏳ Đang luân phiên binh {len(ready_indices)} bàn...")
        self._pending_alternating_windows = list(ready_indices)
        self._execute_next_alternating_window()

    def _execute_next_alternating_window(self) -> None:
        if not self._pending_alternating_windows:
            self.btn_auto_binh_all.setEnabled(True)
            self.btn_auto_binh_all.setText(self._get_auto_binh_all_text())
            return

        window_idx = self._pending_alternating_windows.pop(0)

        def on_window_done(success: bool, msg: str) -> None:
            if self._pending_alternating_windows:
                # 400ms pause before activating next window to simulate natural delay
                QTimer.singleShot(400, self._execute_next_alternating_window)
            else:
                self.btn_auto_binh_all.setEnabled(True)
                self.btn_auto_binh_all.setText(self._get_auto_binh_all_text())

        self._start_auto_binh_for_window(window_idx, on_done_callback=on_window_done)

    def _start_auto_binh_for_window(
        self, window_idx: int, on_done_callback: Optional[Callable[[bool, str], None]] = None
    ) -> None:
        """Executes auto-binh arrangement moves on the selected game window using GestureManager with Hard Safety Guards."""
        panel = self.panels.get(window_idx)
        if not panel or not panel.last_partition or not panel.last_detected_cards:
            msg = "⛔ KHÓA BINH: Cần phát hiện đủ 13 lá bài và có kết quả xếp bài hợp lệ để tự động binh!"
            if on_done_callback is None:
                QMessageBox.warning(self, "Chưa đủ dữ liệu", msg)
            else:
                on_done_callback(False, msg)
            return

        # COOLDOWN LOCK CHECK: Cannot start auto-binh if window is waiting for next round in manual timer mode
        is_auto_game = hasattr(self, "chk_auto_game_timing") and self.chk_auto_game_timing.isChecked()
        if not is_auto_game and self.window_cooldown_remaining.get(window_idx, 0) > 0:
            rem = self.window_cooldown_remaining[window_idx]
            panel.lbl_status.setText(f"⏳ Cửa sổ đang khóa chờ ván mới (còn {rem}s)...")
            if on_done_callback:
                on_done_callback(False, f"Đang trong thời gian chờ ván mới (còn {rem}s)")
            return

        existing_worker = self._auto_binh_workers.get(window_idx)
        if existing_worker:
            if existing_worker.isRunning():
                panel.lbl_status.setText("⏳ Đang thực hiện xếp bài, vui lòng chờ...")
                return
            else:
                try:
                    existing_worker.quit()
                    existing_worker.wait(500)
                    existing_worker.deleteLater()
                except Exception:
                    pass
                self._auto_binh_workers[window_idx] = None

        # HARD SAFETY CHECK 1: Must strictly have exactly 13 detected cards
        if len(panel.last_detected_cards) != 13:
            msg = f"⛔ KHÓA BINH: Cửa sổ #{window_idx} phát hiện {len(panel.last_detected_cards)}/13 lá! Phải đủ 13 lá để tránh binh thủng!"
            panel.lbl_status.setText(msg)
            panel.lbl_status.setStyleSheet("color: #FF453A; font-weight: bold;")
            if on_done_callback is None:
                QMessageBox.warning(self, "Chưa đủ 13 lá", msg)
            else:
                on_done_callback(False, msg)
            return

        # HARD SAFETY CHECK 2: Validate arrangement is not a foul hand
        from app.core.evaluator import Evaluator
        if Evaluator.is_foul(
            panel.last_partition.front_eval,
            panel.last_partition.middle_eval,
            panel.last_partition.back_eval,
        ):
            msg = f"⛔ DỪNG KHẨN CẤP: Thế bài vi phạm luật Mậu Binh (Binh lủng)! Đã hủy binh để bảo vệ tài khoản!"
            panel.lbl_status.setText(msg)
            panel.lbl_status.setStyleSheet("color: #FF453A; font-weight: bold;")
            if on_done_callback:
                on_done_callback(False, msg)
            else:
                QMessageBox.critical(self, "Phát hiện binh lủng", msg)
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
            self._finalize_round_and_lockdown(window_idx, panel, on_done_callback, verification_status="TỐI ƯU")
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
        self.is_auto_binh_executing = True

        target_partition = panel.last_partition

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
            try:
                worker.quit()
                worker.wait(500)
            except Exception:
                pass

            if not success:
                panel.btn_auto_binh.setEnabled(True)
                panel.btn_auto_binh.setText("⚡ Tự Động Binh Bài")
                panel.lbl_status.setText(msg)
                panel.lbl_status.setStyleSheet("color: #FF453A; font-weight: bold;")
                self.is_auto_binh_executing = False
                if on_done_callback:
                    on_done_callback(False, msg)
                return

            # Perform Post-Binh Verification
            panel.lbl_status.setText("🔍 Đang hậu kiểm tra kết quả bài trên bàn cược...")
            panel.lbl_status.setStyleSheet("color: #64D2FF; font-weight: bold;")
            QTimer.singleShot(450, lambda: self._verify_post_binh_result(window_idx, target_partition, on_done_callback))

        worker.step_started.connect(on_step)
        worker.finished_result.connect(on_finished)
        worker.start()

    def _verify_post_binh_result(
        self,
        window_idx: int,
        target_partition: HandArrangement,
        on_done_callback: Optional[Callable[[bool, str], None]] = None,
    ) -> None:
        """Post-Binh verification: Captures table, verifies card layout, and validates Mậu Binh legal hierarchy."""
        panel = self.panels.get(window_idx)
        if not panel:
            self.is_auto_binh_executing = False
            if on_done_callback:
                on_done_callback(True, "Binh hoàn tất")
            return

        combo = getattr(self, f"combo_w{window_idx}", None)
        selected_id = combo.currentData() if combo else None
        if not selected_id:
            panel.lbl_status.setText("✓ Đã hoàn tất xếp bài (Không có cửa sổ để hậu kiểm)")
            panel.lbl_status.setStyleSheet("color: #30D158; font-weight: bold;")
            self._finalize_round_and_lockdown(window_idx, panel, on_done_callback)
            return

        img = ScreenCapture.capture_window_by_id(selected_id)
        if img is None or img.size == 0:
            panel.lbl_status.setText("✓ Đã xếp bài xong (Không chụp được frame hậu kiểm)")
            panel.lbl_status.setStyleSheet("color: #30D158; font-weight: bold;")
            self._finalize_round_and_lockdown(window_idx, panel, on_done_callback)
            return

        detected_cards, _ = recognize_cards_pipeline(
            img,
            detector=self.detector,
            recognizer=self.recognizer,
        )

        state = WindowCardState(
            window_id=window_idx,
            detected_cards=detected_cards,
            status=f"POST_VERIFIED_{len(detected_cards)}_CARDS",
        )
        panel.viewer.set_image(img, detected_cards)

        verification_status = ""
        if len(detected_cards) == 13:
            sorted_dets = sorted(detected_cards, key=lambda d: d.bbox[1])
            f_cards = [d.card for d in sorted(sorted_dets[0:3], key=lambda d: d.bbox[0]) if d.card]
            m_cards = [d.card for d in sorted(sorted_dets[3:8], key=lambda d: d.bbox[0]) if d.card]
            b_cards = [d.card for d in sorted(sorted_dets[8:13], key=lambda d: d.bbox[0]) if d.card]

            if len(f_cards) == 3 and len(m_cards) == 5 and len(b_cards) == 5:
                from app.core.evaluator import Evaluator
                f_eval = Evaluator.evaluate_front(f_cards)
                m_eval = Evaluator.evaluate_five(m_cards)
                b_eval = Evaluator.evaluate_five(b_cards)
                is_foul = Evaluator.is_foul(f_eval, m_eval, b_eval)

                if is_foul:
                    panel.lbl_status.setText("⚠️ CẢNH BÁO HẬU KIỂM: Phát hiện thế bài có dấu hiệu binh lủng! Hãy kiểm tra lại bàn chơi!")
                    panel.lbl_status.setStyleSheet("color: #FF453A; font-weight: bold;")
                    self.is_auto_binh_executing = False
                    if on_done_callback:
                        on_done_callback(False, "Cảnh báo hậu kiểm: Binh lủng")
                    return
                else:
                    verification_status = "HẬU KIỂM CHUẨN LUẬT"
                    panel.lbl_status.setText("✅ ĐÃ HẬU KIỂM: 3 Chi chuẩn luật 100% không lủng (Chi 1 ≤ Chi 2 ≤ Chi 3)")
                    panel.lbl_status.setStyleSheet("color: #30D158; font-weight: bold;")
            else:
                panel.lbl_status.setText("✅ ĐÃ BINH BÀI XONG: Đã kéo xếp các lá bài thành công")
                panel.lbl_status.setStyleSheet("color: #30D158; font-weight: bold;")
        else:
            panel.lbl_status.setText(f"✓ ĐÃ BINH BÀI XONG: Hậu kiểm nhận diện {len(detected_cards)}/13 lá")
            panel.lbl_status.setStyleSheet("color: #30D158; font-weight: bold;")

        self._finalize_round_and_lockdown(window_idx, panel, on_done_callback, verification_status=verification_status)

    def _finalize_round_and_lockdown(
        self,
        window_idx: int,
        panel: SingleWindowPanel,
        on_done_callback: Optional[Callable[[bool, str], None]] = None,
        verification_status: str = "",
    ) -> None:
        """Applies post-round cooldown lockdown and updates round badges and counters."""
        curr_hash = CardStateManager.compute_position_invariant_hash(panel.last_detected_cards)
        self.last_binned_hashes[window_idx] = curr_hash
        self.has_seen_table_cleared[window_idx] = False
        r_num = self.window_round_counters.get(window_idx, 1)
        panel.set_round(r_num, is_completed=True)

        self.total_binned_rounds += 1
        self.lbl_loop_counter.setText(f"Đã binh: {self.total_binned_rounds} ván")

        is_auto_game = hasattr(self, "chk_auto_game_timing") and self.chk_auto_game_timing.isChecked()

        if is_auto_game:
            # Automatic game rhythm mode: Zero artificial timer freeze!
            self.window_cooldown_remaining[window_idx] = 0
            panel.btn_auto_binh.setEnabled(False)
            panel.btn_auto_binh.setText("⏳ Chờ game tính tiền & chia bài...")
            panel.btn_auto_binh.setStyleSheet("background-color: #3A3A3C; color: #8E8E93;")
            if "HẬU KIỂM" in verification_status:
                panel.lbl_status.setText(f"✅ ĐÃ HẬU KIỂM VÁN #{r_num}: Chuẩn luật 100% không lủng — Đang theo dõi game so bài & cộng tiền...")
            elif "TỐI ƯU" in verification_status:
                panel.lbl_status.setText(f"✅ BÀI ĐÃ TỐI ƯU VÁN #{r_num} — Đang theo dõi game so bài & cộng tiền...")
            else:
                panel.lbl_status.setText(f"✅ ĐÃ BINH XONG VÁN #{r_num} — Đang theo dõi game so bài & cộng tiền...")
            panel.lbl_status.setStyleSheet("color: #30D158; font-weight: bold;")
        else:
            round_duration = self.spin_round_time.value()
            cooldown_wait = self.spin_cooldown.value()
            start_ts = self.window_round_start_times.get(window_idx, 0.0)
            elapsed = time.time() - start_ts if start_ts > 0 else 0.0
            rem_round = max(0, int(round_duration - elapsed))
            total_lock_time = rem_round + cooldown_wait
            self.window_cooldown_remaining[window_idx] = total_lock_time

            panel.btn_auto_binh.setEnabled(False)
            panel.btn_auto_binh.setText(f"⏳ Chờ ván mới ({total_lock_time}s)")
            panel.btn_auto_binh.setStyleSheet("background-color: #3A3A3C; color: #8E8E93;")
            if "HẬU KIỂM" in verification_status:
                panel.lbl_status.setText(f"✅ ĐÃ HẬU KIỂM VÁN #{r_num}: Chuẩn luật 100% không lủng — Khóa đợi ván mới (còn {total_lock_time}s)...")
            elif "TỐI ƯU" in verification_status:
                panel.lbl_status.setText(f"✅ BÀI ĐÃ TỐI ƯU VÁN #{r_num} — Khóa đợi ván mới (còn {total_lock_time}s)...")
            else:
                panel.lbl_status.setText(f"✅ ĐÃ BINH XONG VÁN #{r_num} — Khóa đợi ván mới (còn {total_lock_time}s)...")
            panel.lbl_status.setStyleSheet("color: #30D158; font-weight: bold;")

        self.is_auto_binh_executing = False

        if on_done_callback:
            on_done_callback(True, "Binh và hậu kiểm hoàn tất")

    def closeEvent(self, event) -> None:
        """Ensures all scanning loops, cooldown timers, and gesture workers are stopped cleanly."""
        if hasattr(self, "_cooldown_timer") and self._cooldown_timer.isActive():
            self._cooldown_timer.stop()
        self._stop_bot()
        self.is_auto_loop_enabled = False
        self.auto_loop_queue.clear()
        for wid, worker in list(self._auto_binh_workers.items()):
            if worker:
                if worker.isRunning():
                    worker.stop()
                    worker.wait(1000)
                try:
                    worker.deleteLater()
                except Exception:
                    pass
        self._auto_binh_workers.clear()
        super().closeEvent(event)
