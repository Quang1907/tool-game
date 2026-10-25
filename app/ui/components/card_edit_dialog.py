"""Card Confirmation and Correction Dialog with image crop preview, reference library saving, and 52-card selector."""

from __future__ import annotations
from typing import Optional
import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.card import Card, Rank, Suit
from app.vision.card_recognizer import DetectedCard
from app.vision.card_reference_library import CardReferenceLibrary


class CardEditDialog(QDialog):
    """Comprehensive Card Confirmation & Correction Dialog allowing inspection of raw crop,
    prediction breakdown, alternative candidates, manual correction, and reference sample saving.
    """

    def __init__(
        self,
        current_card: Optional[Card] = None,
        detected_card: Optional[DetectedCard] = None,
        reference_library: Optional[CardReferenceLibrary] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Xác nhận & Sửa kết quả lá bài")
        self.resize(720, 480)
        self.setMinimumSize(660, 420)

        self.detected_card: Optional[DetectedCard] = detected_card
        self.reference_library: Optional[CardReferenceLibrary] = reference_library or CardReferenceLibrary()

        # Initialize selected card from detected_card or current_card
        if detected_card and detected_card.card:
            self.selected_card: Optional[Card] = detected_card.card
        else:
            self.selected_card = current_card

        self.is_confirmed: bool = False
        self.saved_as_reference: bool = False
        self.deleted_reference: bool = False

        self._card_buttons: dict[str, QPushButton] = {}
        self._init_ui()
        self._highlight_selected_card()

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        # =====================================================================
        # LEFT PANEL: Crop Image, Prediction Breakdown & Alternatives
        # =====================================================================
        left_panel = QVBoxLayout()
        left_panel.setSpacing(8)

        lbl_crop_title = QLabel("Ảnh chụp thực tế lá bài:")
        lbl_crop_title.setStyleSheet("font-weight: 700; color: #0A84FF; font-size: 13px;")
        left_panel.addWidget(lbl_crop_title)

        # Card crop image viewer
        self.lbl_crop_img = QLabel()
        self.lbl_crop_img.setAlignment(Qt.AlignCenter)
        self.lbl_crop_img.setFixedSize(140, 196)
        self.lbl_crop_img.setStyleSheet(
            "background-color: #1C1C1E; border: 2px solid #3A3A3C; border-radius: 8px; padding: 4px;"
        )
        self._render_crop_image()
        left_panel.addWidget(self.lbl_crop_img, alignment=Qt.AlignCenter)

        # Prediction details box
        box_pred = QFrame()
        box_pred.setStyleSheet("background-color: #2C2C2E; border-radius: 6px; padding: 6px;")
        layout_pred = QVBoxLayout(box_pred)
        layout_pred.setSpacing(4)
        layout_pred.setContentsMargins(8, 6, 8, 6)

        pred_title = QLabel("Dự đoán của hệ thống:")
        pred_title.setStyleSheet("font-weight: 700; font-size: 11px; color: #8E8E93;")
        layout_pred.addWidget(pred_title)

        # Predicted Card Badge
        pred_str = self.detected_card.card.unicode_name if (self.detected_card and self.detected_card.card) else "Unknown"
        conf_pct = int(self.detected_card.confidence * 100) if self.detected_card else 0
        self.lbl_pred_badge = QLabel(f"Lá bài: {pred_str} ({conf_pct}%)")
        color = "#30D158" if conf_pct >= 75 else ("#FF9F0A" if conf_pct >= 55 else "#FF453A")
        self.lbl_pred_badge.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {color};")
        layout_pred.addWidget(self.lbl_pred_badge)

        # Source / Status
        status_text = "Nguồn: Thuật toán nhận diện"
        if self.detected_card and self.detected_card.is_reference_match:
            status_text = "Nguồn: Thư viện ảnh mẫu đã xác nhận"
        elif self.detected_card and self.detected_card.is_uncertain:
            status_text = f"Nghi ngờ: {self.detected_card.uncertain_reason or 'Cần xác nhận'}"
        self.lbl_source = QLabel(status_text)
        self.lbl_source.setWordWrap(True)
        self.lbl_source.setStyleSheet("font-size: 11px; color: #8E8E93;")
        layout_pred.addWidget(self.lbl_source)

        # Alternative Candidates
        if self.detected_card and self.detected_card.alternative_candidates:
            alts_str = ", ".join([f"{c[0]}: {int(c[1]*100)}%" for c in self.detected_card.alternative_candidates[:3]])
            lbl_alts = QLabel(f"Dự đoán phụ: {alts_str}")
            lbl_alts.setStyleSheet("font-size: 10px; color: #64D2FF; font-style: italic;")
            layout_pred.addWidget(lbl_alts)

        # Existing samples in reference library
        if self.reference_library and self.selected_card:
            code = f"{self.selected_card.rank.char}{self.selected_card.suit.char.upper()}"
            existing_count = len(self.reference_library.get_references_for_card(code))
            self.lbl_ref_count = QLabel(f"Thư viện đã có: {existing_count} mẫu của {code}")
            self.lbl_ref_count.setStyleSheet("font-size: 10px; color: #30D158;")
            layout_pred.addWidget(self.lbl_ref_count)
        else:
            self.lbl_ref_count = QLabel("Thư viện mẫu: 0 mẫu")
            self.lbl_ref_count.setStyleSheet("font-size: 10px; color: #8E8E93;")
            layout_pred.addWidget(self.lbl_ref_count)

        left_panel.addWidget(box_pred)
        left_panel.addStretch()

        main_layout.addLayout(left_panel, stretch=2)

        # =====================================================================
        # RIGHT PANEL: 52-Card Grid Selector & Actions
        # =====================================================================
        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)

        # Header & Search
        header_layout = QHBoxLayout()
        header_title = QLabel("Chọn lá bài chính xác:")
        header_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        header_layout.addWidget(header_title)

        header_layout.addStretch()

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Tìm nhanh (vd: AS, 10H)...")
        self.input_search.setFixedWidth(150)
        self.input_search.textChanged.connect(self._on_search_text_changed)
        header_layout.addWidget(self.input_search)

        right_panel.addLayout(header_layout)

        # 52 Cards Grid
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(3)
        grid.setContentsMargins(0, 0, 0, 0)

        suits = [Suit.SPADES, Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS]
        ranks = [
            Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX,
            Rank.SEVEN, Rank.EIGHT, Rank.NINE, Rank.TEN,
            Rank.JACK, Rank.QUEEN, Rank.KING, Rank.ACE
        ]

        for row_idx, suit in enumerate(suits):
            suit_lbl = QLabel(f"{suit.symbol}")
            is_red = suit in (Suit.HEARTS, Suit.DIAMONDS)
            suit_color = "#FF453A" if is_red else "#FFFFFF"
            suit_lbl.setStyleSheet(f"font-weight: 700; font-size: 16px; color: {suit_color}; min-width: 18px;")
            grid.addWidget(suit_lbl, row_idx, 0, Qt.AlignCenter)

            for col_idx, rank in enumerate(ranks):
                card = Card(rank, suit)
                code = f"{rank.char}{suit.char.upper()}"
                btn = QPushButton(f"{rank.char}")
                btn.setFixedSize(34, 40)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda _, c=card: self._select_card(c))

                self._card_buttons[code] = btn
                grid.addWidget(btn, row_idx, col_idx + 1)

        self._refresh_card_buttons_style()
        right_panel.addWidget(grid_widget)

        # Action Buttons
        right_panel.addSpacing(6)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        # 1. Confirm Card (Chỉ xác nhận cho ván này)
        self.btn_confirm = QPushButton("✅ Xác nhận lá này")
        self.btn_confirm.setFixedHeight(36)
        self.btn_confirm.setStyleSheet(
            "background-color: #0A84FF; color: white; font-weight: 700; border-radius: 6px; padding: 0 12px;"
        )
        self.btn_confirm.clicked.connect(self._on_confirm_clicked)
        actions_layout.addWidget(self.btn_confirm)

        # 2. Save as Reference (Lưu ảnh vào thư viện mẫu để lần sau tự nhận diện đúng)
        self.btn_save_ref = QPushButton("💾 Lưu làm ảnh mẫu")
        self.btn_save_ref.setFixedHeight(36)
        self.btn_save_ref.setStyleSheet(
            "background-color: #30D158; color: white; font-weight: 700; border-radius: 6px; padding: 0 12px;"
        )
        self.btn_save_ref.setToolTip("Lưu ảnh crop này vào thư viện ảnh mẫu đã xác nhận để các lần quét sau nhận diện đúng")
        self.btn_save_ref.clicked.connect(self._on_save_as_reference_clicked)
        actions_layout.addWidget(self.btn_save_ref)

        # 3. Delete existing references for this card
        self.btn_delete_ref = QPushButton("🗑️ Xóa mẫu")
        self.btn_delete_ref.setFixedHeight(36)
        self.btn_delete_ref.setStyleSheet(
            "background-color: #3A3A3C; color: #FF453A; font-weight: 600; border-radius: 6px; padding: 0 10px;"
        )
        self.btn_delete_ref.clicked.connect(self._on_delete_references_clicked)
        actions_layout.addWidget(self.btn_delete_ref)

        actions_layout.addStretch()

        # 4. Cancel
        self.btn_cancel = QPushButton("Bỏ qua", objectName="SecondaryBtn")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.clicked.connect(self.reject)
        actions_layout.addWidget(self.btn_cancel)

        right_panel.addLayout(actions_layout)

        main_layout.addLayout(right_panel, stretch=5)

    def _render_crop_image(self) -> None:
        """Renders raw card crop into QLabel with proper aspect ratio."""
        if self.detected_card is None or self.detected_card.raw_crop is None or self.detected_card.raw_crop.size == 0:
            self.lbl_crop_img.setText("Không có ảnh crop")
            return

        img = self.detected_card.raw_crop
        h, w = img.shape[:2]
        if len(img.shape) == 2:
            rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(132, 188, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_crop_img.setPixmap(scaled)

    def _select_card(self, card: Card) -> None:
        """User clicked a card button in the 52-card selector."""
        self.selected_card = card
        self._highlight_selected_card()

        # Update reference count label
        if self.reference_library:
            code = f"{card.rank.char}{card.suit.char.upper()}"
            refs = self.reference_library.get_references_for_card(code)
            self.lbl_ref_count.setText(f"Thư viện đã có: {len(refs)} mẫu của {code}")
            self.lbl_ref_count.setStyleSheet("font-size: 10px; color: #30D158;" if refs else "font-size: 10px; color: #8E8E93;")

    def _highlight_selected_card(self) -> None:
        """Applies highlight styling to the currently selected card button."""
        if not self.selected_card:
            return
        selected_code = f"{self.selected_card.rank.char}{self.selected_card.suit.char.upper()}"
        self._refresh_card_buttons_style(selected_code)

    def _refresh_card_buttons_style(self, selected_code: Optional[str] = None) -> None:
        for code, btn in self._card_buttons.items():
            is_red = code.endswith("H") or code.endswith("D")
            fg = "#FF453A" if is_red else "#FFFFFF"
            if code == selected_code:
                btn.setStyleSheet(
                    f"font-weight: 800; font-size: 12px; color: {fg}; background-color: #0A84FF; "
                    f"border: 2px solid #FFFFFF; border-radius: 4px;"
                )
            else:
                btn.setStyleSheet(
                    f"font-weight: 700; font-size: 11px; color: {fg}; background-color: #2C2C2E; "
                    f"border: 1px solid #3A3A3C; border-radius: 4px;"
                )

    def _on_search_text_changed(self, text: str) -> None:
        """Filter / select card by typing."""
        val = text.strip().upper()
        if val in self._card_buttons:
            # Found exact card code
            btn = self._card_buttons[val]
            btn.click()

    def _on_confirm_clicked(self) -> None:
        """Accepts the selected card and closes dialog."""
        self.is_confirmed = True
        self.accept()

    def _on_save_as_reference_clicked(self) -> None:
        """Saves current crop to CardReferenceLibrary under the selected card."""
        if not self.selected_card:
            QMessageBox.warning(self, "Chưa chọn lá bài", "Vui lòng chọn lá bài chính xác trước khi lưu làm ảnh mẫu.")
            return

        if self.detected_card is None or self.detected_card.raw_crop is None or self.detected_card.raw_crop.size == 0:
            QMessageBox.warning(self, "Không có ảnh", "Không tìm thấy ảnh crop để lưu làm mẫu.")
            return

        try:
            if self.reference_library is not None:
                ref = self.reference_library.add_reference(
                    image=self.detected_card.raw_crop,
                    card=self.selected_card,
                    source="user_confirmed",
                    metadata={"crop_bbox": list(self.detected_card.bbox)},
                )
                self.saved_as_reference = True
                self.is_confirmed = True
                QMessageBox.information(
                    self,
                    "Đã lưu ảnh mẫu",
                    f"Đã lưu thành công ảnh mẫu cho lá {self.selected_card.unicode_name} ({ref.card_code}).\n"
                    f"Các lần quét tiếp theo sẽ tự động nhận diện chính xác lá bài này!",
                )
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi lưu ảnh mẫu", f"Không thể lưu ảnh mẫu: {e}")

    def _on_delete_references_clicked(self) -> None:
        """Deletes all saved samples for the currently selected card."""
        if not self.selected_card or not self.reference_library:
            return

        code = f"{self.selected_card.rank.char}{self.selected_card.suit.char.upper()}"
        existing = self.reference_library.get_references_for_card(code)
        if not existing:
            QMessageBox.information(self, "Thông báo", f"Chưa có ảnh mẫu nào được lưu cho lá {code}.")
            return

        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa mẫu",
            f"Bạn có chắc chắn muốn xóa toàn bộ {len(existing)} ảnh mẫu đã lưu của lá {self.selected_card.unicode_name}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            count = self.reference_library.delete_references_for_card(code)
            self.deleted_reference = True
            QMessageBox.information(self, "Đã xóa", f"Đã xóa {count} ảnh mẫu của lá {code}.")
            self._select_card(self.selected_card)
