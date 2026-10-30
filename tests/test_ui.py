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
        assert window.tabs.count() == 7

        # Check tabs exist
        assert "Nhập bài" in window.tabs.tabText(0)
        assert "Quét màn hình" in window.tabs.tabText(1)
        assert "Xếp bài" in window.tabs.tabText(2)
        assert "Mô phỏng" in window.tabs.tabText(3)
        assert "Lịch sử" in window.tabs.tabText(4)
        assert "Bot 3 Cửa Sổ" in window.tabs.tabText(5)
        assert "Tự động binh bài" in window.tabs.tabText(6)

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

    def test_vision_widget_image_loading_and_zoom(self, qapp):
        import numpy as np
        window = MainWindow()
        vision_tab = window.tab_vision

        # Load dummy test image (300x500 BGR)
        dummy_img = np.zeros((300, 500, 3), dtype=np.uint8)
        dummy_img[50:250, 50:450] = (255, 255, 255)

        vision_tab.set_image(dummy_img)
        assert vision_tab.current_image is not None
        assert vision_tab.btn_recognize.isEnabled() is True
        assert vision_tab.btn_clear_img.isEnabled() is True

        # Test zoom controls
        init_zoom = vision_tab.image_viewer._zoom_factor
        vision_tab.image_viewer.zoom_in()
        assert vision_tab.image_viewer._zoom_factor > init_zoom

        vision_tab.image_viewer.zoom_out()
        vision_tab.image_viewer.fit_in_view()
        assert vision_tab.image_viewer._zoom_factor == 1.0

        # Test clear
        vision_tab._clear_image()
        assert vision_tab.current_image is None
        assert vision_tab.btn_recognize.isEnabled() is False

    def test_card_edit_dialog_confirmation_and_save_reference(self, qapp, tmp_path):
        import numpy as np
        from app.core.card import Card, Rank, Suit
        from app.database.db import DatabaseManager
        from app.ui.components.card_edit_dialog import CardEditDialog
        from app.vision.card_recognizer import DetectedCard
        from app.vision.card_reference_library import CardReferenceLibrary

        db = DatabaseManager(db_path=tmp_path / "test_ui.db")
        lib = CardReferenceLibrary(db_manager=db, storage_dir=tmp_path / "refs")

        # Mock detected card crop
        raw_crop = np.full((140, 100, 3), 240, dtype=np.uint8)
        det = DetectedCard(
            card=Card(Rank.ACE, Suit.SPADES),
            confidence=0.88,
            bbox=(10, 20, 100, 140),
            raw_crop=raw_crop,
            alternative_candidates=[("AS", 0.88), ("4S", 0.62)],
        )

        dialog = CardEditDialog(detected_card=det, reference_library=lib)
        assert "A♠" in dialog.lbl_pred_badge.text()
        assert dialog.selected_card == Card(Rank.ACE, Suit.SPADES)

        # Select King of Hearts
        card_kh = Card(Rank.KING, Suit.HEARTS)
        dialog._select_card(card_kh)
        assert dialog.selected_card == card_kh

        # Save as reference
        from unittest.mock import patch
        from PySide6.QtWidgets import QMessageBox
        with patch("PySide6.QtWidgets.QMessageBox.information") as mock_info, \
             patch("PySide6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            dialog._on_save_as_reference_clicked()
            assert dialog.saved_as_reference is True
            assert dialog.is_confirmed is True

        # Verify reference library persisted the crop under KH
        saved_refs = lib.get_references_for_card("KH")
        assert len(saved_refs) == 1
        assert saved_refs[0].card_code == "KH"

    def test_card_reference_manager_dialog(self, qapp, tmp_path):
        from app.core.card import Card, Rank, Suit
        from app.database.db import DatabaseManager
        from app.ui.components.card_reference_manager import CardReferenceManagerDialog
        from app.vision.card_reference_library import CardReferenceLibrary
        import numpy as np

        db = DatabaseManager(db_path=tmp_path / "test_mgr.db")
        lib = CardReferenceLibrary(db_manager=db, storage_dir=tmp_path / "refs")

        # Add sample for 10D
        img = np.full((120, 90, 3), 245, dtype=np.uint8)
        lib.add_reference(image=img, card=Card(Rank.TEN, Suit.DIAMONDS))

        dialog = CardReferenceManagerDialog(reference_library=lib)
        assert dialog.list_cards.count() == 52

        # Test search filter
        dialog.input_search.setText("10D")
        assert dialog.list_cards.count() == 1
        item = dialog.list_cards.item(0)
        assert "10D" in item.text()

        # Reset search
        dialog.input_search.setText("")
        assert dialog.list_cards.count() == 52
        dialog.close()

