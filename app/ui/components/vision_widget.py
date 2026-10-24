"""Computer Vision screen capture and card recognition UI component."""

from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.card import Card, CardParser
from app.ui.components.card_widget import CardWidget
from app.vision.card_detector import CardDetector
from app.vision.card_recognizer import CardRecognizer, DetectedCard
from app.vision.recognition_validator import RecognitionValidator
from app.vision.screen_capture import ScreenCapture


class VisionWidget(QWidget):
    """Component for interactive screen capture, file loading, and card verification."""

    cards_confirmed = Signal(list)  # Emits list[Card] when 13 valid cards confirmed

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.detector = CardDetector()
        self.recognizer = CardRecognizer()
        self.current_image: Optional[np.ndarray] = None
        self.detected_cards: List[DetectedCard] = []
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Action Buttons Header
        btn_layout = QHBoxLayout()
        self.btn_capture = QPushButton("📷 Chụp vùng màn hình (macOS)")
        self.btn_capture.setFixedHeight(36)
        self.btn_capture.clicked.connect(self._on_capture_screen)
        btn_layout.addWidget(self.btn_capture)

        self.btn_open_file = QPushButton("📂 Mở file ảnh...", objectName="SecondaryBtn")
        self.btn_open_file.setFixedHeight(36)
        self.btn_open_file.clicked.connect(self._on_open_file)
        btn_layout.addWidget(self.btn_open_file)

        btn_layout.addStretch()

        self.btn_recognize = QPushButton("🔍 Nhận diện bài")
        self.btn_recognize.setFixedHeight(36)
        self.btn_recognize.setEnabled(False)
        self.btn_recognize.clicked.connect(self._on_recognize)
        btn_layout.addWidget(self.btn_recognize)

        main_layout.addLayout(btn_layout)

        # Image Preview Box
        box_preview = QGroupBox("Xem trước ảnh màn hình")
        layout_preview = QVBoxLayout(box_preview)

        self.lbl_image_preview = QLabel("Chưa có ảnh. Bấm 'Chụp vùng màn hình' hoặc 'Mở file ảnh'.")
        self.lbl_image_preview.setAlignment(Qt.AlignCenter)
        self.lbl_image_preview.setMinimumHeight(220)
        self.lbl_image_preview.setStyleSheet(
            "background-color: #141414; border: 1px dashed #3A3A3C; border-radius: 6px; color: #8E8E93;"
        )
        layout_preview.addWidget(self.lbl_image_preview)
        main_layout.addWidget(box_preview)

        # Detected Cards Result Box
        box_cards = QGroupBox("Kết quả nhận diện bài (Cho phép sửa thủ công)")
        layout_cards = QVBoxLayout(box_cards)

        self.lbl_validation_msg = QLabel("Chưa quét bài.")
        self.lbl_validation_msg.setStyleSheet("font-weight: 600; color: #8E8E93;")
        layout_cards.addWidget(self.lbl_validation_msg)

        # Scroll Area for detected cards
        self.scroll_cards = QScrollArea()
        self.scroll_cards.setWidgetResizable(True)
        self.scroll_cards.setFixedHeight(120)
        self.scroll_cards.setStyleSheet("background-color: #1E1E1E; border: none;")

        self.cards_container = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll_cards.setWidget(self.cards_container)
        layout_cards.addWidget(self.scroll_cards)

        # Confirmation Action
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        self.btn_confirm = QPushButton("Xác nhận & Chuyển sang Xếp bài")
        self.btn_confirm.setFixedHeight(38)
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self._on_confirm_cards)
        footer_layout.addWidget(self.btn_confirm)

        layout_cards.addLayout(footer_layout)
        main_layout.addWidget(box_cards)

    def _on_capture_screen(self) -> None:
        try:
            img = ScreenCapture.capture_interactive_region()
            if img is not None:
                self.set_image(img)
        except PermissionError as e:
            QMessageBox.warning(
                self,
                "Yêu cầu quyền Screen Recording",
                f"{e}\n\nHãy mở System Settings -> Privacy & Security -> Screen Recording để cấp quyền.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi chụp màn hình", str(e))

    def _on_open_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file ảnh bàn bài", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
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

        # Render preview pixmap
        h, w, ch = image.shape
        bytes_per_line = ch * w
        # OpenCV is BGR, convert to RGB for Qt
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)

        # Scale down if large
        scaled_pix = pix.scaled(
            self.lbl_image_preview.width(), 260, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.lbl_image_preview.setPixmap(scaled_pix)

    def _on_recognize(self) -> None:
        if self.current_image is None:
            return

        # 1. Detect candidate card crops
        crops = self.detector.detect_cards(self.current_image)
        if not crops:
            # Fallback if contours not card-shaped: split image into 13 horizontal/vertical slices
            QMessageBox.information(
                self,
                "Thông báo",
                "Không tự động tìm thấy khung viền 13 lá. "
                "Bạn có thể dùng tab Nhập bài thủ công hoặc kiểm tra model nhận diện.",
            )
            return

        # 2. Run recognition
        self.detected_cards = self.recognizer.recognize_all(crops)
        self._display_detected_cards()

    def _display_detected_cards(self) -> None:
        # Clear existing card widgets
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for idx, det in enumerate(self.detected_cards):
            card_widget = CardWidget(card=det.card, width=46, height=66, selectable=False)
            self.cards_layout.addWidget(card_widget)

        self.cards_layout.addStretch()

        # Validate
        report = RecognitionValidator.validate(self.detected_cards)
        self.lbl_validation_msg.setText(report.message)
        if report.is_valid:
            self.lbl_validation_msg.setStyleSheet("color: #30D158; font-weight: 600;")
            self.btn_confirm.setEnabled(True)
        else:
            self.lbl_validation_msg.setStyleSheet("color: #FF9F0A; font-weight: 600;")
            self.btn_confirm.setEnabled(False)

    def _on_confirm_cards(self) -> None:
        cards = [d.card for d in self.detected_cards if d.card is not None]
        if len(cards) == 13:
            self.cards_confirmed.emit(cards)
