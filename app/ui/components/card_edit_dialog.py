from __future__ import annotations
import logging
from pathlib import Path
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

logger = logging.getLogger(__name__)


class CardContradictionDialog(QDialog):
    """Modal inspection dialog displayed when user's selected card rank strongly contradicts
    the detected visual rank features, preventing accidental mislabeled references.
    """

    def __init__(
        self,
        card_crop: np.ndarray,
        rank_crop: Optional[np.ndarray],
        selected_card: Card,
        predicted_rank: Rank,
        confidence: float,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cảnh báo xung đột nhận diện lá bài")
        self.resize(520, 360)
        self.setStyleSheet("background-color: #1C1C1E; color: #FFFFFF;")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header warning banner
        title_box = QHBoxLayout()
        lbl_warn_icon = QLabel("⚠️")
        lbl_warn_icon.setStyleSheet("font-size: 28px;")
        title_box.addWidget(lbl_warn_icon)

        lbl_title = QLabel("Cảnh báo: Nhãn chọn không khớp với hình ảnh nhận diện!")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FF9F0A;")
        lbl_title.setWordWrap(True)
        title_box.addWidget(lbl_title, stretch=1)
        layout.addLayout(title_box)

        # Content: Side-by-side card preview & comparison
        content_box = QHBoxLayout()
        content_box.setSpacing(16)

        # Left: Actual crop & rank crop
        crops_layout = QVBoxLayout()
        crops_layout.setAlignment(Qt.AlignCenter)
        lbl_card = QLabel()
        CardEditDialog._set_pixmap_to_label(lbl_card, card_crop, 100, 140)
        lbl_card.setStyleSheet("border: 1px solid #3A3A3C; border-radius: 6px;")
        crops_layout.addWidget(lbl_card, alignment=Qt.AlignCenter)

        if rank_crop is not None and rank_crop.size > 0:
            lbl_r = QLabel()
            CardEditDialog._set_pixmap_to_label(lbl_r, rank_crop, 40, 50)
            lbl_r.setStyleSheet("border: 1px solid #FF9F0A; border-radius: 4px;")
            crops_layout.addWidget(lbl_r, alignment=Qt.AlignCenter)
            lbl_r_tag = QLabel("Vùng Rank Crop")
            lbl_r_tag.setStyleSheet("font-size: 10px; color: #8E8E93;")
            crops_layout.addWidget(lbl_r_tag, alignment=Qt.AlignCenter)

        content_box.addLayout(crops_layout)

        # Right: Detail texts
        detail_layout = QVBoxLayout()
        detail_layout.setSpacing(8)

        sel_code = f"{selected_card.rank.char}{selected_card.suit.char.upper()}"
        lbl_info = QLabel(
            f"• <b>Bạn đang chọn:</b> <font color='#0A84FF'>{selected_card.unicode_name} ({sel_code})</font><br>"
            f"• <b>Hệ thống nhận diện rank:</b> <font color='#FF453A'>Rank {predicted_rank.char} ({int(confidence * 100)}% tin cậy)</font><br><br>"
            f"Việc lưu sai nhãn bài vào thư viện mẫu có thể khiến hệ thống "
            f"nhận diện nhầm lẫn các ván bài tiếp theo.<br><br>"
            f"Bạn có chắc chắn muốn lưu ảnh này làm mẫu cho <b>{selected_card.unicode_name} ({sel_code})</b> không?"
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("font-size: 12px; color: #E5E5EA; line-height: 1.4;")
        detail_layout.addWidget(lbl_info)
        content_box.addLayout(detail_layout, stretch=1)

        layout.addLayout(content_box)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_cancel = QPushButton("❌ Hủy & Chọn lại")
        btn_cancel.setStyleSheet(
            "background-color: #2C2C2E; color: #FFFFFF; font-weight: 600; padding: 8px 16px; border-radius: 6px;"
        )
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_proceed = QPushButton("⚠️ Vẫn lưu làm ảnh mẫu")
        btn_proceed.setStyleSheet(
            "background-color: #FF9F0A; color: #000000; font-weight: 700; padding: 8px 16px; border-radius: 6px;"
        )
        btn_proceed.clicked.connect(self.accept)
        btn_layout.addWidget(btn_proceed)

        layout.addLayout(btn_layout)


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
        self._rank_buttons: dict[Rank, QPushButton] = {}
        self._suit_buttons: dict[Suit, QPushButton] = {}
        self._init_ui()
        self._highlight_selected_card()

    @property
    def rank_buttons(self) -> dict[Rank, QPushButton]:
        return self._rank_buttons

    @property
    def suit_buttons(self) -> dict[Suit, QPushButton]:
        return self._suit_buttons

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        # =====================================================================
        # LEFT PANEL: Crop Image, Rank/Suit Crops, Prediction Breakdown & Alternatives
        # =====================================================================
        left_panel = QVBoxLayout()
        left_panel.setSpacing(8)

        lbl_crop_title = QLabel("Ảnh chụp thực tế lá bài:")
        lbl_crop_title.setStyleSheet("font-weight: 700; color: #0A84FF; font-size: 13px;")
        left_panel.addWidget(lbl_crop_title)

        # Side-by-side card comparison (Real crop vs Matched reference sample)
        row_images = QHBoxLayout()
        row_images.setSpacing(6)

        col_crop = QVBoxLayout()
        col_crop.setSpacing(2)
        lbl_c_tag = QLabel("Ảnh Crop Thực Tế")
        lbl_c_tag.setStyleSheet("font-size: 10px; color: #8E8E93;")
        col_crop.addWidget(lbl_c_tag, alignment=Qt.AlignCenter)
        self.lbl_crop_img = QLabel()
        self.lbl_crop_img.setAlignment(Qt.AlignCenter)
        self.lbl_crop_img.setFixedSize(90, 128)
        self.lbl_crop_img.setStyleSheet("background-color: #1C1C1E; border: 1px solid #3A3A3C; border-radius: 6px;")
        col_crop.addWidget(self.lbl_crop_img, alignment=Qt.AlignCenter)
        row_images.addLayout(col_crop)

        col_ref = QVBoxLayout()
        col_ref.setSpacing(2)
        self.lbl_ref_tag = QLabel("Mẫu Đối Chiếu")
        self.lbl_ref_tag.setStyleSheet("font-size: 10px; color: #30D158;")
        col_ref.addWidget(self.lbl_ref_tag, alignment=Qt.AlignCenter)
        self.lbl_matched_ref_img = QLabel()
        self.lbl_matched_ref_img.setAlignment(Qt.AlignCenter)
        self.lbl_matched_ref_img.setFixedSize(90, 128)
        self.lbl_matched_ref_img.setStyleSheet("background-color: #1C1C1E; border: 1px solid #30D158; border-radius: 6px;")
        col_ref.addWidget(self.lbl_matched_ref_img, alignment=Qt.AlignCenter)
        row_images.addLayout(col_ref)

        left_panel.addLayout(row_images)

        # Dedicated Rank Crop and Suit Crop previews
        row_crops = QHBoxLayout()
        row_crops.setSpacing(8)

        box_r = QVBoxLayout()
        box_r.setSpacing(2)
        lbl_r_title = QLabel("Crop Rank")
        lbl_r_title.setStyleSheet("font-size: 10px; color: #8E8E93;")
        box_r.addWidget(lbl_r_title, alignment=Qt.AlignCenter)
        self.lbl_rank_crop = QLabel()
        self.lbl_rank_crop.setFixedSize(44, 44)
        self.lbl_rank_crop.setAlignment(Qt.AlignCenter)
        self.lbl_rank_crop.setStyleSheet("background-color: #1C1C1E; border: 1px solid #3A3A3C; border-radius: 4px;")
        box_r.addWidget(self.lbl_rank_crop, alignment=Qt.AlignCenter)
        row_crops.addLayout(box_r)

        box_s = QVBoxLayout()
        box_s.setSpacing(2)
        lbl_s_title = QLabel("Crop Suit")
        lbl_s_title.setStyleSheet("font-size: 10px; color: #8E8E93;")
        box_s.addWidget(lbl_s_title, alignment=Qt.AlignCenter)
        self.lbl_suit_crop = QLabel()
        self.lbl_suit_crop.setFixedSize(44, 44)
        self.lbl_suit_crop.setAlignment(Qt.AlignCenter)
        self.lbl_suit_crop.setStyleSheet("background-color: #1C1C1E; border: 1px solid #3A3A3C; border-radius: 4px;")
        box_s.addWidget(self.lbl_suit_crop, alignment=Qt.AlignCenter)
        row_crops.addLayout(box_s)

        left_panel.addLayout(row_crops)
        self._render_crop_images()

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
        if self.detected_card and self.detected_card.card:
            pred_str = self.detected_card.card.unicode_name
            conf_pct = int(self.detected_card.confidence * 100)
            self.lbl_pred_badge = QLabel(f"Lá bài: {pred_str} ({conf_pct}%)")
            color = "#30D158" if conf_pct >= 75 else ("#FF9F0A" if conf_pct >= 55 else "#FF453A")
            self.lbl_pred_badge.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {color};")
            layout_pred.addWidget(self.lbl_pred_badge)

            # Detailed Rank and Suit Confidence
            r_conf = int(self.detected_card.rank_confidence * 100)
            s_conf = int(self.detected_card.suit_confidence * 100)
            r_char = self.detected_card.rank_char
            s_char = self.detected_card.suit_char
            self.lbl_rank_suit_conf = QLabel(f"Rank: {r_char} ({r_conf}%) | Suit: {s_char} ({s_conf}%)")
            self.lbl_rank_suit_conf.setStyleSheet("font-size: 11px; font-weight: 600; color: #64D2FF;")
            layout_pred.addWidget(self.lbl_rank_suit_conf)
        else:
            crop_st = getattr(self.detected_card, "crop_status", "NON_CARD_OBJECT") if self.detected_card else "UNKNOWN"
            self.lbl_pred_badge = QLabel(f"Không phải lá bài [{crop_st}]")
            self.lbl_pred_badge.setStyleSheet("font-size: 13px; font-weight: 700; color: #FF453A;")
            layout_pred.addWidget(self.lbl_pred_badge)

            self.lbl_rank_suit_conf = QLabel("Rank: - (Không hợp lệ) | Suit: - (Không hợp lệ)")
            self.lbl_rank_suit_conf.setStyleSheet("font-size: 11px; font-weight: 600; color: #FF453A;")
            layout_pred.addWidget(self.lbl_rank_suit_conf)

        # Source / Status & Similarity
        sim_pct = int((self.detected_card.matched_similarity if self.detected_card else 0) * 100)
        status_text = f"Trạng thái: {self.detected_card.recognition_status if self.detected_card else 'CONFIRMED'}"
        if self.detected_card and self.detected_card.is_reference_match:
            status_text += f" | Mẫu khớp ({sim_pct}%)"
        elif self.detected_card and self.detected_card.is_uncertain:
            status_text += f" | {self.detected_card.uncertain_reason or 'Cần xác nhận'}"
        self.lbl_source = QLabel(status_text)
        self.lbl_source.setWordWrap(True)
        self.lbl_source.setStyleSheet("font-size: 11px; color: #8E8E93;")
        layout_pred.addWidget(self.lbl_source)

        # Bounding box info
        if self.detected_card:
            x, y, w, h = self.detected_card.bbox
            lbl_bbox = QLabel(f"Vị trí: ({x}, {y}) | Size: {w}x{h}")
            lbl_bbox.setStyleSheet("font-size: 10px; color: #8E8E93;")
            layout_pred.addWidget(lbl_bbox)

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
            self.lbl_ref_count.setStyleSheet("font-size: 10px; color: #30D158;" if existing_count else "font-size: 10px; color: #8E8E93;")
        else:
            self.lbl_ref_count = QLabel("Thư viện mẫu: 0 mẫu")
            self.lbl_ref_count.setStyleSheet("font-size: 10px; color: #8E8E93;")
        layout_pred.addWidget(self.lbl_ref_count)

        # Button to view similar reference samples
        self.btn_view_similar = QPushButton("🖼️ Xem ảnh mẫu tương tự", objectName="SecondaryBtn")
        self.btn_view_similar.setFixedHeight(26)
        self.btn_view_similar.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        self.btn_view_similar.clicked.connect(self._on_view_similar_clicked)
        layout_pred.addWidget(self.btn_view_similar)

        left_panel.addWidget(box_pred)
        left_panel.addStretch()

        main_layout.addLayout(left_panel, stretch=2)

        # =====================================================================
        # RIGHT PANEL: Independent Rank/Suit Pickers & 52-Card Grid Selector
        # =====================================================================
        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)

        # Header & Search
        header_layout = QHBoxLayout()
        header_title = QLabel("Chọn lá bài chính xác:")
        header_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        header_layout.addWidget(header_title)

        header_layout.addStretch()

        self.lbl_selected_display = QLabel()
        self.lbl_selected_display.setStyleSheet("font-size: 13px; font-weight: 700; color: #0A84FF;")
        self._update_selected_display()
        header_layout.addWidget(self.lbl_selected_display)

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Tìm (vd: AS, 10H)...")
        self.input_search.setFixedWidth(130)
        self.input_search.textChanged.connect(self._on_search_text_changed)
        header_layout.addWidget(self.input_search)

        right_panel.addLayout(header_layout)

        # 1. Quick Rank Selector Row
        rank_row = QHBoxLayout()
        rank_row.setSpacing(3)
        rank_title = QLabel("Rank:")
        rank_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #8E8E93; min-width: 32px;")
        rank_row.addWidget(rank_title)

        ranks_order = [
            Rank.ACE,
            Rank.TWO,
            Rank.THREE,
            Rank.FOUR,
            Rank.FIVE,
            Rank.SIX,
            Rank.SEVEN,
            Rank.EIGHT,
            Rank.NINE,
            Rank.TEN,
            Rank.JACK,
            Rank.QUEEN,
            Rank.KING,
        ]
        self._rank_buttons: dict[Rank, QPushButton] = {}
        for r in ranks_order:
            btn_r = QPushButton(r.char)
            btn_r.setFixedSize(36, 30)
            btn_r.setCursor(Qt.PointingHandCursor)
            btn_r.setStyleSheet(
                "padding: 0; font-size: 12px; font-weight: 600; color: #FFFFFF; "
                "background-color: #2C2C2E; border: 1px solid #3A3A3C; border-radius: 4px;"
            )
            btn_r.clicked.connect(lambda _, rank_val=r: self._on_rank_button_clicked(rank_val))
            self._rank_buttons[r] = btn_r
            rank_row.addWidget(btn_r)
        right_panel.addLayout(rank_row)

        # 2. Quick Suit Selector Row
        suit_row = QHBoxLayout()
        suit_row.setSpacing(6)
        suit_title = QLabel("Suit:")
        suit_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #8E8E93; min-width: 32px;")
        suit_row.addWidget(suit_title)

        suit_defs = [
            (Suit.SPADES, "♠ Bích", "#FFFFFF"),
            (Suit.CLUBS, "♣ Tép", "#FFFFFF"),
            (Suit.DIAMONDS, "♦ Rô", "#FF453A"),
            (Suit.HEARTS, "♥ Cơ", "#FF453A"),
        ]
        self._suit_buttons: dict[Suit, QPushButton] = {}
        for s_val, s_name, s_color in suit_defs:
            btn_s = QPushButton(s_name)
            btn_s.setFixedHeight(30)
            btn_s.setCursor(Qt.PointingHandCursor)
            btn_s.setStyleSheet(
                f"padding: 0 10px; font-size: 12px; font-weight: 700; color: {s_color}; "
                f"background-color: #2C2C2E; border: 1px solid #3A3A3C; border-radius: 4px;"
            )
            btn_s.clicked.connect(lambda _, suit_val=s_val: self._on_suit_button_clicked(suit_val))
            self._suit_buttons[s_val] = btn_s
            suit_row.addWidget(btn_s)
        suit_row.addStretch()
        right_panel.addLayout(suit_row)

        # 3. 52 Cards Grid
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(3)
        grid.setContentsMargins(0, 0, 0, 0)

        suits = [Suit.SPADES, Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS]

        for row_idx, suit in enumerate(suits):
            suit_lbl = QLabel(f"{suit.symbol}")
            is_red = suit in (Suit.HEARTS, Suit.DIAMONDS)
            suit_color = "#FF453A" if is_red else "#FFFFFF"
            suit_lbl.setStyleSheet(f"font-weight: 700; font-size: 16px; color: {suit_color}; min-width: 18px;")
            grid.addWidget(suit_lbl, row_idx, 0, Qt.AlignCenter)

            for col_idx, rank in enumerate(ranks_order):
                card = Card(rank, suit)
                code = f"{rank.char}{suit.char.upper()}"
                btn = QPushButton(f"{rank.char}")
                btn.setFixedSize(34, 38)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda _, c=card: self._select_card(c))

                self._card_buttons[code] = btn
                grid.addWidget(btn, row_idx, col_idx + 1)

        self._refresh_card_buttons_style()
        right_panel.addWidget(grid_widget)

        # Action Buttons
        right_panel.addSpacing(4)
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

    def _render_crop_images(self) -> None:
        """Renders raw card crop, matched reference crop, rank crop, and suit crop into QLabels."""
        if self.detected_card is None:
            self.lbl_crop_img.setText("Không có ảnh")
            self.lbl_matched_ref_img.setText("-")
            self.lbl_rank_crop.setText("-")
            self.lbl_suit_crop.setText("-")
            return

        # 1. Full card crop
        if self.detected_card.raw_crop is not None and self.detected_card.raw_crop.size > 0:
            self._set_pixmap_to_label(self.lbl_crop_img, self.detected_card.raw_crop, 88, 124)
        else:
            self.lbl_crop_img.setText("Không có ảnh crop")

        # 2. Dynamic reference sample for currently selected card
        self._update_reference_preview_for_selected_card()

        # 3. Dynamic Rank crop and Suit crop
        if self.detected_card.raw_crop is not None and self.detected_card.raw_crop.size > 0:
            d_rank, d_suit = CardReferenceLibrary.extract_dynamic_corner_patches(self.detected_card.raw_crop)
            r_img = d_rank if (d_rank is not None and d_rank.size > 0) else self.detected_card.rank_crop
            s_img = d_suit if (d_suit is not None and d_suit.size > 0) else self.detected_card.suit_crop

            if r_img is not None and r_img.size > 0:
                self._set_pixmap_to_label(self.lbl_rank_crop, r_img, 42, 42)
            else:
                self.lbl_rank_crop.setText("-")

            if s_img is not None and s_img.size > 0:
                self._set_pixmap_to_label(self.lbl_suit_crop, s_img, 42, 42)
            else:
                self.lbl_suit_crop.setText("-")
        else:
            self.lbl_rank_crop.setText("-")
            self.lbl_suit_crop.setText("-")

    def _update_reference_preview_for_selected_card(self) -> None:
        """Dynamically updates the reference sample preview according to the currently selected card."""
        if not self.selected_card or not self.reference_library:
            self.lbl_matched_ref_img.setText("Chưa chọn bài")
            self.lbl_matched_ref_img.setStyleSheet("background-color: #1C1C1E; border: 1px solid #3A3A3C; border-radius: 6px; color: #8E8E93;")
            if hasattr(self, "lbl_ref_tag"):
                self.lbl_ref_tag.setText("Mẫu Đối Chiếu")
                self.lbl_ref_tag.setStyleSheet("font-size: 10px; color: #8E8E93;")
            if hasattr(self, "lbl_ref_count"):
                self.lbl_ref_count.setText("Thư viện mẫu: 0 mẫu")
            return

        code = f"{self.selected_card.rank.char}{self.selected_card.suit.char.upper()}"
        refs = self.reference_library.get_references_for_card(code)

        if refs:
            ref_img = self.reference_library.get_reference_image(refs[0].id)
            if ref_img is not None:
                self._set_pixmap_to_label(self.lbl_matched_ref_img, ref_img, 88, 124)
                self.lbl_matched_ref_img.setStyleSheet("background-color: #1C1C1E; border: 1px solid #30D158; border-radius: 6px;")
                if hasattr(self, "lbl_ref_tag"):
                    self.lbl_ref_tag.setText(f"Mẫu đối chiếu ({code})")
                    self.lbl_ref_tag.setStyleSheet("font-size: 10px; color: #30D158; font-weight: 700;")
                if hasattr(self, "lbl_ref_count"):
                    self.lbl_ref_count.setText(f"Thư viện đã có: {len(refs)} mẫu của {code}")
                    self.lbl_ref_count.setStyleSheet("font-size: 10px; color: #30D158;")
                return

        # No reference found for the selected card
        self.lbl_matched_ref_img.clear()
        self.lbl_matched_ref_img.setText(f"Chưa có mẫu\ncho {code}")
        self.lbl_matched_ref_img.setStyleSheet("background-color: #1C1C1E; border: 1px dashed #8E8E93; border-radius: 6px; color: #8E8E93; font-size: 11px;")
        if hasattr(self, "lbl_ref_tag"):
            self.lbl_ref_tag.setText(f"Chưa có mẫu ({code})")
            self.lbl_ref_tag.setStyleSheet("font-size: 10px; color: #8E8E93;")
        if hasattr(self, "lbl_ref_count"):
            self.lbl_ref_count.setText(f"Thư viện chưa có mẫu của {code}")
            self.lbl_ref_count.setStyleSheet("font-size: 10px; color: #8E8E93;")

    @staticmethod
    def _set_pixmap_to_label(label: QLabel, img: np.ndarray, max_w: int, max_h: int) -> None:
        h, w = img.shape[:2]
        if len(img.shape) == 2:
            rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled)

    def _update_selected_display(self) -> None:
        if self.selected_card:
            code = f"{self.selected_card.rank.char}{self.selected_card.suit.char.upper()}"
            self.lbl_selected_display.setText(f"Đang chọn: {self.selected_card.unicode_name} ({code})")
        else:
            self.lbl_selected_display.setText("Chưa chọn bài")

    def _on_rank_button_clicked(self, rank: Rank) -> None:
        """User selected a rank from the quick rank bar, preserving current suit."""
        current_suit = self.selected_card.suit if self.selected_card else Suit.SPADES
        self._select_card(Card(rank, current_suit))

    def _on_suit_button_clicked(self, suit: Suit) -> None:
        """User selected a suit from the quick suit bar, preserving current rank."""
        current_rank = self.selected_card.rank if self.selected_card else Rank.ACE
        self._select_card(Card(current_rank, suit))

    def _on_view_similar_clicked(self) -> None:
        """Displays saved reference samples for the currently selected card."""
        if not self.selected_card or not self.reference_library:
            return
        code = f"{self.selected_card.rank.char}{self.selected_card.suit.char.upper()}"
        refs = self.reference_library.get_references_for_card(code)
        if not refs:
            QMessageBox.information(self, "Ảnh mẫu tương tự", f"Chưa có ảnh mẫu nào trong thư viện cho lá {code}.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Các ảnh mẫu đã lưu cho lá {self.selected_card.unicode_name} ({code})")
        dlg.resize(460, 280)
        vbox = QVBoxLayout(dlg)
        vbox.addWidget(QLabel(f"Tìm thấy {len(refs)} ảnh mẫu đã xác nhận:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        h_layout = QHBoxLayout(container)
        h_layout.setSpacing(10)

        for ref in refs:
            p = Path(ref.image_path)
            if not p.exists():
                continue
            r_img = cv2.imread(str(p))
            if r_img is None:
                continue
            col = QVBoxLayout()
            lbl = QLabel()
            self._set_pixmap_to_label(lbl, r_img, 90, 126)
            col.addWidget(lbl, alignment=Qt.AlignCenter)
            col.addWidget(QLabel(f"Hash: {ref.image_hash[:6]}"), alignment=Qt.AlignCenter)
            col.addWidget(QLabel(f"Ngày: {ref.created_at[:10]}"), alignment=Qt.AlignCenter)
            w = QWidget()
            w.setLayout(col)
            h_layout.addWidget(w)

        h_layout.addStretch()
        scroll.setWidget(container)
        vbox.addWidget(scroll)

        btn_close = QPushButton("Đóng", objectName="SecondaryBtn")
        btn_close.clicked.connect(dlg.accept)
        vbox.addWidget(btn_close)
        dlg.exec()

    def _select_card(self, card: Card) -> None:
        """User clicked a card button in the 52-card selector or rank/suit bars."""
        self.selected_card = card
        self._update_selected_display()
        self._highlight_selected_card()
        self._update_reference_preview_for_selected_card()

    def _highlight_selected_card(self) -> None:
        """Applies highlight styling to Rank buttons, Suit buttons, and 52-card grid."""
        sel_rank = self.selected_card.rank if self.selected_card else None
        sel_suit = self.selected_card.suit if self.selected_card else None

        # 1. Update Rank buttons
        for r, btn in self._rank_buttons.items():
            if r == sel_rank:
                btn.setStyleSheet(
                    "padding: 0; font-size: 13px; font-weight: 800; color: #FFFFFF; "
                    "background-color: #0A84FF; border: 2px solid #FFFFFF; border-radius: 4px;"
                )
            else:
                btn.setStyleSheet(
                    "padding: 0; font-size: 12px; font-weight: 600; color: #FFFFFF; "
                    "background-color: #2C2C2E; border: 1px solid #3A3A3C; border-radius: 4px;"
                )

        # 2. Update Suit buttons
        for s, btn in self._suit_buttons.items():
            is_red = s in (Suit.HEARTS, Suit.DIAMONDS)
            s_color = "#FF453A" if is_red else "#FFFFFF"
            if s == sel_suit:
                btn.setStyleSheet(
                    f"padding: 0 10px; font-size: 12px; font-weight: 800; color: #FFFFFF; "
                    f"background-color: #0A84FF; border: 2px solid #FFFFFF; border-radius: 4px;"
                )
            else:
                btn.setStyleSheet(
                    f"padding: 0 10px; font-size: 12px; font-weight: 700; color: {s_color}; "
                    f"background-color: #2C2C2E; border: 1px solid #3A3A3C; border-radius: 4px;"
                )

        # 3. Update 52-card grid buttons
        selected_code = f"{self.selected_card.rank.char}{self.selected_card.suit.char.upper()}" if self.selected_card else None
        self._refresh_card_buttons_style(selected_code)

    def _refresh_card_buttons_style(self, selected_code: Optional[str] = None) -> None:
        for code, btn in self._card_buttons.items():
            is_red = code.endswith("H") or code.endswith("D")
            fg = "#FF453A" if is_red else "#FFFFFF"
            if code == selected_code:
                btn.setStyleSheet(
                    f"padding: 0; font-weight: 800; font-size: 12px; color: #FFFFFF; background-color: #0A84FF; "
                    f"border: 2px solid #FFFFFF; border-radius: 4px;"
                )
            else:
                btn.setStyleSheet(
                    f"padding: 0; font-weight: 700; font-size: 11px; color: {fg}; background-color: #2C2C2E; "
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
        if not self.selected_card:
            QMessageBox.warning(
                self,
                "Chưa chọn lá bài",
                "Vui lòng chọn một lá bài từ bảng bên phải trước khi xác nhận!",
            )
            return
        self.is_confirmed = True
        self.accept()

    def _on_save_as_reference_clicked(self) -> None:
        """Saves current crop to CardReferenceLibrary under the selected card with confirmation."""
        if not self.selected_card:
            QMessageBox.warning(self, "Chưa chọn lá bài", "Vui lòng chọn lá bài chính xác trước khi lưu làm ảnh mẫu.")
            return

        if self.detected_card is None or self.detected_card.raw_crop is None or self.detected_card.raw_crop.size == 0:
            QMessageBox.warning(self, "Không có ảnh", "Không tìm thấy ảnh crop để lưu làm mẫu.")
            return

        if (
            self.detected_card is not None
            and getattr(self.detected_card, "crop_status", "") in (
                "INVALID_CARD_CROP",
                "NON_CARD_OBJECT",
                "MISSING_RANK_REGION",
                "MISSING_SUIT_REGION",
            )
        ):
            QMessageBox.warning(
                self,
                "Không thể lưu ảnh mẫu",
                "Vùng ảnh này được xác định là đối tượng không phải lá bài (Avatar người chơi hoặc nút UI).\n"
                "Không thể lưu ảnh này vào thư viện mẫu!",
            )
            return

        code = f"{self.selected_card.rank.char}{self.selected_card.suit.char.upper()}"

        # Sanity check: verify with template engine and reference library if there is a contradiction
        from app.vision.template_engine import CardTemplateEngine
        engine = CardTemplateEngine()
        d_rank, _ = CardReferenceLibrary.extract_dynamic_corner_patches(self.detected_card.raw_crop)
        v_rank, v_conf = (
            engine.match_rank(cv2.cvtColor(d_rank, cv2.COLOR_BGR2GRAY))
            if (d_rank is not None and d_rank.size > 0)
            else (None, 0.0)
        )

        # Check if confirmed reference library supports user's selection
        ref_rank = None
        if self.reference_library and d_rank is not None and d_rank.size > 0:
            q_rank_glyph = CardReferenceLibrary.extract_primary_glyph(d_rank, (24, 36))
            r_matched, r_score, _ = self.reference_library.match_rank_glyph(q_rank_glyph, min_score=0.68)
            if r_score >= 0.70:
                ref_rank = r_matched

        logger.info(
            "User requested saving reference for %s (bbox=%s, engine_v_rank=%s, v_conf=%.2f, ref_rank=%s)",
            code,
            self.detected_card.bbox,
            v_rank.char if v_rank else None,
            v_conf,
            ref_rank.char if ref_rank else None,
        )

        has_conflict = (
            v_rank is not None
            and v_conf >= 0.85
            and v_rank != self.selected_card.rank
            and ref_rank != self.selected_card.rank
        )
        if has_conflict:
            contra_dialog = CardContradictionDialog(
                card_crop=self.detected_card.raw_crop,
                rank_crop=d_rank,
                selected_card=self.selected_card,
                predicted_rank=v_rank,
                confidence=v_conf,
                parent=self,
            )
            if contra_dialog.exec() != QDialog.Accepted:
                logger.info("User cancelled saving reference after contradiction warning.")
                return
        else:
            confirm = QMessageBox.question(
                self,
                "Xác nhận lưu ảnh mẫu",
                f"Bạn có chắc chắn muốn lưu ảnh crop này làm mẫu chuẩn cho lá bài:\n\n"
                f"👉 {self.selected_card.unicode_name} ({code}) 👈",
                QMessageBox.Yes | QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return

        try:
            if self.reference_library is not None:
                ref = self.reference_library.add_reference(
                    image=self.detected_card.raw_crop,
                    card=self.selected_card,
                    source="user_confirmed",
                    metadata={"crop_bbox": list(self.detected_card.bbox)},
                )
                assert ref.card_code == code, f"Reference card_code mismatch: {ref.card_code} != {code}"
                self.saved_as_reference = True
                self.is_confirmed = True
                self._update_reference_preview_for_selected_card()
                QMessageBox.information(
                    self,
                    "Đã lưu ảnh mẫu",
                    f"Đã lưu thành công ảnh mẫu cho lá {self.selected_card.unicode_name} ({ref.card_code}).\n"
                    f"Thư viện hiện có {len(self.reference_library.get_references_for_card(code))} mẫu của lá này.\n"
                    f"Các lần quét tiếp theo sẽ tự động nhận diện chính xác!",
                )
                self.accept()
        except Exception as e:
            logger.exception("Failed to save reference sample for %s: %s", code, e)
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
            f"Bạn có chắc chắn muốn xóa toàn bộ {len(existing)} ảnh mẫu đã lưu của lá {self.selected_card.unicode_name} ({code})?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            count = self.reference_library.delete_references_for_card(code)
            self.deleted_reference = True
            QMessageBox.information(self, "Đã xóa", f"Đã xóa {count} ảnh mẫu của lá {code}.")
            self._update_reference_preview_for_selected_card()
