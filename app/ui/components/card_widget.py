"""Interactive visual representation of a playing card in PySide6."""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from app.core.card import Card, Suit


class CardWidget(QWidget):
    """Rendered visual playing card with rank, suit symbol, and selection highlight."""

    clicked = Signal(object)  # Emits self or Card

    def __init__(
        self,
        card: Optional[Card] = None,
        width: int = 56,
        height: int = 80,
        selectable: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.card = card
        self._width = width
        self._height = height
        self.selectable = selectable
        self.is_selected = False

        self.setFixedSize(self._width, self._height)
        self.setCursor(Qt.PointingHandCursor if selectable else Qt.ArrowCursor)

    def set_card(self, card: Optional[Card]) -> None:
        self.card = card
        self.update()

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        self.update()

    def mousePressEvent(self, event) -> None:
        if self.selectable:
            self.is_selected = not self.is_selected
            self.clicked.emit(self.card)
            self.update()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        radius = 8

        # Background Path
        path = QPainterPath()
        path.addRoundedRect(1, 1, w - 2, h - 2, radius, radius)

        # Draw card background
        if self.card is None:
            # Empty placeholder slot
            painter.fillPath(path, QColor("#2C2C2E"))
            painter.setPen(QPen(QColor("#48484A"), 1.5, Qt.DashLine))
            painter.drawPath(path)
            return

        # Active Card Background
        card_bg = QColor("#FFFFFF") if not self.is_selected else QColor("#E1F0FF")
        painter.fillPath(path, card_bg)

        # Border
        if self.is_selected:
            painter.setPen(QPen(QColor("#0A84FF"), 2.5))
        else:
            painter.setPen(QPen(QColor("#D1D1D6"), 1.0))
        painter.drawPath(path)

        # Determine suit color
        is_red = self.card.suit in (Suit.HEARTS, Suit.DIAMONDS)
        suit_color = QColor("#D70015") if is_red else QColor("#1C1C1E")

        painter.setPen(suit_color)

        # Draw Top-Left Rank & Suit
        font_rank = QFont("SF Pro Text", 11, QFont.Bold)
        font_suit = QFont("SF Pro Text", 12)

        painter.setFont(font_rank)
        painter.drawText(6, 16, self.card.rank.char)

        painter.setFont(font_suit)
        painter.drawText(6, 30, self.card.suit.symbol)

        # Draw Large Center Suit Symbol
        font_center = QFont("SF Pro Text", int(self._height * 0.35))
        painter.setFont(font_center)
        painter.drawText(0, 0, w, h, Qt.AlignCenter, self.card.suit.symbol)
