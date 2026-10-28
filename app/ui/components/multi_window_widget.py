"""Multi-Window Bot Widget: 3-window simultaneous game monitor and analyzer on macOS."""

from __future__ import annotations
from typing import Dict, List, Optional
import cv2
import numpy as np
from PySide6.QtCore import Qt, QThread, Signal
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

from app.core.card import Card
from app.core.solver import HandArrangement, Solver
from app.services.multi_window_service import MultiWindowWorker
from app.ui.components.card_widget import CardWidget
from app.ui.components.zoomable_viewer import ZoomableImageViewer
from app.vision.card_detector import CardDetector
from app.vision.card_recognizer import CardRecognizer
from app.vision.card_state import WindowCardState
from app.vision.roi_manager import WindowROI
from app.vision.screen_capture import ScreenCapture
from app.vision.window_manager import WindowItem, WindowManager


class SingleWindowPanel(QGroupBox):
    """Panel displaying live camera ROI, detected cards, and optimal 3-chi arrangement for one game window."""

    def __init__(self, window_idx: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(f"Cửa sổ #{window_idx}", parent)
        self.window_idx = window_idx
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

    def update_state(self, state: WindowCardState, crop_img: Optional[np.ndarray]) -> None:
        """Updates live preview and card list."""
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
            self.viewer.set_image(crop_img, state.detected_cards)

        # Update card thumbnails
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for det in state.detected_cards:
            w = CardWidget(card=det.card, width=36, height=52, selectable=False)
            self.cards_layout.addWidget(w)
        self.cards_layout.addStretch()

    def update_solution(self, partition: HandArrangement) -> None:
        """Displays solved 3-chi hand breakdown."""
        f_names = " ".join(c.unicode_name for c in partition.front)
        m_names = " ".join(c.unicode_name for c in partition.middle)
        b_names = " ".join(c.unicode_name for c in partition.back)

        f_type = partition.front_eval.description
        m_type = partition.middle_eval.description
        b_type = partition.back_eval.description

        self.lbl_chi_front.setText(f"Chi Đầu: {f_names} ({f_type})")
        self.lbl_chi_middle.setText(f"Chi Giữa: {m_names} ({m_type})")
        self.lbl_chi_back.setText(f"Chi Cuối: {b_names} ({b_type})")


class MultiWindowWidget(QWidget):
    """Widget orchestrating simultaneous 3-window game detection on macOS."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.window_manager = WindowManager()
        self.detector = CardDetector()
        self.recognizer = CardRecognizer()
        self.solver = Solver()
        self._thread: Optional[QThread] = None
        self._worker: Optional[MultiWindowWorker] = None
        self.discovered_windows: List[WindowItem] = []
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

        toolbar.addStretch()

        self.lbl_fps = QLabel("FPS: —")
        self.lbl_fps.setStyleSheet("color: #30D158; font-weight: 600; padding: 4px 8px; background: rgba(48,209,88,0.12); border-radius: 4px;")
        toolbar.addWidget(self.lbl_fps)

        self.btn_start = QPushButton("▶ Bắt đầu quét 3 cửa sổ")
        self.btn_start.setFixedHeight(32)
        self.btn_start.clicked.connect(self._toggle_bot)
        toolbar.addWidget(self.btn_start)

        main_layout.addLayout(toolbar)

        # 3 Side-by-side or Grid Panels
        grid = QGridLayout()
        grid.setSpacing(10)

        self.panels: Dict[int, SingleWindowPanel] = {}
        for i in range(1, 4):
            panel = SingleWindowPanel(window_idx=i, parent=self)
            self.panels[i] = panel
            grid.addWidget(panel, 0, i - 1)

        main_layout.addLayout(grid)

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

        # Run Card Detection
        crops = self.detector.detect_cards(img)

        # Run Card Recognition
        detected_cards = self.recognizer.recognize_all(crops)

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

        if len(valid_cards) == 13:
            arrangements = self.solver.solve_heuristic(valid_cards)
            if arrangements:
                panel.update_solution(arrangements[0])
                panel.lbl_status.setText(f"✓ Đã xác nhận [{win_title}]: 13 lá — Đã có gợi ý tối ưu")
                panel.lbl_status.setStyleSheet("color: #30D158; font-weight: 600;")
        elif detected_cards:
            panel.lbl_status.setText(f"✓ Đã kết nối [{win_title}]: Phát hiện {len(detected_cards)} lá (Cần 13 lá)")
            panel.lbl_status.setStyleSheet("color: #0A84FF; font-weight: 600;")
        else:
            panel.lbl_status.setText(f"✓ Đã kết nối [{win_title}]: Đang chờ chia bài...")
            panel.lbl_status.setStyleSheet("color: #FF9F0A; font-weight: 600;")

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
        self._worker = MultiWindowWorker(rois=rois, poll_interval_sec=0.15)
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

    def _on_frame_processed(self, window_id: int, state: WindowCardState, crop_img: Optional[np.ndarray]) -> None:
        if window_id in self.panels:
            self.panels[window_id].update_state(state, crop_img)

    def _on_solution_found(self, window_id: int, solution: HandArrangement) -> None:
        if window_id in self.panels:
            self.panels[window_id].update_solution(solution)
