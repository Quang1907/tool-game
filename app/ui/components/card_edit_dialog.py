"""Card Edit Dialog allowing quick manual correction of misidentified cards."""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.card import Card, Rank, Suit
from app.ui.components.card_widget import CardWidget


class CardEditDialog(QDialog):
    """Dialog allowing user to click and pick the correct card for a detected slot."""

    def __init__(self, current_card: Optional[Card] = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Chỉnh sửa lá bài")
        self.setFixedSize(540, 320)
        self.selected_card: Optional[Card] = current_card
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Chọn lá bài chính xác:")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0A84FF;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(4)

        suits = [Suit.SPADES, Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS]
        ranks = [
            Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX,
            Rank.SEVEN, Rank.EIGHT, Rank.NINE, Rank.TEN,
            Rank.JACK, Rank.QUEEN, Rank.KING, Rank.ACE
        ]

        for row_idx, suit in enumerate(suits):
            suit_lbl = QLabel(f"{suit.symbol}")
            suit_lbl.setStyleSheet("font-weight: 700; font-size: 14px; color: #8E8E93;")
            grid.addWidget(suit_lbl, row_idx, 0)

            for col_idx, rank in enumerate(ranks):
                card = Card(rank, suit)
                btn = QPushButton(f"{rank.char}")
                btn.setFixedSize(32, 38)
                is_red = suit in (Suit.HEARTS, Suit.DIAMONDS)
                color_hex = "#D70015" if is_red else "#FFFFFF"
                btn.setStyleSheet(f"font-weight: 700; color: {color_hex}; background-color: #2C2C2E; padding: 2px;")
                btn.clicked.connect(lambda _, c=card: self._select_and_accept(c))
                grid.addWidget(btn, row_idx, col_idx + 1)

        layout.addLayout(grid)

        # Cancel button
        btn_cancel = QPushButton("Hủy", objectName="SecondaryBtn")
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel, alignment=Qt.AlignRight)

    def _select_and_accept(self, card: Card) -> None:
        self.selected_card = card
        self.accept()
