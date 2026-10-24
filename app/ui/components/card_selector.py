"""Interactive 52-card selection panel for picking 13 unique player cards."""

from __future__ import annotations
from typing import List, Set
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.card import Card, CardParser, Rank, Suit
from app.ui.components.card_widget import CardWidget


class CardSelectorWidget(QWidget):
    """Panel displaying 52 cards arranged in suit rows for interactive 13-card selection."""

    cards_changed = Signal(list)  # Emits list[Card] when selection changes
    confirmed = Signal(list)      # Emits list[Card] when user confirms 13 cards

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.selected_cards: Set[Card] = set()
        self.card_widgets: dict[int, CardWidget] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header info
        header_layout = QHBoxLayout()
        self.lbl_count = QLabel("Đã chọn: 0 / 13 lá bài")
        self.lbl_count.setStyleSheet("font-size: 16px; font-weight: 700; color: #0A84FF;")
        header_layout.addWidget(self.lbl_count)
        header_layout.addStretch()

        btn_sample = QPushButton("Bộ bài mẫu", objectName="SecondaryBtn")
        btn_sample.clicked.connect(self._load_sample_hand)
        header_layout.addWidget(btn_sample)

        btn_clear = QPushButton("Xóa chọn", objectName="DangerBtn")
        btn_clear.clicked.connect(self.clear_selection)
        header_layout.addWidget(btn_clear)

        main_layout.addLayout(header_layout)

        # Grid of 52 cards (4 suits x 13 ranks)
        suits = [Suit.SPADES, Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS]
        ranks = [
            Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX,
            Rank.SEVEN, Rank.EIGHT, Rank.NINE, Rank.TEN,
            Rank.JACK, Rank.QUEEN, Rank.KING, Rank.ACE
        ]

        for suit in suits:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(6)

            # Suit label
            suit_lbl = QLabel(f"{suit.symbol} {suit.vietnamese_name}")
            suit_lbl.setFixedWidth(75)
            suit_lbl.setStyleSheet("font-weight: 600; color: #8E8E93;")
            row_layout.addWidget(suit_lbl)

            for rank in ranks:
                card = Card(rank, suit)
                w = CardWidget(card=card, width=42, height=60, selectable=True)
                w.clicked.connect(lambda c=card: self._on_card_clicked(c))
                self.card_widgets[card.card_id] = w
                row_layout.addWidget(w)

            row_layout.addStretch()
            main_layout.addLayout(row_layout)

        # Footer Actions
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        self.btn_confirm = QPushButton("Xác nhận 13 lá bài")
        self.btn_confirm.setFixedHeight(38)
        self.btn_confirm.setFixedWidth(200)
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self._on_confirm)
        footer_layout.addWidget(self.btn_confirm)

        main_layout.addLayout(footer_layout)

    def _on_card_clicked(self, card: Card) -> None:
        if card in self.selected_cards:
            self.selected_cards.remove(card)
            self.card_widgets[card.card_id].set_selected(False)
        else:
            if len(self.selected_cards) >= 13:
                # Max 13 cards reached
                self.card_widgets[card.card_id].set_selected(False)
                return
            self.selected_cards.add(card)
            self.card_widgets[card.card_id].set_selected(True)

        self._update_status()

    def _update_status(self) -> None:
        count = len(self.selected_cards)
        self.lbl_count.setText(f"Đã chọn: {count} / 13 lá bài")
        if count == 13:
            self.lbl_count.setStyleSheet("font-size: 16px; font-weight: 700; color: #30D158;")
            self.btn_confirm.setEnabled(True)
        else:
            self.lbl_count.setStyleSheet("font-size: 16px; font-weight: 700; color: #0A84FF;")
            self.btn_confirm.setEnabled(False)

        self.cards_changed.emit(list(self.selected_cards))

    def clear_selection(self) -> None:
        self.selected_cards.clear()
        for w in self.card_widgets.values():
            w.set_selected(False)
        self._update_status()

    def _load_sample_hand(self) -> None:
        """Loads a pre-made interesting 13-card hand for rapid testing."""
        self.clear_selection()
        sample = CardParser.parse_cards("As Ks Qs Js 10s 9h 9d 8c 8s 7h 5d 3c 2h")
        self.set_cards(sample)

    def set_cards(self, cards: List[Card]) -> None:
        self.clear_selection()
        for c in cards[:13]:
            self.selected_cards.add(c)
            if c.card_id in self.card_widgets:
                self.card_widgets[c.card_id].set_selected(True)
        self._update_status()

    def _on_confirm(self) -> None:
        if len(self.selected_cards) == 13:
            self.confirmed.emit(list(self.selected_cards))
