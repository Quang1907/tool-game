"""Unit tests for PySide6 MainWindow and UI components in offscreen mode."""

import os
import pytest

# Use offscreen platform for headless automated testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.core.card import CardParser
from app.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestUIComponents:
    def test_main_window_initialization(self, qapp):
        window = MainWindow()
        assert window.windowTitle() == "Binh 13 Analyzer — macOS Professional Edition"
        assert window.tabs.count() == 5

        # Check tabs exist
        assert "Nhập bài" in window.tabs.tabText(0)
        assert "Quét màn hình" in window.tabs.tabText(1)
        assert "Xếp bài" in window.tabs.tabText(2)
        assert "Mô phỏng" in window.tabs.tabText(3)
        assert "Lịch sử" in window.tabs.tabText(4)

    def test_workflow_card_selection_to_solving(self, qapp):
        window = MainWindow()
        test_cards = CardParser.parse_cards("As Ks Qs Js 10s 9h 9d 8c 8s 7h 5d 3c 2h")

        # Simulate confirming cards from selector
        window.tab_selector.set_cards(test_cards)
        assert len(window.tab_selector.selected_cards) == 13
        assert window.tab_selector.btn_confirm.isEnabled() is True

        # Trigger confirmation
        window.tab_selector.btn_confirm.click()

        # Should automatically solve and switch to Tab 2 (index 2: Xếp bài & Chiến thuật)
        assert window.tabs.currentIndex() == 2
        assert len(window.current_arrangements) > 0
        assert window.tab_solver.current_arrangement is not None

        # Verify front, mid, back are rendered
        best = window.tab_solver.current_arrangement
        assert best.back_eval >= best.middle_eval
        assert not best.is_foul
