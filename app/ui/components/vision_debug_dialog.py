"""Comprehensive 4-step Computer Vision Diagnostic & Inspection Dialog for macOS.

Implements the 4 mandatory diagnostic inspection views:
1. Original Frame (Raw captured screen image)
2. Detection Overlay (Annotated with Bounding Boxes, Polygons, IDs, Dimensions, Confidence, Status)
3. Individual Card Crop (Source patch, rectified patch, dimensions, detection confidence)
4. Recognition Debug (Rank crop, Suit crop, matched reference sample image, similarity %, final decision)
"""

from __future__ import annotations
from typing import List, Optional
import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.vision.card_detector import DetectionDebugInfo
from app.vision.card_recognizer import DetectedCard
from app.vision.card_reference_library import CardReferenceLibrary


class VisionDebugDialog(QDialog):
    """Full 4-step Diagnostic Dialog for inspecting card detection, cropping, and reference matching."""

    def __init__(
        self,
        table_image: Optional[np.ndarray] = None,
        debug_info: Optional[DetectionDebugInfo] = None,
        detected_cards: Optional[List[DetectedCard]] = None,
        reference_library: Optional[CardReferenceLibrary] = None,
        parent: Optional[QWidget] = None,
        *,
        original_frame: Optional[np.ndarray] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("🔬 Kiểm tra Debug Computer Vision (4 Bước Chẩn Đoán)")
        self.resize(1000, 680)
        self.setMinimumSize(850, 550)

        # Support both original_frame and table_image cleanly
        self.table_image = original_frame if original_frame is not None else table_image
        self.debug_info = debug_info
        self.detected_cards = detected_cards or []
        self.reference_library = reference_library or CardReferenceLibrary()

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header Title
        header = QHBoxLayout()
        lbl_title = QLabel("🔬 Chẩn đoán Pipeline Nhận diện Lá bài & Thư viện Ảnh mẫu")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #FFFFFF;")
        header.addWidget(lbl_title)
        header.addStretch()

        btn_close = QPushButton("Đóng", objectName="SecondaryBtn")
        btn_close.clicked.connect(self.accept)
        header.addWidget(btn_close)
        layout.addLayout(header)

        # Tab Widget for 4 views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #3A3A3C; background: #1C1C1E; border-radius: 6px; }
            QTabBar::tab { background: #2C2C2E; color: #8E8E93; padding: 8px 16px; font-weight: 600; border-top-left-radius: 6px; border-top-right-radius: 6px; }
            QTabBar::tab:selected { background: #0A84FF; color: #FFFFFF; }
        """)

        # Add 4 Diagnostic Tabs
        self.tabs.addTab(self._build_tab_original_frame(), "1. Original Frame (Ảnh gốc)")
        self.tabs.addTab(self._build_tab_detection_overlay(), "2. Detection Overlay (Khung nhận diện)")
        self.tabs.addTab(self._build_tab_individual_crop(), "3. Individual Card Crop (Từng lá)")
        self.tabs.addTab(self._build_tab_recognition_debug(), "4. Recognition & Reference (Ảnh mẫu)")

        layout.addWidget(self.tabs)

    # =========================================================================
    # TAB 1: Original Frame
    # =========================================================================
    def _build_tab_original_frame(self) -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(8)

        info_bar = QHBoxLayout()
        if self.table_image is not None and self.table_image.size > 0:
            h, img_w = self.table_image.shape[:2]
            lbl_dim = QLabel(f"📐 Kích thước ảnh gốc: {img_w} x {h} px | Kênh: {self.table_image.shape[2]}")
        else:
            lbl_dim = QLabel("Chưa có ảnh gốc.")
        lbl_dim.setStyleSheet("color: #64D2FF; font-weight: 600;")
        info_bar.addWidget(lbl_dim)
        info_bar.addStretch()
        vbox.addLayout(info_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        lbl_img = QLabel()
        lbl_img.setAlignment(Qt.AlignCenter)
        if self.table_image is not None and self.table_image.size > 0:
            self._set_pixmap(lbl_img, self.table_image, max_w=950, max_h=550)
        else:
            lbl_img.setText("Không có ảnh")
        scroll.setWidget(lbl_img)
        vbox.addWidget(scroll)
        return w

    # =========================================================================
    # TAB 2: Detection Overlay
    # =========================================================================
    def _build_tab_detection_overlay(self) -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(8)

        splitter = QSplitter(Qt.Vertical)

        # Top: Annotated Image with Bounding Boxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        lbl_overlay = QLabel()
        lbl_overlay.setAlignment(Qt.AlignCenter)

        overlay_img = None
        if self.debug_info and self.debug_info.detection_overlay is not None:
            overlay_img = self.debug_info.detection_overlay
        elif self.table_image is not None:
            overlay_img = self.table_image

        if overlay_img is not None:
            self._set_pixmap(lbl_overlay, overlay_img, max_w=950, max_h=340)
        else:
            lbl_overlay.setText("Không có ảnh overlay")
        scroll.setWidget(lbl_overlay)
        splitter.addWidget(scroll)

        # Bottom: Table listing every detected object with filter (Accepted, Duplicates, Rejected)
        table_box = QGroupBox("Bảng đối chiếu Detection & Deduplication (Part F):")
        tbl_layout = QVBoxLayout(table_box)

        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Xem nhóm đối tượng:"))
        self.combo_tab2_filter = QComboBox()
        self.combo_tab2_filter.addItems([
            f"✅ Lá bài hợp lệ ({len(self.detected_cards)})",
            f"⚠️ Detections trùng lặp ({len(self.debug_info.duplicate_detections) if self.debug_info else 0})",
            f"❌ Contours bị loại ({len(self.debug_info.rejected_detections) if self.debug_info else 0})",
        ])
        self.combo_tab2_filter.currentIndexChanged.connect(self._on_tab2_filter_changed)
        filter_bar.addWidget(self.combo_tab2_filter)
        filter_bar.addStretch()
        tbl_layout.addLayout(filter_bar)

        self.table_tab2 = QTableWidget()
        self.table_tab2.setColumnCount(9)
        self.table_tab2.setHorizontalHeaderLabels([
            "ID", "Bounding Box", "Kích thước", "Tỷ lệ (W/H)", "Det. Conf", "Crop Status", "Nhóm trùng", "Lý do loại", "Rank/Suit"
        ])
        self.table_tab2.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl_layout.addWidget(self.table_tab2)

        self._populate_tab2_table(0)

        splitter.addWidget(table_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        vbox.addWidget(splitter)
        return w

    def _on_tab2_filter_changed(self, index: int) -> None:
        self._populate_tab2_table(index)

    def _populate_tab2_table(self, filter_idx: int) -> None:
        self.table_tab2.setRowCount(0)
        items: List[any] = []
        if filter_idx == 0:
            items = self.detected_cards
        elif filter_idx == 1 and self.debug_info:
            items = self.debug_info.duplicate_detections
        elif filter_idx == 2 and self.debug_info:
            items = self.debug_info.rejected_detections

        self.table_tab2.setRowCount(len(items))
        for row, item in enumerate(items):
            det_id = getattr(item, "detection_id", f"#{row+1}")
            bbox = getattr(item, "bbox", (0, 0, 0, 0))
            x, y, dw, dh = bbox
            aspect = round(dw / float(dh), 2) if dh > 0 else 0.0
            det_conf = getattr(item, "detection_confidence", 0.0)
            crop_st = getattr(item, "crop_status", "VALID_CARD_CROP")
            dup_grp = getattr(item, "duplicate_group", "")
            rej_reason = getattr(item, "rejection_reason", "")
            
            # Label/tag
            if hasattr(item, "card") and item.card is not None:
                tag = f"{item.card.unicode_name} ({int(item.confidence*100)}%)"
            elif filter_idx == 1:
                tag = "TRÙNG LẶP [Đã loại]"
            else:
                tag = f"LOẠI BỎ [{rej_reason or 'Non-card'}]"

            self.table_tab2.setItem(row, 0, QTableWidgetItem(str(det_id)))
            self.table_tab2.setItem(row, 1, QTableWidgetItem(f"({x}, {y}, {dw}, {dh})"))
            self.table_tab2.setItem(row, 2, QTableWidgetItem(f"{dw} x {dh}"))
            self.table_tab2.setItem(row, 3, QTableWidgetItem(str(aspect)))
            self.table_tab2.setItem(row, 4, QTableWidgetItem(f"{int(det_conf * 100)}%"))
            self.table_tab2.setItem(row, 5, QTableWidgetItem(str(crop_st)))
            self.table_tab2.setItem(row, 6, QTableWidgetItem(str(dup_grp or "-")))
            
            rej_item = QTableWidgetItem(str(rej_reason or "-"))
            if rej_reason:
                rej_item.setForeground(QColor("#FF453A"))
            self.table_tab2.setItem(row, 7, rej_item)

            tag_item = QTableWidgetItem(tag)
            if filter_idx == 0:
                tag_item.setForeground(QColor("#30D158"))
            elif filter_idx == 1:
                tag_item.setForeground(QColor("#FF9F0A"))
            else:
                tag_item.setForeground(QColor("#FF453A"))
            self.table_tab2.setItem(row, 8, tag_item)

    # =========================================================================
    # TAB 3: Individual Card Crop
    # =========================================================================
    def _build_tab_individual_crop(self) -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(10)

        # Selector Row
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Chọn lá bài để kiểm tra ảnh crop:"))
        self.combo_crop_card = QComboBox()
        for idx, det in enumerate(self.detected_cards):
            c_name = det.card.unicode_name if det.card else f"[{getattr(det, 'crop_status', 'NON_CARD_OBJECT')}]"
            self.combo_crop_card.addItem(f"#{idx+1} {det.detection_id}: {c_name} [{det.recognition_status}]", idx)
        self.combo_crop_card.currentIndexChanged.connect(self._on_crop_card_selected)
        top_bar.addWidget(self.combo_crop_card)
        top_bar.addStretch()
        vbox.addLayout(top_bar)

        # Crop visual inspection cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        # 1. Raw Patch
        box_raw = QGroupBox("1. Ảnh gốc của lá (Source Patch)")
        layout_raw = QVBoxLayout(box_raw)
        self.lbl_tab3_raw = QLabel()
        self.lbl_tab3_raw.setAlignment(Qt.AlignCenter)
        self.lbl_tab3_raw.setFixedSize(140, 200)
        self.lbl_tab3_raw.setStyleSheet("background-color: #141414; border: 1px solid #3A3A3C; border-radius: 6px;")
        layout_raw.addWidget(self.lbl_tab3_raw, alignment=Qt.AlignCenter)
        self.lbl_tab3_raw_stats = QLabel("Bbox: -\nKích thước: -")
        self.lbl_tab3_raw_stats.setStyleSheet("font-size: 11px; color: #8E8E93;")
        layout_raw.addWidget(self.lbl_tab3_raw_stats)
        cards_layout.addWidget(box_raw)

        # 2. Rectified Normalized Patch (120x168)
        box_norm = QGroupBox("2. Ảnh đã chuẩn hóa (120x168 Patch)")
        layout_norm = QVBoxLayout(box_norm)
        self.lbl_tab3_norm = QLabel()
        self.lbl_tab3_norm.setAlignment(Qt.AlignCenter)
        self.lbl_tab3_norm.setFixedSize(140, 200)
        self.lbl_tab3_norm.setStyleSheet("background-color: #141414; border: 1px solid #3A3A3C; border-radius: 6px;")
        layout_norm.addWidget(self.lbl_tab3_norm, alignment=Qt.AlignCenter)
        self.lbl_tab3_norm_stats = QLabel("Kích thước chuẩn: 120 x 168 px\nKhử viền xanh: Đã xử lý")
        self.lbl_tab3_norm_stats.setStyleSheet("font-size: 11px; color: #8E8E93;")
        layout_norm.addWidget(self.lbl_tab3_norm_stats)
        cards_layout.addWidget(box_norm)

        # 3. Detection Confidence & Occlusion details
        box_det_details = QGroupBox("3. Thông số Detection & Validation")
        layout_det_details = QVBoxLayout(box_det_details)
        self.lbl_tab3_det_info = QLabel()
        self.lbl_tab3_det_info.setStyleSheet("font-size: 12px; color: #FFFFFF; line-height: 1.6;")
        self.lbl_tab3_det_info.setWordWrap(True)
        layout_det_details.addWidget(self.lbl_tab3_det_info)
        layout_det_details.addStretch()
        cards_layout.addWidget(box_det_details, stretch=1)

        vbox.addLayout(cards_layout)
        vbox.addStretch()

        if self.detected_cards:
            self._on_crop_card_selected(0)

        return w

    def _on_crop_card_selected(self, idx: int) -> None:
        if not (0 <= idx < len(self.detected_cards)):
            return
        det = self.detected_cards[idx]
        x, y, w, h = det.bbox

        # Raw crop
        if det.raw_crop is not None and det.raw_crop.size > 0:
            self._set_pixmap(self.lbl_tab3_raw, det.raw_crop, 136, 194)
            self.lbl_tab3_raw_stats.setText(f"Tọa độ gốc (x, y): ({x}, {y})\nKích thước crop: {w} x {h} px\nTrạng thái: {det.crop_status}")
        else:
            self.lbl_tab3_raw.setText("Không có ảnh")
            self.lbl_tab3_raw_stats.setText(f"Tọa độ gốc: ({x}, {y}, {w}, {h})")

        # Normalized crop
        norm_img = cv2.resize(det.raw_crop, (120, 168)) if (det.raw_crop is not None and det.raw_crop.size > 0) else None
        if norm_img is not None:
            self._set_pixmap(self.lbl_tab3_norm, norm_img, 136, 194)
        else:
            self.lbl_tab3_norm.setText("Không có ảnh")

        det_pct = int(det.detection_confidence * 100)
        rec_pct = int(det.confidence * 100)
        crop_st = getattr(det, "crop_status", "VALID_CARD_CROP")
        dup_grp = getattr(det, "duplicate_group", "") or "None"
        rej_r = getattr(det, "rejection_reason", "") or "None"

        if det.card is not None:
            tag = f"<span style='color:#30D158; font-weight:700;'>{det.card.unicode_name}</span>"
        else:
            tag = f"<span style='color:#FF453A; font-weight:700;'>[ĐỐI TƯỢNG KHÔNG PHẢI LÁ BÀI / {crop_st}]</span>"

        self.lbl_tab3_det_info.setText(
            f"<b>Đối tượng:</b> {tag}<br>"
            f"<b>Detection ID:</b> {det.detection_id}<br>"
            f"<b>Tọa độ ảnh gốc (Bbox):</b> ({x}, {y}, {w}, {h})<br>"
            f"<b>Kích thước crop:</b> {w} x {h} px<br>"
            f"<b>Detection Confidence:</b> {det_pct}%<br>"
            f"<b>Recognition Confidence:</b> {rec_pct}%<br>"
            f"<b>Crop Validation Status:</b> {crop_st}<br>"
            f"<b>Chồng lấp (Overlap):</b> {'Có' if det.is_overlapping else 'Không'}<br>"
            f"<b>Bị che khuất (Occluded):</b> {'Có' if det.is_partially_occluded else 'Không'}<br>"
            f"<b>Nhóm trùng:</b> {dup_grp}<br>"
            f"<b>Lý do từ chối (Rejection Reason):</b> {rej_r}<br>"
            f"<b>Trạng thái nhận diện:</b> {det.recognition_status}"
        )

    # =========================================================================
    # TAB 4: Recognition & Reference Matching
    # =========================================================================
    def _build_tab_recognition_debug(self) -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(10)

        # Top selector
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Chọn đối tượng để xem chi tiết đối soát ảnh mẫu:"))
        self.combo_rec_card = QComboBox()
        for idx, det in enumerate(self.detected_cards):
            c_name = det.card.unicode_name if det.card else f"[{getattr(det, 'crop_status', 'NON_CARD_OBJECT')}]"
            self.combo_rec_card.addItem(f"#{idx+1} {det.detection_id}: {c_name} ({int(det.confidence*100)}%)", idx)
        self.combo_rec_card.currentIndexChanged.connect(self._on_rec_card_selected)
        top_bar.addWidget(self.combo_rec_card)
        top_bar.addStretch()
        vbox.addLayout(top_bar)

        # 4 visual boxes side-by-side
        row_compare = QHBoxLayout()
        row_compare.setSpacing(12)

        # A. Rank Crop
        box_r = QGroupBox("A. Rank Crop (Góc trên)")
        layout_r = QVBoxLayout(box_r)
        self.lbl_tab4_rank = QLabel()
        self.lbl_tab4_rank.setFixedSize(80, 80)
        self.lbl_tab4_rank.setAlignment(Qt.AlignCenter)
        self.lbl_tab4_rank.setStyleSheet("background-color: #141414; border: 1px solid #3A3A3C; border-radius: 4px;")
        layout_r.addWidget(self.lbl_tab4_rank, alignment=Qt.AlignCenter)
        self.lbl_tab4_rank_score = QLabel("Rank Conf: -")
        self.lbl_tab4_rank_score.setAlignment(Qt.AlignCenter)
        self.lbl_tab4_rank_score.setStyleSheet("font-size: 11px; color: #64D2FF; font-weight: 600;")
        layout_r.addWidget(self.lbl_tab4_rank_score)
        row_compare.addWidget(box_r)

        # B. Suit Crop
        box_s = QGroupBox("B. Suit Crop (Biểu tượng chất)")
        layout_s = QVBoxLayout(box_s)
        self.lbl_tab4_suit = QLabel()
        self.lbl_tab4_suit.setFixedSize(80, 80)
        self.lbl_tab4_suit.setAlignment(Qt.AlignCenter)
        self.lbl_tab4_suit.setStyleSheet("background-color: #141414; border: 1px solid #3A3A3C; border-radius: 4px;")
        layout_s.addWidget(self.lbl_tab4_suit, alignment=Qt.AlignCenter)
        self.lbl_tab4_suit_score = QLabel("Suit Conf: -")
        self.lbl_tab4_suit_score.setAlignment(Qt.AlignCenter)
        self.lbl_tab4_suit_score.setStyleSheet("font-size: 11px; color: #64D2FF; font-weight: 600;")
        layout_s.addWidget(self.lbl_tab4_suit_score)
        row_compare.addWidget(box_s)

        # C. Query Card Crop
        box_query = QGroupBox("C. Ảnh lá bài cần nhận diện")
        layout_query = QVBoxLayout(box_query)
        self.lbl_tab4_query = QLabel()
        self.lbl_tab4_query.setFixedSize(100, 140)
        self.lbl_tab4_query.setAlignment(Qt.AlignCenter)
        self.lbl_tab4_query.setStyleSheet("background-color: #141414; border: 1px solid #3A3A3C; border-radius: 4px;")
        layout_query.addWidget(self.lbl_tab4_query, alignment=Qt.AlignCenter)
        row_compare.addWidget(box_query)

        # D. Matched Reference Sample
        box_ref = QGroupBox("D. Ảnh mẫu khớp từ Thư viện")
        layout_ref = QVBoxLayout(box_ref)
        self.lbl_tab4_ref = QLabel()
        self.lbl_tab4_ref.setFixedSize(100, 140)
        self.lbl_tab4_ref.setAlignment(Qt.AlignCenter)
        self.lbl_tab4_ref.setStyleSheet("background-color: #141414; border: 1px solid #30D158; border-radius: 4px;")
        layout_ref.addWidget(self.lbl_tab4_ref, alignment=Qt.AlignCenter)
        self.lbl_tab4_ref_status = QLabel("Similarity: -")
        self.lbl_tab4_ref_status.setAlignment(Qt.AlignCenter)
        self.lbl_tab4_ref_status.setStyleSheet("font-size: 11px; color: #30D158; font-weight: 700;")
        layout_ref.addWidget(self.lbl_tab4_ref_status)
        row_compare.addWidget(box_ref)

        vbox.addLayout(row_compare)

        # Summary decision panel
        box_decision = QFrame()
        box_decision.setStyleSheet("background-color: #2C2C2E; border-radius: 6px; padding: 10px;")
        layout_dec = QVBoxLayout(box_decision)
        self.lbl_tab4_decision = QLabel()
        self.lbl_tab4_decision.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF; line-height: 1.5;")
        self.lbl_tab4_decision.setWordWrap(True)
        layout_dec.addWidget(self.lbl_tab4_decision)
        vbox.addWidget(box_decision)

        vbox.addStretch()

        if self.detected_cards:
            self._on_rec_card_selected(0)

        return w

    def _on_rec_card_selected(self, idx: int) -> None:
        if not (0 <= idx < len(self.detected_cards)):
            return
        det = self.detected_cards[idx]
        crop_st = getattr(det, "crop_status", "VALID_CARD_CROP")
        is_non_card = det.card is None or crop_st in ("NON_CARD_OBJECT", "INVALID_CARD_CROP", "MISSING_RANK_REGION", "MISSING_SUIT_REGION")

        # 1. Rank Crop
        if det.rank_crop is not None and det.rank_crop.size > 0:
            rh, rw = det.rank_crop.shape[:2]
            self._set_pixmap(self.lbl_tab4_rank, det.rank_crop, 76, 76)
            if is_non_card:
                self.lbl_tab4_rank_score.setText(f"Rank ({rw}x{rh}): Không hợp lệ")
                self.lbl_tab4_rank_score.setStyleSheet("font-size: 11px; color: #FF453A; font-weight: 600;")
            else:
                self.lbl_tab4_rank_score.setText(f"Rank ({rw}x{rh}): {int(det.rank_confidence*100)}%")
                self.lbl_tab4_rank_score.setStyleSheet("font-size: 11px; color: #64D2FF; font-weight: 600;")
        else:
            self.lbl_tab4_rank.setText("Không có")
            self.lbl_tab4_rank_score.setText("Rank: Không có")
            self.lbl_tab4_rank_score.setStyleSheet("font-size: 11px; color: #8E8E93;")

        # 2. Suit Crop
        if det.suit_crop is not None and det.suit_crop.size > 0:
            sh, sw = det.suit_crop.shape[:2]
            self._set_pixmap(self.lbl_tab4_suit, det.suit_crop, 76, 76)
            if is_non_card:
                self.lbl_tab4_suit_score.setText(f"Suit ({sw}x{sh}): Không hợp lệ")
                self.lbl_tab4_suit_score.setStyleSheet("font-size: 11px; color: #FF453A; font-weight: 600;")
            else:
                self.lbl_tab4_suit_score.setText(f"Suit ({sw}x{sh}): {int(det.suit_confidence*100)}%")
                self.lbl_tab4_suit_score.setStyleSheet("font-size: 11px; color: #64D2FF; font-weight: 600;")
        else:
            self.lbl_tab4_suit.setText("Không có")
            self.lbl_tab4_suit_score.setText("Suit: Không có")
            self.lbl_tab4_suit_score.setStyleSheet("font-size: 11px; color: #8E8E93;")

        # 3. Query Crop
        if det.raw_crop is not None and det.raw_crop.size > 0:
            norm_q = cv2.resize(det.raw_crop, (120, 168))
            self._set_pixmap(self.lbl_tab4_query, norm_q, 96, 134)
        else:
            self.lbl_tab4_query.setText("Chưa có")

        # 4. Matched Reference Crop
        ref_img = None
        if det.reference_crop is not None and det.reference_crop.size > 0:
            ref_img = det.reference_crop
        elif det.matched_reference_id:
            ref_img = self.reference_library.get_reference_image(det.matched_reference_id)

        if not is_non_card and ref_img is not None:
            norm_r = cv2.resize(ref_img, (120, 168))
            self._set_pixmap(self.lbl_tab4_ref, norm_r, 96, 134)
            sim_pct = int(det.matched_similarity * 100)
            self.lbl_tab4_ref_status.setText(f"Similarity: {sim_pct}% [Khớp]")
            self.lbl_tab4_ref_status.setStyleSheet("font-size: 11px; color: #30D158; font-weight: 700;")
        else:
            self.lbl_tab4_ref.setText("Không áp dụng" if is_non_card else "Chưa có mẫu")
            self.lbl_tab4_ref_status.setText("Không áp dụng ảnh mẫu" if is_non_card else "Chưa dùng ảnh mẫu")
            self.lbl_tab4_ref_status.setStyleSheet("font-size: 11px; color: #8E8E93;")

        # Decision text
        if det.card is not None:
            tag = det.card.unicode_name
            status_color = "#30D158" if det.recognition_status == "CONFIRMED" else ("#FF9F0A" if det.recognition_status in ("UNCERTAIN", "REFERENCE_NOT_USED") else "#FF453A")
            ref_source_str = "Có (Khớp từ mẫu đã xác nhận)" if det.is_reference_match else "Không (Dùng thuật toán font dự phòng)"
            recog_display = f"<span style='color:{status_color}'>{tag}</span> ({int(det.confidence*100)}%)"
        else:
            tag = f"[ĐỐI TƯỢNG KHÔNG PHẢI LÁ BÀI / {crop_st}]"
            status_color = "#FF453A"
            ref_source_str = "Không áp dụng (Không phải lá bài)"
            recog_display = f"<span style='color:{status_color}; font-weight:700;'>{tag}</span> (0%)"

        rej_reason = det.rejection_reason or det.uncertain_reason or ('Đối tượng không thỏa mãn cấu trúc lá bài' if is_non_card else 'Nhận diện tốt')
        self.lbl_tab4_decision.setText(
            f"<b>Kết quả nhận diện:</b> {recog_display}<br>"
            f"<b>Trạng thái:</b> <span style='color:{status_color}'>{det.recognition_status}</span><br>"
            f"<b>Sử dụng ảnh mẫu:</b> {ref_source_str}<br>"
            f"<b>Độ tương đồng ảnh mẫu (Similarity):</b> {int(det.matched_similarity*100)}%<br>"
            f"<b>Ghi chú / Lý do:</b> {rej_reason}"
        )

    @staticmethod
    def _set_pixmap(label: QLabel, img: np.ndarray, max_w: int, max_h: int) -> None:
        h, w = img.shape[:2]
        if len(img.shape) == 2:
            rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled)
