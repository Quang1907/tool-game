"""Card Reference Manager UI for browsing, inspecting, adding, and deleting confirmed card samples."""

from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.card import Card, Rank, Suit
from app.vision.card_reference_library import CardReference, CardReferenceLibrary


class CardReferenceManagerDialog(QDialog):
    """Management dialog for inspecting, adding, and deleting confirmed reference samples across 52 cards."""

    def __init__(
        self,
        reference_library: Optional[CardReferenceLibrary] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("📚 Quản lý Thư viện Ảnh mẫu Đã xác nhận — Binh 13")
        self.resize(860, 560)
        self.setMinimumSize(780, 500)

        self.library = reference_library or CardReferenceLibrary()
        self.all_52_cards: List[Card] = [Card.from_id(i) for i in range(52)]
        self.selected_card: Optional[Card] = self.all_52_cards[0]
        self.selected_ref_id: Optional[str] = None

        self._init_ui()
        self._populate_card_list()
        self._load_selected_card_samples()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # ---------------------------------------------------------------------
        # 1. Header with Stats Summary
        # ---------------------------------------------------------------------
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Thư viện Ảnh mẫu Đã xác nhận (Card Reference Library)")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0A84FF;")
        title_box.addWidget(title)

        self.lbl_stats = QLabel("Đang tải dữ liệu...")
        self.lbl_stats.setStyleSheet("font-size: 11px; color: #8E8E93;")
        title_box.addWidget(self.lbl_stats)
        header.addLayout(title_box)

        header.addStretch()

        self.btn_refresh = QPushButton("🔄 Làm mới", objectName="SecondaryBtn")
        self.btn_refresh.clicked.connect(self._refresh_all)
        header.addWidget(self.btn_refresh)

        main_layout.addLayout(header)

        # ---------------------------------------------------------------------
        # 2. Filter Bar
        # ---------------------------------------------------------------------
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        lbl_search = QLabel("Tìm kiếm:")
        lbl_search.setStyleSheet("font-weight: 600;")
        filter_bar.addWidget(lbl_search)

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Lọc theo mã bài (vd: A, 10, S, H, 2C)...")
        self.input_search.setFixedWidth(200)
        self.input_search.textChanged.connect(self._populate_card_list)
        filter_bar.addWidget(self.input_search)

        self.combo_suit_filter = QComboBox()
        self.combo_suit_filter.addItems([
            "Tất cả chất (All Suits)",
            "Chất Bích ♠ (Spades)",
            "Chất Chuồn ♣ (Clubs)",
            "Chất Rô ♦ (Diamonds)",
            "Chất Cơ ♥ (Hearts)",
        ])
        self.combo_suit_filter.currentIndexChanged.connect(self._populate_card_list)
        filter_bar.addWidget(self.combo_suit_filter)

        self.combo_coverage_filter = QComboBox()
        self.combo_coverage_filter.addItems([
            "Tất cả 52 lá bài",
            "Đã có ảnh mẫu (Has Samples)",
            "Chưa có ảnh mẫu (Missing)",
        ])
        self.combo_coverage_filter.currentIndexChanged.connect(self._populate_card_list)
        filter_bar.addWidget(self.combo_coverage_filter)

        filter_bar.addStretch()
        main_layout.addLayout(filter_bar)

        # ---------------------------------------------------------------------
        # 3. Splitter: 52 Cards List (Left) & Reference Samples Gallery (Right)
        # ---------------------------------------------------------------------
        splitter = QSplitter(Qt.Horizontal)

        # LEFT: 52 Cards List
        box_left = QFrame()
        box_left.setStyleSheet("background-color: #1E1E1E; border: 1px solid #2C2C2E; border-radius: 6px;")
        layout_left = QVBoxLayout(box_left)
        layout_left.setContentsMargins(6, 8, 6, 6)

        lbl_cards_header = QLabel("Danh sách 52 lá bài:")
        lbl_cards_header.setStyleSheet("font-weight: 700; color: #FFFFFF; font-size: 12px;")
        layout_left.addWidget(lbl_cards_header)

        self.list_cards = QListWidget()
        self.list_cards.setStyleSheet(
            "QListWidget { background-color: #1E1E1E; border: none; font-size: 13px; font-weight: 600; } "
            "QListWidget::item { padding: 6px; border-radius: 4px; margin-bottom: 2px; } "
            "QListWidget::item:selected { background-color: #0A84FF; color: white; }"
        )
        self.list_cards.itemClicked.connect(self._on_card_item_clicked)
        layout_left.addWidget(self.list_cards)

        splitter.addWidget(box_left)

        # RIGHT: Reference Samples Gallery
        box_right = QFrame()
        box_right.setStyleSheet("background-color: #1E1E1E; border: 1px solid #2C2C2E; border-radius: 6px;")
        self.layout_right = QVBoxLayout(box_right)
        self.layout_right.setContentsMargins(10, 10, 10, 10)
        self.layout_right.setSpacing(8)

        # Selected Card Header
        self.lbl_selected_title = QLabel("Chi tiết ảnh mẫu:")
        self.lbl_selected_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0A84FF;")
        self.layout_right.addWidget(self.lbl_selected_title)

        # Scroll area for samples
        self.scroll_samples = QScrollArea()
        self.scroll_samples.setWidgetResizable(True)
        self.scroll_samples.setStyleSheet("background-color: #141414; border: 1px solid #2C2C2E; border-radius: 6px;")

        self.samples_container = QWidget()
        self.layout_samples = QVBoxLayout(self.samples_container)
        self.layout_samples.setSpacing(8)
        self.layout_samples.setContentsMargins(8, 8, 8, 8)
        self.scroll_samples.setWidget(self.samples_container)
        self.layout_right.addWidget(self.scroll_samples)

        # Action Buttons for Selected Card
        actions_bar = QHBoxLayout()
        actions_bar.setSpacing(8)

        self.btn_add_sample = QPushButton("➕ Thêm ảnh mẫu từ file...")
        self.btn_add_sample.setStyleSheet(
            "background-color: #30D158; color: white; font-weight: 700; border-radius: 6px; padding: 6px 12px;"
        )
        self.btn_add_sample.clicked.connect(self._on_add_sample_from_file)
        actions_bar.addWidget(self.btn_add_sample)

        self.btn_delete_selected = QPushButton("🗑️ Xóa mẫu đã chọn", objectName="DangerBtn")
        self.btn_delete_selected.setEnabled(False)
        self.btn_delete_selected.clicked.connect(self._on_delete_selected_sample)
        actions_bar.addWidget(self.btn_delete_selected)

        self.btn_delete_all = QPushButton("🧹 Xóa tất cả mẫu lá này", objectName="SecondaryBtn")
        self.btn_delete_all.clicked.connect(self._on_delete_all_samples_for_card)
        actions_bar.addWidget(self.btn_delete_all)

        actions_bar.addStretch()
        self.layout_right.addLayout(actions_bar)

        splitter.addWidget(box_right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)

        main_layout.addWidget(splitter)

        # ---------------------------------------------------------------------
        # 4. Footer
        # ---------------------------------------------------------------------
        footer = QHBoxLayout()
        footer.addStretch()

        btn_close = QPushButton("Đóng", objectName="SecondaryBtn")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)

        main_layout.addLayout(footer)

    def _refresh_all(self) -> None:
        """Reloads cache and refreshes entire UI."""
        self.library.reload_cache()
        self._populate_card_list()
        self._load_selected_card_samples()

    def _populate_card_list(self) -> None:
        """Filters and populates the 52 cards list."""
        self.list_cards.clear()
        summary = self.library.get_summary()
        counts = summary["counts"]
        total = summary["total_samples"]
        covered = summary["unique_cards_covered"]
        pct = summary["coverage_pct"]

        self.lbl_stats.setText(f"Tổng số ảnh mẫu: {total} | Đã có mẫu: {covered}/52 lá bài ({pct}%)")

        search_text = self.input_search.text().strip().upper()
        suit_idx = self.combo_suit_filter.currentIndex()
        cov_idx = self.combo_coverage_filter.currentIndex()

        suit_map = {1: Suit.SPADES, 2: Suit.CLUBS, 3: Suit.DIAMONDS, 4: Suit.HEARTS}
        target_suit = suit_map.get(suit_idx, None)

        for card in self.all_52_cards:
            code = f"{card.rank.char}{card.suit.char.upper()}"
            sample_count = counts.get(code, 0)

            # Suit filter
            if target_suit is not None and card.suit != target_suit:
                continue

            # Coverage filter (1: Has, 2: Missing)
            if cov_idx == 1 and sample_count == 0:
                continue
            if cov_idx == 2 and sample_count > 0:
                continue

            # Search text filter
            if search_text:
                if (
                    search_text not in code
                    and search_text not in card.unicode_name
                    and search_text not in card.rank.char
                ):
                    continue

            # Create List Item
            is_red = card.suit in (Suit.HEARTS, Suit.DIAMONDS)
            color_dot = "🔴" if is_red else "⚫"
            badge = f"[{sample_count} mẫu]" if sample_count > 0 else "[Chưa có]"

            item_text = f"{color_dot} {card.unicode_name} ({code})  {badge}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, card)

            if sample_count > 0:
                item.setForeground(Qt.white)
            else:
                item.setForeground(Qt.gray)

            self.list_cards.addItem(item)

        # Select first matching item if available
        if self.list_cards.count() > 0:
            self.list_cards.setCurrentRow(0)
            self.selected_card = self.list_cards.item(0).data(Qt.UserRole)
        else:
            self.selected_card = None

        self._load_selected_card_samples()

    def _on_card_item_clicked(self, item: QListWidgetItem) -> None:
        card = item.data(Qt.UserRole)
        self.selected_card = card
        self.selected_ref_id = None
        self.btn_delete_selected.setEnabled(False)
        self._load_selected_card_samples()

    def _load_selected_card_samples(self) -> None:
        """Renders thumbnails and metadata for the currently selected card."""
        # Clear previous samples from layout cleanly
        while self.layout_samples.count():
            child = self.layout_samples.takeAt(0)
            w = child.widget()
            if w is not None:
                w.setParent(None)
                w.hide()
                w.deleteLater()

        if not self.selected_card:
            self.lbl_selected_title.setText("Chưa chọn lá bài nào")
            return

        code = f"{self.selected_card.rank.char}{self.selected_card.suit.char.upper()}"
        refs = self.library.get_references_for_card(code)

        self.lbl_selected_title.setText(
            f"Lá bài: {self.selected_card.unicode_name} ({code}) — Có {len(refs)} ảnh mẫu đã xác nhận"
        )

        if not refs:
            empty_lbl = QLabel(
                f"Chưa có ảnh mẫu nào cho lá {self.selected_card.unicode_name}.\n"
                f"Hãy bấm '➕ Thêm ảnh mẫu từ file...' hoặc nhấn '💾 Lưu làm ảnh mẫu' khi quét bài."
            )
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #8E8E93; font-size: 13px; font-style: italic; padding: 40px;")
            self.layout_samples.addWidget(empty_lbl)
            self.btn_delete_all.setEnabled(False)
            self.btn_delete_selected.setEnabled(False)
            return

        self.btn_delete_all.setEnabled(True)

        for ref in refs:
            item_frame = self._create_sample_row_widget(ref)
            self.layout_samples.addWidget(item_frame)

        self.layout_samples.addStretch()

    def _create_sample_row_widget(self, ref: CardReference) -> QFrame:
        """Builds a row item for a reference sample with thumbnail and metadata."""
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #242426; border: 1px solid #3A3A3C; border-radius: 6px; padding: 6px; } "
            "QFrame:hover { border: 1px solid #0A84FF; }"
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        # Thumbnail
        lbl_thumb = QLabel()
        lbl_thumb.setFixedSize(54, 76)
        lbl_thumb.setStyleSheet("background-color: #000000; border: 1px solid #48484A; border-radius: 4px;")
        lbl_thumb.setAlignment(Qt.AlignCenter)

        img_path = Path(ref.image_path)
        if img_path.exists():
            img = cv2.imread(str(img_path))
            if img is not None:
                h, w = img.shape[:2]
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
                pix = QPixmap.fromImage(qimg).scaled(50, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                lbl_thumb.setPixmap(pix)
            else:
                lbl_thumb.setText("Lỗi")
        else:
            lbl_thumb.setText("Mất file")

        layout.addWidget(lbl_thumb)

        # Metadata Details
        meta_box = QVBoxLayout()
        meta_box.setSpacing(2)

        lbl_id = QLabel(f"ID: {ref.id[:12]}...  |  Mã băm (dHash): {ref.image_hash[:10]}...")
        lbl_id.setStyleSheet("font-size: 11px; font-weight: 700; color: #64D2FF;")
        meta_box.addWidget(lbl_id)

        lbl_date = QLabel(f"Thời gian lưu: {ref.created_at[:19].replace('T', ' ')}")
        lbl_date.setStyleSheet("font-size: 11px; color: #8E8E93;")
        meta_box.addWidget(lbl_date)

        lbl_src = QLabel(f"Nguồn: {ref.source}  |  Đã xác nhận: {'Có' if ref.confirmed else 'Chưa'}")
        lbl_src.setStyleSheet("font-size: 11px; color: #30D158;")
        meta_box.addWidget(lbl_src)

        layout.addLayout(meta_box, stretch=1)

        # Select / Delete button for this sample
        btn_del = QPushButton("Xóa", objectName="DangerBtn")
        btn_del.setFixedSize(50, 30)
        btn_del.clicked.connect(lambda _, r_id=ref.id: self._delete_single_reference(r_id))
        layout.addWidget(btn_del)

        return frame

    def _on_add_sample_from_file(self) -> None:
        """Allows user to import an image file as a confirmed sample for selected card."""
        if not self.selected_card:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Chọn ảnh mẫu cho lá {self.selected_card.unicode_name}",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not file_path:
            return

        img = cv2.imread(file_path)
        if img is None or img.size == 0:
            QMessageBox.critical(self, "Lỗi đọc file", "Không thể đọc ảnh từ file đã chọn.")
            return

        try:
            ref = self.library.add_reference(
                image=img,
                card=self.selected_card,
                source="manual_file_import",
                metadata={"imported_from": file_path},
            )
            QMessageBox.information(
                self,
                "Thêm thành công",
                f"Đã thêm ảnh mẫu cho lá {self.selected_card.unicode_name} ({ref.card_code}).",
            )
            self._refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi thêm ảnh mẫu", f"Không thể thêm ảnh mẫu: {e}")

    def _delete_single_reference(self, ref_id: str) -> None:
        """Deletes a single reference sample after user confirmation."""
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa mẫu",
            "Bạn có chắc muốn xóa ảnh mẫu này khỏi thư viện?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self.library.delete_reference(ref_id)
            self._refresh_all()

    def _on_delete_selected_sample(self) -> None:
        if self.selected_ref_id:
            self._delete_single_reference(self.selected_ref_id)

    def _on_delete_all_samples_for_card(self) -> None:
        if not self.selected_card:
            return
        code = f"{self.selected_card.rank.char}{self.selected_card.suit.char.upper()}"
        confirm = QMessageBox.question(
            self,
            "Xóa toàn bộ mẫu",
            f"Bạn có chắc chắn muốn xóa TOÀN BỘ ảnh mẫu của lá {self.selected_card.unicode_name} ({code})?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self.library.delete_references_for_card(code)
            self._refresh_all()
