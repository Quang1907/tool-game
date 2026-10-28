"""Unit and Integration tests for Multi-Window macOS Bot, CardTracker, and Invariant State."""

import numpy as np
import pytest

from app.core.card import Card, Rank, Suit
from app.vision.card_detector import CardCrop, CardDetection, CardDetector, CardTracker
from app.vision.card_recognizer import DetectedCard
from app.vision.card_state import CardStateManager, WindowCardState
from app.vision.roi_manager import ROIManager, WindowROI
from app.vision.window_manager import WindowItem, WindowManager


class TestCardTrackerAndPositionInvariance:
    def test_card_tracker_movement_vs_change(self):
        """CardTracker distinguishes card movement (no solve) from card content change (solve)."""
        tracker = CardTracker(debounce_frames=2)

        # Frame 1: 5 cards at Position A
        c1 = Card(Rank.ACE, Suit.SPADES)
        c2 = Card(Rank.KING, Suit.HEARTS)
        c3 = Card(Rank.QUEEN, Suit.DIAMONDS)

        cards_frame1 = [
            DetectedCard(card=c1, confidence=0.95, bbox=(10, 10, 50, 70), raw_crop=np.zeros((70, 50, 3))),
            DetectedCard(card=c2, confidence=0.95, bbox=(70, 10, 50, 70), raw_crop=np.zeros((70, 50, 3))),
            DetectedCard(card=c3, confidence=0.95, bbox=(130, 10, 50, 70), raw_crop=np.zeros((70, 50, 3))),
        ]

        status1, should_recalc1 = tracker.evaluate_frame(cards_frame1)
        assert status1 == "CONTENT_CHANGED"
        assert should_recalc1 is True

        # Frame 2: Same 3 cards moved to Position B (+50px shift)
        cards_frame2 = [
            DetectedCard(card=c1, confidence=0.95, bbox=(60, 60, 50, 70), raw_crop=np.zeros((70, 50, 3))),
            DetectedCard(card=c2, confidence=0.95, bbox=(120, 60, 50, 70), raw_crop=np.zeros((70, 50, 3))),
            DetectedCard(card=c3, confidence=0.95, bbox=(180, 60, 50, 70), raw_crop=np.zeros((70, 50, 3))),
        ]

        status2, should_recalc2 = tracker.evaluate_frame(cards_frame2)
        assert status2 == "MOVED_NO_RECALCULATE"
        assert should_recalc2 is False, "Moving cards must NOT trigger solver recalculation"

        # Frame 3: One card changes rank (Queen -> Jack)
        c3_new = Card(Rank.JACK, Suit.DIAMONDS)
        cards_frame3 = [
            DetectedCard(card=c1, confidence=0.95, bbox=(60, 60, 50, 70), raw_crop=np.zeros((70, 50, 3))),
            DetectedCard(card=c2, confidence=0.95, bbox=(120, 60, 50, 70), raw_crop=np.zeros((70, 50, 3))),
            DetectedCard(card=c3_new, confidence=0.95, bbox=(180, 60, 50, 70), raw_crop=np.zeros((70, 50, 3))),
        ]

        status3, should_recalc3 = tracker.evaluate_frame(cards_frame3)
        assert status3 == "CONTENT_CHANGED"
        assert should_recalc3 is True, "Card content change MUST trigger solver recalculation"

    def test_state_manager_position_invariant_hash(self):
        """CardStateManager hash is strictly invariant to spatial card ordering and positions."""
        state_mgr = CardStateManager()

        c_a = Card(Rank.ACE, Suit.SPADES)
        c_k = Card(Rank.KING, Suit.HEARTS)

        list1 = [
            DetectedCard(card=c_a, confidence=0.9, bbox=(10, 20, 40, 60), raw_crop=np.zeros((60, 40, 3))),
            DetectedCard(card=c_k, confidence=0.9, bbox=(80, 20, 40, 60), raw_crop=np.zeros((60, 40, 3))),
        ]

        # Swapped positions and different coordinates
        list2 = [
            DetectedCard(card=c_k, confidence=0.9, bbox=(200, 300, 40, 60), raw_crop=np.zeros((60, 40, 3))),
            DetectedCard(card=c_a, confidence=0.9, bbox=(500, 400, 40, 60), raw_crop=np.zeros((60, 40, 3))),
        ]

        hash1 = state_mgr.compute_position_invariant_hash(list1)
        hash2 = state_mgr.compute_position_invariant_hash(list2)

        assert hash1 != ""
        assert hash1 == hash2, "Position-invariant hash must be identical regardless of card positions or ordering"


class TestROIManagerAndOcclusion:
    def test_roi_manager_retina_2x_crop(self):
        """ROIManager scales macOS screen points by Retina 2.0x factor and offsets titlebar."""
        # 1000x800 full frame
        frame = np.zeros((800, 1000, 3), dtype=np.uint8)
        frame[100:600, 200:800] = (255, 255, 255)

        roi_mgr = ROIManager(retina_scale=2.0)
        # Window at x=100, y=50, w=300, h=250 points, titlebar=28 points
        roi = WindowROI(window_id=1, name="Game 1", bounds_pts=(100, 50, 300, 250), titlebar_inset_pts=28)

        crop = roi_mgr.crop_window_roi(frame, roi)
        assert crop is not None
        # Width: 300 * 2.0 = 600 px
        # Height: (250 - 28) * 2.0 = 222 * 2.0 = 444 px
        assert crop.shape == (444, 600, 3)

    def test_window_manager_occlusion_calculation(self):
        """WindowManager detects when target window is occluded by another window on top."""
        wm = WindowManager()

        target = WindowItem(window_id=101, owner_name="Game", title="Table 1", bounds=(100, 100, 400, 300))
        # Window in front (earlier in list) completely covering target
        covering = WindowItem(window_id=202, owner_name="Safari", title="Browser", bounds=(50, 50, 500, 400))

        occluded = wm.compute_occlusion(target, [covering, target])
        assert occluded.is_occluded is True
        assert occluded.occlusion_ratio >= 0.90

    def test_window_manager_ignores_analyzer_self_window(self):
        """WindowManager does not let Binh 13 Analyzer occlude user game windows."""
        wm = WindowManager()
        target = WindowItem(window_id=101, owner_name="GameApp", title="Table 1", bounds=(0, 0, 800, 600))
        analyzer = WindowItem(window_id=999, owner_name="Python", title="Binh 13 Analyzer — macOS Professional Edition", bounds=(0, 0, 800, 600))

        occluded = wm.compute_occlusion(target, [analyzer, target])
        assert occluded.is_occluded is False
        assert occluded.occlusion_ratio == 0.0


class TestDirectWindowCaptureAndSelection:
    """Verifies that selecting a window immediately captures, displays, detects, and solves."""

    def test_capture_window_by_id_invalid_id(self):
        from app.vision.screen_capture import ScreenCapture
        assert ScreenCapture.capture_window_by_id(0) is None
        assert ScreenCapture.capture_window_by_id(-1) is None

    def test_multi_window_selection_updates_preview_and_solution(self, qapp):
        from unittest.mock import patch
        from app.ui.components.multi_window_widget import MultiWindowWidget
        from app.vision.screen_capture import ScreenCapture
        import cv2

        widget = MultiWindowWidget()
        win = WindowItem(window_id=77777, owner_name="TestGame", title="Binh Table", bounds=(0, 0, 600, 400))
        widget.discovered_windows = [win]
        widget.combo_w1.clear()
        widget.combo_w1.addItem(win.display_label, win.window_id)

        # Mock capture_window_by_id to return a synthetic image
        synth_img = np.full((400, 600, 3), 40, dtype=np.uint8)

        with patch.object(ScreenCapture, "capture_window_by_id", return_value=synth_img):
            widget._on_window_selected(1)

        panel = widget.panels[1]
        assert "Đã kết nối" in panel.lbl_status.text()
        assert panel.viewer._current_image is not None

        # Test with 13 detected cards to verify solver.solve_heuristic integration
        from app.core.card import CardParser
        from app.vision.card_recognizer import DetectedCard

        sample_cards = CardParser.parse_cards("As Ks Qs Js 10s 9h 8h 7h 6h 5h 4c 3c 2c")
        mock_detected = [
            DetectedCard(
                card=c,
                confidence=0.99,
                rank_confidence=0.99,
                suit_confidence=0.99,
                bbox=(i * 20, 0, 40, 60),
                raw_crop=np.zeros((60, 40, 3), dtype=np.uint8),
            )
            for i, c in enumerate(sample_cards)
        ]

        with patch.object(ScreenCapture, "capture_window_by_id", return_value=synth_img), \
             patch("app.ui.components.multi_window_widget.recognize_cards_pipeline", return_value=(mock_detected, None)):
            widget._on_window_selected(1)

        assert "13 lá — Đã có gợi ý tối ưu" in panel.lbl_status.text()
        assert panel.lbl_chi_front.text().startswith("Chi Đầu:")
        assert panel.lbl_chi_middle.text().startswith("Chi Giữa:")
        assert panel.lbl_chi_back.text().startswith("Chi Cuối:")

        widget.close()

    def test_multi_window_deduces_opponent_and_optimizes_counter_strategy(self, qapp):
        from app.core.card import CardParser, Deck
        from app.ui.components.multi_window_widget import MultiWindowWidget

        widget = MultiWindowWidget()
        deck = Deck()
        deck.shuffle(seed=123)

        w1_cards = deck.deal(13)
        w2_cards = deck.deal(13)
        w3_cards = deck.deal(13)
        actual_opp_cards = deck.deal(13)

        widget.window_cards[1] = w1_cards
        widget.window_cards[2] = w2_cards
        widget.window_cards[3] = w3_cards

        widget._evaluate_table_strategy()

        # Verify Opponent Panel displays deduction
        opp_panel = widget.opponent_panel
        assert "ĐÃ KHÓA CHẶT 13 LÁ ĐỐI THỦ" in opp_panel.lbl_status.text()
        assert opp_panel.lbl_chi_front.text().startswith("Chi Đầu:")
        assert opp_panel.lbl_chi_middle.text().startswith("Chi Giữa:")
        assert opp_panel.lbl_chi_back.text().startswith("Chi Cuối:")

        # Verify all 3 panels received counter strategy
        for idx in (1, 2, 3):
            p = widget.panels[idx]
            assert p.lbl_opp_outcome.text() != "Đang chờ đủ 3 cửa sổ..."
            assert "Đầu:" in p.lbl_opp_breakdown.text()

        widget.close()

    def test_shared_vision_pipeline_and_reference_library(self, qapp):
        """Verifies that MainWindow passes the exact same detector, recognizer, and reference_library to both Tab 2 and Tab 6."""
        from app.ui.main_window import MainWindow

        win = MainWindow()
        assert win.tab_multi_bot.detector is win.tab_vision.detector
        assert win.tab_multi_bot.recognizer is win.tab_vision.recognizer
        assert win.tab_multi_bot.reference_library is win.tab_vision.reference_library
        win.close()



