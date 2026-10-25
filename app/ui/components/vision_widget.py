"""Modern Computer Vision and Screen Capture component for macOS."""

from __future__ import annotations
from typing import List, Optional
import numpy as np
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.card import Card
from app.services.vision_service import VisionWorker
from app.ui.components.card_edit_dialog import CardEditDialog
from app.ui.components.card_reference_manager import CardReferenceManagerDialog
from app.ui.components.card_widget import CardWidget
from app.ui.components.zoomable_viewer import ZoomableImageViewer
from app.vision.card_detector import CardDetector
from app.vision.card_recognizer import CardRecognizer, DetectedCard
from app.vision.card_reference_library import CardReferenceLibrary
from app.vision.recognition_validator import RecognitionValidator
from app.vision.screen_capture import ScreenCapture


class VisionWidget(QWidget):
    """Component for interactive multi-monitor capture, window capture, zooming, and card verification."""

    cards_confirmed = Signal(list)  # Emits list[Card] when 13 valid cards confirmed

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.detector = CardDetector()
        self.reference_library = CardReferenceLibrary()
        self.recognizer = CardRecognizer(reference_library=self.reference_library)
        self.current_image: Optional[np.ndarray] = None
        self.detected_cards: List[DetectedCard] = []

        self._vision_thread: Optional[QThread] = None
        self._vision_worker: Optional[VisionWorker] = None

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # 1. Top Action Toolbar
        toolbar = QHBoxLayout()

        # Multi-monitor selector
        lbl_screen = QLabel("Màn hình:")
        lbl_screen.setStyleSheet("font-weight: 600;")
        toolbar.addWidget(lbl_screen)

        self.combo_screens = QComboBox()
        self._populate_screens()
        toolbar.addWidget(self.combo_screens)

        btn_cap_full = QPushButton("🖥️ Toàn màn hình", objectName="SecondaryBtn")
        btn_cap_full.clicked.connect(self._on_capture_full_screen)
        toolbar.addWidget(btn_cap_full)

        self.btn_cap_window = QPushButton("🪟 Cửa sổ game / app", objectName="SecondaryBtn")
        self.btn_cap_window.clicked.connect(self._on_capture_window)
        toolbar.addWidget(self.btn_cap_window)

        self.btn_cap_region = QPushButton("📷 Chụp vùng tự do (Drag)")
        self.btn_cap_region.clicked.connect(self._on_capture_region)
        toolbar.addWidget(self.btn_cap_region)

        self.btn_open_file = QPushButton("📂 Mở file ảnh...", objectName="SecondaryBtn")
        self.btn_open_file.clicked.connect(self._on_open_file)
        toolbar.addWidget(self.btn_open_file)

        self.btn_ref_manager = QPushButton("📚 Thư viện ảnh mẫu", objectName="SecondaryBtn")
        self.btn_ref_manager.setToolTip("Quản lý 52 lá bài và các ảnh mẫu đã xác nhận")
        self.btn_ref_manager.clicked.connect(self._open_reference_manager)
        toolbar.addWidget(self.btn_ref_manager)

        toolbar.addStretch()

        self.btn_recapture = QPushButton("🔄 Chụp lại", objectName="SecondaryBtn")
        self.btn_recapture.setEnabled(False)
        self.btn_recapture.clicked.connect(self._on_capture_region)
        toolbar.addWidget(self.btn_recapture)

        self.btn_clear_img = QPushButton("❌ Hủy ảnh", objectName="DangerBtn")
        self.btn_clear_img.setEnabled(False)
        self.btn_clear_img.clicked.connect(self._clear_image)
        toolbar.addWidget(self.btn_clear_img)

        main_layout.addLayout(toolbar)

        # 2. Main Content Split (Image Viewer on Left/Center, Controls on Right/Bottom)
        box_viewer = QGroupBox("Xem trước ảnh (Hỗ trợ Zoom & Kéo ảnh)")
        layout_viewer = QVBoxLayout(box_viewer)

        # Viewer toolbar (Zoom In, Zoom Out, Fit, 100%)
        viewer_tools = QHBoxLayout()
        btn_zoom_in = QPushButton("🔍+ Phóng to", objectName="SecondaryBtn")
        btn_zoom_in.clicked.connect(lambda: self.image_viewer.zoom_in())
        viewer_tools.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("🔍- Thu nhỏ", objectName="SecondaryBtn")
        btn_zoom_out.clicked.connect(lambda: self.image_viewer.zoom_out())
        viewer_tools.addWidget(btn_zoom_out)

        btn_fit = QPushButton("↕ Vừa khung", objectName="SecondaryBtn")
        btn_fit.clicked.connect(lambda: self.image_viewer.fit_in_view())
        viewer_tools.addWidget(btn_fit)

        btn_actual = QPushButton("1:1 Kích thước gốc", objectName="SecondaryBtn")
        btn_actual.clicked.connect(lambda: self.image_viewer.zoom_actual_size())
        viewer_tools.addWidget(btn_actual)

        viewer_tools.addStretch()

        # Detection Mode Selector
        viewer_tools.addWidget(QLabel("Chế độ quét:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItems([
            "Tự động tìm khung bài (Auto)",
            "Cắt đều 13 lá ngang (13-Card Row)",
            "Cắt lưới 3 chi 3-5-5 (3-Row Grid)",
        ])
        viewer_tools.addWidget(self.combo_mode)

        self.btn_recognize = QPushButton("🔍 Nhận diện lá bài")
        self.btn_recognize.setFixedHeight(30)
        self.btn_recognize.setEnabled(False)
        self.btn_recognize.clicked.connect(self._start_recognition)
        viewer_tools.addWidget(self.btn_recognize)

        layout_viewer.addLayout(viewer_tools)

        # Zoomable Image Viewer
        self.image_viewer = ZoomableImageViewer()
        self.image_viewer.setMinimumHeight(280)
        layout_viewer.addWidget(self.image_viewer)

        main_layout.addWidget(box_viewer)

        # 3. Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # 4. Results & Editing Section
        box_cards = QGroupBox("Danh sách lá bài đã nhận diện (Click vào lá để sửa thủ công)")
        layout_cards = QVBoxLayout(box_cards)

        self.lbl_validation_msg = QLabel("Chưa có dữ liệu bài.")
        self.lbl_validation_msg.setStyleSheet("font-weight: 600; color: #8E8E93;")
        layout_cards.addWidget(self.lbl_validation_msg)

        # Scroll Area for card thumbnails
        self.scroll_cards = QScrollArea()
        self.scroll_cards.setWidgetResizable(True)
        self.scroll_cards.setFixedHeight(125)
        self.scroll_cards.setStyleSheet("background-color: #1E1E1E; border: none;")

        self.cards_container = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll_cards.setWidget(self.cards_container)
        layout_cards.addWidget(self.scroll_cards)

        # Confirmation Footer
        footer = QHBoxLayout()
        self.lbl_instructions = QLabel("💡 Mẹo: Bấm trực tiếp vào lá bài phía trên để đổi giá trị và lưu làm ảnh mẫu.")
        self.lbl_instructions.setStyleSheet("color: #8E8E93; font-style: italic;")
        footer.addWidget(self.lbl_instructions)

        footer.addStretch()

        self.btn_review_uncertain = QPushButton("⚠️ Duyệt bài nghi ngờ", objectName="SecondaryBtn")
        self.btn_review_uncertain.setToolTip("Duyệt nhanh và xác nhận các lá bài có độ tin cậy thấp hoặc nghi ngờ")
        self.btn_review_uncertain.setEnabled(False)
        self.btn_review_uncertain.clicked.connect(self._review_low_confidence_cards)
        footer.addWidget(self.btn_review_uncertain)

        self.btn_confirm = QPushButton("Xác nhận 13 lá & Chuyển sang Xếp bài")
        self.btn_confirm.setFixedHeight(38)
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self._on_confirm_cards)
        footer.addWidget(self.btn_confirm)

        layout_cards.addLayout(footer)
        main_layout.addWidget(box_cards)

    def _populate_screens(self) -> None:
        """Populates screen dropdown with connected display monitors."""
        self.combo_screens.clear()
        screens = ScreenCapture.get_available_screens()
        for s in screens:
            label = f"{s.name} ({s.width}x{s.height})"
            if s.is_primary:
                label += " [Chính]"
            self.combo_screens.addItem(label, s.index)

    def _on_capture_region(self) -> None:
        try:
            img = ScreenCapture.capture_interactive_region()
            if img is not None:
                self.set_image(img)
        except PermissionError as e:
            self._show_permission_alert(str(e))
        except Exception as e:
            QMessageBox.critical(self, "Lỗi chụp màn hình", str(e))

    def _on_capture_window(self) -> None:
        try:
            img = ScreenCapture.capture_window()
            if img is not None:
                self.set_image(img)
        except PermissionError as e:
            self._show_permission_alert(str(e))
        except Exception as e:
            QMessageBox.critical(self, "Lỗi chụp cửa sổ", str(e))

    def _on_capture_full_screen(self) -> None:
        display_idx = self.combo_screens.currentData() or 1
        try:
            img = ScreenCapture.capture_full_screen(display_index=display_idx)
            if img is not None:
                self.set_image(img)
        except PermissionError as e:
            self._show_permission_alert(str(e))
        except Exception as e:
            QMessageBox.critical(self, "Lỗi chụp toàn màn hình", str(e))

    def _show_permission_alert(self, message: str) -> None:
        QMessageBox.warning(
            self,
            "Yêu cầu quyền Screen Recording",
            f"{message}\n\nHãy vào: System Settings -> Privacy & Security -> Screen Recording.",
        )

    def _on_open_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file ảnh bàn bài", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)"
        )
        if file_path:
            try:
                img = ScreenCapture.load_image_file(file_path)
                self.set_image(img)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi đọc file ảnh", str(e))

    def set_image(self, image: np.ndarray) -> None:
        self.current_image = image
        self.btn_recognize.setEnabled(True)
        self.btn_recapture.setEnabled(True)
        self.btn_clear_img.setEnabled(True)

        self.image_viewer.set_image(image)
        self.lbl_validation_msg.setText("Ảnh đã tải lên. Bấm 'Nhận diện lá bài' để quét.")

    def _clear_image(self) -> None:
        self.current_image = None
        self.detected_cards.clear()
        self.image_viewer._scene.clear()
        self.btn_recognize.setEnabled(False)
        self.btn_recapture.setEnabled(False)
        self.btn_clear_img.setEnabled(False)
        self.btn_confirm.setEnabled(False)
        self._display_detected_cards()
        self.lbl_validation_msg.setText("Chưa có ảnh.")

    def _start_recognition(self) -> None:
        if self.current_image is None:
            return

        mode_idx = self.combo_mode.currentIndex()
        mode_str = "AUTO"
        if mode_idx == 1:
            mode_str = "STRIP_13"
        elif mode_idx == 2:
            mode_str = "GRID_3_5_5"

        self.btn_recognize.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_validation_msg.setText("Đang chạy Computer Vision nhận diện bài...")

        # Setup background thread
        self._vision_thread = QThread()
        self._vision_worker = VisionWorker(
            image=self.current_image,
            detector=self.detector,
            recognizer=self.recognizer,
            mode=mode_str,
        )
        self._vision_worker.moveToThread(self._vision_thread)

        self._vision_thread.started.connect(self._vision_worker.run)
        self._vision_worker.progress.connect(self._on_vision_progress)
        self._vision_worker.finished.connect(self._on_vision_finished)
        self._vision_worker.error.connect(self._on_vision_error)

        self._vision_thread.start()

    def _on_vision_progress(self, current: int, total: int, status: str) -> None:
        self.progress_bar.setValue(current)
        self.lbl_validation_msg.setText(status)

    def _on_vision_finished(self, detected_cards: List[DetectedCard]) -> None:
        if self._vision_thread and self._vision_thread.isRunning():
            self._vision_thread.quit()
            self._vision_thread.wait()

        self.progress_bar.setVisible(False)
        self.btn_recognize.setEnabled(True)
        self.detected_cards = detected_cards

        # Update viewer bounding boxes
        if self.current_image is not None:
            self.image_viewer.set_image(self.current_image, detected_cards)

        self._display_detected_cards()

    def _on_vision_error(self, err_msg: str) -> None:
        if self._vision_thread and self._vision_thread.isRunning():
            self._vision_thread.quit()
            self._vision_thread.wait()

        self.progress_bar.setVisible(False)
        self.btn_recognize.setEnabled(True)
        QMessageBox.critical(self, "Lỗi nhận diện bài", err_msg)
        self.lbl_validation_msg.setText(f"Lỗi: {err_msg}")

    def _display_detected_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        has_uncertain = False
        for idx, det in enumerate(self.detected_cards):
            card_col = QVBoxLayout()
            card_col.setSpacing(2)

            w = CardWidget(card=det.card, width=48, height=70, selectable=True)
            w.clicked.connect(lambda _, i=idx: self._open_card_editor(i))
            card_col.addWidget(w)

            # Badge / Label for confidence & reference match
            conf_pct = int(det.confidence * 100) if det.card else 0
            if det.is_reference_match:
                conf_text = f"{conf_pct}% [Mẫu]"
                conf_color = "#30D158"
            elif det.is_uncertain:
                has_uncertain = True
                conf_text = f"{conf_pct}% [Nghi ngờ]"
                conf_color = "#FF9F0A"
            else:
                conf_text = f"{conf_pct}%"
                conf_color = "#30D158" if det.confidence >= 0.70 else "#FF9F0A"

            conf_lbl = QLabel(conf_text)
            conf_lbl.setAlignment(Qt.AlignCenter)
            conf_lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {conf_color};")
            card_col.addWidget(conf_lbl)

            container = QWidget()
            container.setLayout(card_col)
            self.cards_layout.addWidget(container)

        self.cards_layout.addStretch()

        # Update Review Uncertain button state
        has_low_conf = any(not d.is_verified and d.confidence < 0.70 for d in self.detected_cards)
        self.btn_review_uncertain.setEnabled(has_uncertain or has_low_conf)

        report = RecognitionValidator.validate(self.detected_cards)
        if has_uncertain or has_low_conf:
            self.lbl_validation_msg.setText(f"{report.message} (Có lá bài cần xác nhận, bấm '⚠️ Duyệt bài nghi ngờ')")
            self.lbl_validation_msg.setStyleSheet("color: #FF9F0A; font-weight: 600;")
        else:
            self.lbl_validation_msg.setText(report.message)
            if report.is_valid:
                self.lbl_validation_msg.setStyleSheet("color: #30D158; font-weight: 600;")
            else:
                self.lbl_validation_msg.setStyleSheet("color: #FF9F0A; font-weight: 600;")

        self.btn_confirm.setEnabled(report.is_valid)

    def _open_card_editor(self, index: int) -> None:
        if not (0 <= index < len(self.detected_cards)):
            return

        det = self.detected_cards[index]
        dialog = CardEditDialog(
            current_card=det.card,
            detected_card=det,
            reference_library=self.reference_library,
            parent=self,
        )
        if dialog.exec() and dialog.selected_card:
            # Update detected card
            self.detected_cards[index] = DetectedCard(
                card=dialog.selected_card,
                confidence=1.0,  # Manually verified by user
                bbox=det.bbox,
                raw_crop=det.raw_crop,
                is_verified=True,
                is_reference_match=dialog.saved_as_reference or det.is_reference_match,
                is_uncertain=False,
            )
            # If user saved reference, reload library cache immediately
            if dialog.saved_as_reference:
                self.reference_library.reload_cache()

            # Refresh UI and overlay
            if self.current_image is not None:
                self.image_viewer.set_image(self.current_image, self.detected_cards)
            self._display_detected_cards()

    def _review_low_confidence_cards(self) -> None:
        """Sequential review of low-confidence or uncertain cards."""
        low_indices = [
            i for i, d in enumerate(self.detected_cards)
            if not d.is_verified and (d.confidence < 0.70 or d.is_uncertain or d.card is None)
        ]
        if not low_indices:
            QMessageBox.information(
                self,
                "Hoàn tất duyệt bài",
                "Tất cả các lá bài hiện tại đều có độ tin cậy cao hoặc đã được xác nhận!",
            )
            return

        for idx in low_indices:
            self._open_card_editor(idx)

    def _open_reference_manager(self) -> None:
        """Opens CardReferenceManagerDialog."""
        dialog = CardReferenceManagerDialog(
            reference_library=self.reference_library,
            parent=self,
        )
        dialog.exec()

    def _on_confirm_cards(self) -> None:
        cards = [d.card for d in self.detected_cards if d.card is not None]
        if len(cards) == 13:
            self.cards_confirmed.emit(cards)
            self.cards_confirmed.emit(cards)
