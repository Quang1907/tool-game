"""Solver view displaying the 3 partitioned hands and candidate arrangements."""

from __future__ import annotations
from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.solver import HandArrangement
from app.ui.components.card_widget import CardWidget


class SolverWidget(QWidget):
    """Displays 3 partitioned hands (Chi Đầu 3 lá, Chi Giữa 5 lá, Chi Cuối 5 lá) with ranking controls."""

    arrangement_selected = Signal(object)  # Emits HandArrangement
    strategy_changed = Signal(str)        # Emits strategy string

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.arrangements: List[HandArrangement] = []
        self.current_index: int = 0
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Controls Header
        ctrl_layout = QHBoxLayout()

        lbl_strat = QLabel("Chiến lược xếp:")
        lbl_strat.setStyleSheet("font-weight: 600;")
        ctrl_layout.addWidget(lbl_strat)

        self.combo_strategy = QComboBox()
        self.combo_strategy.addItems([
            "Cân bằng (Balanced)",
            "Ưu tiên Chi Đầu (Front-heavy)",
            "Ưu tiên Chi Cuối (Back-heavy)",
            "Ưu tiên Chi Giữa (Middle-heavy)",
        ])
        self.combo_strategy.currentIndexChanged.connect(self._on_strategy_changed)
        ctrl_layout.addWidget(self.combo_strategy)

        ctrl_layout.addStretch()

        self.btn_prev = QPushButton("◀ Phương án trước", objectName="SecondaryBtn")
        self.btn_prev.clicked.connect(self._prev_arrangement)
        ctrl_layout.addWidget(self.btn_prev)

        self.lbl_page = QLabel("0 / 0")
        self.lbl_page.setStyleSheet("font-weight: 700; color: #0A84FF; min-width: 60px;")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        ctrl_layout.addWidget(self.lbl_page)

        self.btn_next = QPushButton("Phương án sau ▶", objectName="SecondaryBtn")
        self.btn_next.clicked.connect(self._next_arrangement)
        ctrl_layout.addWidget(self.btn_next)

        main_layout.addLayout(ctrl_layout)

        # Status Badge
        self.lbl_status = QLabel("Chưa có bài để xếp. Hãy nhập 13 lá ở tab Nhập bài hoặc Quét màn hình.")
        self.lbl_status.setStyleSheet("color: #8E8E93; font-style: italic;")
        main_layout.addWidget(self.lbl_status)

        # 1. Front Hand Box (Chi Đầu - 3 cards)
        self.box_front = QGroupBox("Chi Đầu (3 lá bài)")
        layout_front = QVBoxLayout(self.box_front)
        self.lbl_front_cat = QLabel("Loại bài: -")
        self.lbl_front_cat.setStyleSheet("font-size: 14px; font-weight: 600; color: #30D158;")
        layout_front.addWidget(self.lbl_front_cat)

        self.cards_front_layout = QHBoxLayout()
        self.cards_front_layout.setSpacing(10)
        self.front_card_widgets = [CardWidget(width=58, height=84) for _ in range(3)]
        for w in self.front_card_widgets:
            self.cards_front_layout.addWidget(w)
        self.cards_front_layout.addStretch()
        layout_front.addLayout(self.cards_front_layout)
        main_layout.addWidget(self.box_front)

        # 2. Middle Hand Box (Chi Giữa - 5 cards)
        self.box_middle = QGroupBox("Chi Giữa (5 lá bài)")
        layout_middle = QVBoxLayout(self.box_middle)
        self.lbl_middle_cat = QLabel("Loại bài: -")
        self.lbl_middle_cat.setStyleSheet("font-size: 14px; font-weight: 600; color: #30D158;")
        layout_middle.addWidget(self.lbl_middle_cat)

        self.cards_middle_layout = QHBoxLayout()
        self.cards_middle_layout.setSpacing(10)
        self.middle_card_widgets = [CardWidget(width=58, height=84) for _ in range(5)]
        for w in self.middle_card_widgets:
            self.cards_middle_layout.addWidget(w)
        self.cards_middle_layout.addStretch()
        layout_middle.addLayout(self.cards_middle_layout)
        main_layout.addWidget(self.box_middle)

        # 3. Back Hand Box (Chi Cuối - 5 cards)
        self.box_back = QGroupBox("Chi Cuối (5 lá bài)")
        layout_back = QVBoxLayout(self.box_back)
        self.lbl_back_cat = QLabel("Loại bài: -")
        self.lbl_back_cat.setStyleSheet("font-size: 14px; font-weight: 600; color: #30D158;")
        layout_back.addWidget(self.lbl_back_cat)

        self.cards_back_layout = QHBoxLayout()
        self.cards_back_layout.setSpacing(10)
        self.back_card_widgets = [CardWidget(width=58, height=84) for _ in range(5)]
        for w in self.back_card_widgets:
            self.cards_back_layout.addWidget(w)
        self.cards_back_layout.addStretch()
        layout_back.addLayout(self.cards_back_layout)
        main_layout.addWidget(self.box_back)

        main_layout.addStretch()

    def set_arrangements(self, arrangements: List[HandArrangement]) -> None:
        self.arrangements = arrangements
        self.current_index = 0
        self._display_current()

    def _display_current(self) -> None:
        if not self.arrangements:
            self.lbl_page.setText("0 / 0")
            self.lbl_status.setText("Không tìm thấy phương án hợp lệ (bài lủng toàn bộ).")
            self.lbl_front_cat.setText("Loại bài: -")
            self.lbl_middle_cat.setText("Loại bài: -")
            self.lbl_back_cat.setText("Loại bài: -")
            for w in self.front_card_widgets + self.middle_card_widgets + self.back_card_widgets:
                w.set_card(None)
            return

        total = len(self.arrangements)
        arr = self.arrangements[self.current_index]

        self.lbl_page.setText(f"{self.current_index + 1} / {total}")
        self.lbl_status.setText(
            f"✓ Hợp lệ (Không lủng) • Điểm heuristic: {arr.heuristic_score:.1f} • "
            f"Xếp hạng: #{self.current_index + 1}"
        )
        self.lbl_status.setStyleSheet("color: #30D158; font-weight: 600;")

        # Populate Front
        self.lbl_front_cat.setText(f"Loại bài: {arr.front_eval.description}")
        for idx, card in enumerate(arr.front):
            self.front_card_widgets[idx].set_card(card)

        # Populate Middle
        self.lbl_middle_cat.setText(f"Loại bài: {arr.middle_eval.description}")
        for idx, card in enumerate(arr.middle):
            self.middle_card_widgets[idx].set_card(card)

        # Populate Back
        self.lbl_back_cat.setText(f"Loại bài: {arr.back_eval.description}")
        for idx, card in enumerate(arr.back):
            self.back_card_widgets[idx].set_card(card)

        self.arrangement_selected.emit(arr)

    def _prev_arrangement(self) -> None:
        if self.arrangements and self.current_index > 0:
            self.current_index -= 1
            self._display_current()

    def _next_arrangement(self) -> None:
        if self.arrangements and self.current_index < len(self.arrangements) - 1:
            self.current_index += 1
            self._display_current()

    def _on_strategy_changed(self, idx: int) -> None:
        strat_map = {
            0: "BALANCED",
            1: "FRONT_HEAVY",
            2: "BACK_HEAVY",
            3: "MIDDLE_HEAVY",
        }
        self.strategy_changed.emit(strat_map.get(idx, "BALANCED"))

    @property
    def current_arrangement(self) -> Optional[HandArrangement]:
        if self.arrangements and 0 <= self.current_index < len(self.arrangements):
            return self.arrangements[self.current_index]
        return None
