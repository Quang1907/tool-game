"""Unit tests for Tab 7 Auto-Binh, 156-pair Gesture Mapper, MovePlanner, and MouseController."""

from __future__ import annotations
import json
import pytest

from app.automation.gesture_models import (
    CardSlot,
    GestureConfig,
    GesturePoint,
    GestureSample,
    MoveAction,
    MovePlan,
)
from app.automation.gesture_selector import GestureSelector
from app.automation.move_planner import MovePlanner
from app.automation.mouse_controller import MouseController
from app.automation.gesture_manager import GestureManager
from app.core.card import Card, Rank, Suit
from app.core.evaluator import HandCategory, HandEvaluation
from app.core.solver import HandArrangement, Solver
from app.database.db import DatabaseManager
from app.database.repository import AnalysisRepository


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_data.db"
    return DatabaseManager(db_path=db_file)


class TestGestureModelsAndDatabase:
    """Tests slot models, sample models, and SQLite persistence."""

    def test_slot_creation_and_defaults(self, temp_db):
        repo = AnalysisRepository(db_manager=temp_db)
        slots = repo.get_all_card_slots()
        assert len(slots) == 13, "Must have exactly 13 default card slots"

        front_slots = [s for s in slots if s.group_name == "front"]
        mid_slots = [s for s in slots if s.group_name == "middle"]
        back_slots = [s for s in slots if s.group_name == "back"]
        assert len(front_slots) == 3
        assert len(mid_slots) == 5
        assert len(back_slots) == 5

        # Modify a slot and save
        slots[0].rel_x = 0.38
        slots[0].rel_y = 0.29
        repo.save_card_slot(slots[0])

        reloaded = repo.get_all_card_slots()
        assert reloaded[0].rel_x == 0.38
        assert reloaded[0].rel_y == 0.29

    def test_gesture_sample_crud(self, temp_db):
        repo = AnalysisRepository(db_manager=temp_db)

        # Create sample for pair (1 -> 5)
        pts = [
            GesturePoint(rel_x=0.35, rel_y=0.28, time_ms=0),
            GesturePoint(rel_x=0.42, rel_y=0.40, time_ms=150),
            GesturePoint(rel_x=0.50, rel_y=0.50, time_ms=300),
        ]
        sample = GestureSample.create_new(
            source_slot=1,
            target_slot=5,
            name="Test Kéo 1 sang 5",
            points=pts,
            is_verified=True,
            weight=2.0,
        )
        repo.save_gesture_sample(sample)

        # Retrieve
        samples = repo.get_gesture_samples(source_slot=1, target_slot=5)
        assert len(samples) == 1
        s = samples[0]
        assert s.id == sample.id
        assert s.source_slot == 1
        assert s.target_slot == 5
        assert len(s.points) == 3
        assert s.is_verified is True
        assert s.weight == 2.0

        # Export and import JSON
        json_str = repo.export_gestures_json()
        assert "Test Kéo 1 sang 5" in json_str

        imported_count = repo.import_gestures_json(json_str)
        assert imported_count >= 1

        # Delete
        success = repo.delete_gesture_sample(sample.id)
        assert success is True
        assert len(repo.get_gesture_samples(source_slot=1, target_slot=5)) == 0


class TestGestureSelectorAndBezier:
    """Tests sample selection logic, weighted random, repeat avoidance, and Bézier curves."""

    def test_procedural_bezier_generation(self):
        sample = GestureSelector.generate_natural_bezier_sample(
            source_slot=1,
            target_slot=12,
            start_coord=(0.35, 0.28),
            end_coord=(0.64, 0.72),
            num_points=25,
            base_duration_ms=350,
            is_verified=True,
        )
        assert sample.source_slot == 1
        assert sample.target_slot == 12
        assert len(sample.points) == 25
        assert sample.total_duration_ms >= 240
        assert sample.is_verified is True

        # Check endpoints and monotonic timestamps
        assert abs(sample.points[0].rel_x - 0.35) < 0.001
        assert abs(sample.points[0].rel_y - 0.28) < 0.001
        assert abs(sample.points[-1].rel_x - 0.64) < 0.001
        assert abs(sample.points[-1].rel_y - 0.72) < 0.001

        for i in range(1, len(sample.points)):
            assert sample.points[i].time_ms >= sample.points[i - 1].time_ms

    def test_weighted_random_and_avoid_repeat(self):
        selector = GestureSelector(recent_history_size=3)
        pts = [GesturePoint(0.1, 0.1, 0), GesturePoint(0.2, 0.2, 100)]

        s1 = GestureSample.create_new(1, 2, "Sample 1", pts, is_verified=True, weight=1.0)
        s2 = GestureSample.create_new(1, 2, "Sample 2", pts, is_verified=True, weight=10.0)
        s3 = GestureSample.create_new(1, 2, "Sample 3", pts, is_verified=False, weight=1.0)

        cfg = GestureConfig(random_enabled=True, verified_only=True, avoid_consecutive_repeats=True)
        chosen1 = selector.select_gesture(1, 2, [s1, s2, s3], cfg)
        assert chosen1.is_verified is True

        # Next selection should avoid chosen1 if another candidate is available
        chosen2 = selector.select_gesture(1, 2, [s1, s2, s3], cfg)
        if len([s for s in [s1, s2] if s.id != chosen1.id]) > 0:
            assert chosen2.id != chosen1.id


class TestMovePlanner:
    """Tests minimal swap permutation cycle planning for auto-binh."""

    def test_plan_when_already_optimal(self):
        # Create a mock optimal partition
        front = [Card(Rank.THREE, Suit.SPADES), Card(Rank.THREE, Suit.HEARTS), Card(Rank.ACE, Suit.DIAMONDS)]
        mid = [Card(Rank.SIX, Suit.SPADES), Card(Rank.SIX, Suit.DIAMONDS), Card(Rank.SIX, Suit.CLUBS), Card(Rank.TEN, Suit.DIAMONDS), Card(Rank.NINE, Suit.SPADES)]
        back = [Card(Rank.KING, Suit.HEARTS), Card(Rank.QUEEN, Suit.SPADES), Card(Rank.QUEEN, Suit.CLUBS), Card(Rank.JACK, Suit.HEARTS), Card(Rank.EIGHT, Suit.DIAMONDS)]

        f_eval = HandEvaluation(category=HandCategory.ONE_PAIR, tie_breakers=(3, 14), cards=tuple(front), description="Pair 3", is_front_hand=True)
        m_eval = HandEvaluation(category=HandCategory.THREE_OF_A_KIND, tie_breakers=(6, 10, 9), cards=tuple(mid), description="Trips 6")
        b_eval = HandEvaluation(category=HandCategory.ONE_PAIR, tie_breakers=(12, 13, 11, 8), cards=tuple(back), description="Pair Q")

        partition = HandArrangement(front=tuple(front), middle=tuple(mid), back=tuple(back), front_eval=f_eval, middle_eval=m_eval, back_eval=b_eval, heuristic_score=100.0)

        # Slots currently hold exact cards
        current_slots = {}
        for i, c in enumerate(front, start=1): current_slots[i] = c
        for i, c in enumerate(mid, start=4): current_slots[i] = c
        for i, c in enumerate(back, start=9): current_slots[i] = c

        plan = MovePlanner.plan_moves(current_slots, partition)
        assert plan.is_already_optimal is True
        assert plan.total_swaps == 0
        assert len(plan.actions) == 0

    def test_plan_single_swap_between_front_and_back(self):
        front = [Card(Rank.THREE, Suit.SPADES), Card(Rank.THREE, Suit.HEARTS), Card(Rank.ACE, Suit.DIAMONDS)]
        mid = [Card(Rank.SIX, Suit.SPADES), Card(Rank.SIX, Suit.DIAMONDS), Card(Rank.SIX, Suit.CLUBS), Card(Rank.TEN, Suit.DIAMONDS), Card(Rank.NINE, Suit.SPADES)]
        back = [Card(Rank.KING, Suit.HEARTS), Card(Rank.QUEEN, Suit.SPADES), Card(Rank.QUEEN, Suit.CLUBS), Card(Rank.JACK, Suit.HEARTS), Card(Rank.EIGHT, Suit.DIAMONDS)]

        f_eval = HandEvaluation(category=HandCategory.ONE_PAIR, tie_breakers=(3, 14), cards=tuple(front), description="Pair 3", is_front_hand=True)
        m_eval = HandEvaluation(category=HandCategory.THREE_OF_A_KIND, tie_breakers=(6, 10, 9), cards=tuple(mid), description="Trips 6")
        b_eval = HandEvaluation(category=HandCategory.ONE_PAIR, tie_breakers=(12, 13, 11, 8), cards=tuple(back), description="Pair Q")

        partition = HandArrangement(front=tuple(front), middle=tuple(mid), back=tuple(back), front_eval=f_eval, middle_eval=m_eval, back_eval=b_eval, heuristic_score=100.0)

        # Invert card at slot 1 (3S) with card at slot 9 (KH)
        current_slots = {}
        for i, c in enumerate(front, start=1): current_slots[i] = c
        for i, c in enumerate(mid, start=4): current_slots[i] = c
        for i, c in enumerate(back, start=9): current_slots[i] = c

        current_slots[1] = Card(Rank.KING, Suit.HEARTS)
        current_slots[9] = Card(Rank.THREE, Suit.SPADES)

        plan = MovePlanner.plan_moves(current_slots, partition)
        assert plan.is_already_optimal is False
        assert plan.total_swaps == 1
        assert len(plan.actions) == 1
        act = plan.actions[0]
        assert (act.source_slot, act.target_slot) in [(1, 9), (9, 1)]


class TestMouseControllerMath:
    """Tests coordinate translations and controller safety."""

    def test_rel_to_screen_and_back(self):
        bounds = (200, 150, 1000, 800)
        rel_x, rel_y = (0.35, 0.50)

        screen_x, screen_y = MouseController.rel_to_screen(rel_x, rel_y, bounds)
        assert screen_x == 200 + 350
        assert screen_y == 150 + 400

        back_rx, back_ry = MouseController.screen_to_rel(screen_x, screen_y, bounds)
        assert abs(back_rx - rel_x) < 1e-6
        assert abs(back_ry - rel_y) < 1e-6


class TestGestureWidgetUI:
    """Tests Tab 7 GUI initialization and matrix table."""

    def test_gesture_widget_creation_and_matrix_structure(self, qapp, temp_db):
        from app.ui.components.gesture_widget import GestureWidget
        manager = GestureManager(repository=AnalysisRepository(db_manager=temp_db))
        widget = GestureWidget(gesture_manager=manager)

        # Check matrix table dimensions (13x13)
        assert widget.table_matrix.rowCount() == 13
        assert widget.table_matrix.columnCount() == 13

        # Check diagonal item is disabled
        diag_item = widget.table_matrix.item(0, 0)
        assert diag_item is not None
        assert diag_item.text() == "—"

        # Check non-diagonal item has count
        cell_item = widget.table_matrix.item(0, 1)
        assert cell_item is not None

        # Auto-fill all 156 Bézier samples
        created = manager.generate_missing_bezier_samples(overwrite_all=False)
        assert created == 156
        widget.refresh_all()

        updated_cell = widget.table_matrix.item(0, 1)
        assert updated_cell.text() == "1"

        widget.close()

    def test_visual_card_board_layout_and_three_rows(self, qapp, temp_db):
        """Verifies 13 card slot widgets mapped across 3 Mậu Binh rows:
        Row 1: 1, 2, 3 (Chi Đầu)
        Row 2: 4, 5, 6, 7, 8 (Chi Giữa)
        Row 3: 9, 10, 11, 12, 13 (Chi Cuối)
        """
        from app.ui.components.gesture_widget import GestureWidget
        manager = GestureManager(repository=AnalysisRepository(db_manager=temp_db))
        widget = GestureWidget(gesture_manager=manager)

        # 1. Check all 13 slots exist
        assert len(widget.slot_boxes) == 13
        for i in range(1, 14):
            assert i in widget.slot_boxes
            assert widget.slot_boxes[i].slot_number == i

        # 2. Check initial roles: Source = 1, Target = 2
        assert widget.slot_boxes[1].is_source is True
        assert widget.slot_boxes[2].is_target is True
        assert widget.slot_boxes[3].is_source is False
        assert widget.slot_boxes[3].is_target is False

        # 3. Click slot 5 on board -> Source becomes 5, Target becomes 1 (first target != 5)
        widget._on_slot_box_clicked(5)
        assert widget.active_source == 5
        assert widget.slot_boxes[5].is_source is True
        assert widget.slot_boxes[1].is_target is True

        widget.close()

    def test_guided_sequential_recording_wizard_navigation_and_saving(self, qapp, temp_db):
        """Tests sequential navigation of 12 target steps for slot 1 (2..13) and slot 2 (1, 3..13)."""
        from app.ui.components.gesture_widget import GestureWidget
        manager = GestureManager(repository=AnalysisRepository(db_manager=temp_db))
        widget = GestureWidget(gesture_manager=manager)

        # Initially Source is 1
        assert widget.active_source == 1
        assert widget.active_target_idx == 0
        assert widget._get_active_target_slot() == 2

        # Advance next step (1 -> 3)
        widget._on_wiz_next_clicked()
        assert widget.active_target_idx == 1
        assert widget._get_active_target_slot() == 3

        # Click chip for last target (target_idx = 11 -> slot 13)
        widget._on_target_chip_clicked(11)
        assert widget.active_target_idx == 11
        assert widget._get_active_target_slot() == 13

        # Simulate receiving recorded macro sample from recorder
        pts = [GesturePoint(0.35, 0.28, 0), GesturePoint(0.50, 0.50, 150), GesturePoint(0.78, 0.72, 320)]
        sample = GestureSample.create_new(
            source_slot=1,
            target_slot=13,
            name="Macro 1->13",
            points=pts,
            total_duration_ms=320,
            is_verified=True,
        )
        widget._on_recorder_finished(sample)

        # Verify sample was saved into repository
        saved_samples = manager.get_samples_for_pair(1, 13)
        assert len(saved_samples) == 1
        assert saved_samples[0].name == "Macro 1->13"

        # Switch to Source 2: Targets must be 1, then 3, 4, ... up to 13
        widget._on_source_button_clicked(2)
        assert widget.active_source == 2
        assert widget.active_target_idx == 0
        assert widget._get_active_target_slot() == 1  # 2 -> 1 first

        widget._on_wiz_next_clicked()
        assert widget._get_active_target_slot() == 3  # then 2 -> 3

        widget.close()

    def test_adapt_trajectory_to_endpoints(self):
        """Tests that recorded macro trajectories are dynamically warped to the exact live
        card coordinates regardless of fullscreen or shrunk window size.
        """
        pts = [
            GesturePoint(0.20, 0.20, 0),
            GesturePoint(0.40, 0.35, 100),
            GesturePoint(0.60, 0.65, 200),
            GesturePoint(0.80, 0.80, 300),
        ]
        target_start = (0.12, 0.45)
        target_end = (0.68, 0.91)

        adapted = GestureManager.adapt_trajectory_to_endpoints(pts, target_start, target_end)
        assert len(adapted) == len(pts)

        # 1. Exact start and end points
        assert abs(adapted[0].rel_x - target_start[0]) < 1e-4
        assert abs(adapted[0].rel_y - target_start[1]) < 1e-4
        assert abs(adapted[-1].rel_x - target_end[0]) < 1e-4
        assert abs(adapted[-1].rel_y - target_end[1]) < 1e-4

        # 2. Intermediate points scaled proportionally
        for p in adapted:
            assert 0.0 <= p.rel_x <= 1.0
            assert 0.0 <= p.rel_y <= 1.0

    def test_window_manager_live_bounds_query(self):
        from unittest.mock import patch
        from app.vision.window_manager import WindowItem, WindowManager

        wm = WindowManager()
        win = WindowItem(window_id=8888, owner_name="GameClient", title="Binh 13", bounds=(150, 120, 960, 640))

        with patch.object(wm, "list_windows", return_value=[win]):
            bounds = wm.get_window_bounds(8888)
            assert bounds == (150, 120, 960, 640)

            item = wm.get_window_by_id(8888)
            assert item is not None
            assert item.owner_name == "GameClient"

            # Invalid ID returns None
            assert wm.get_window_bounds(9999) is None

    def test_window_manager_activate_window(self):
        from unittest.mock import patch, MagicMock
        from app.vision.window_manager import WindowItem, WindowManager

        wm = WindowManager()
        win = WindowItem(window_id=7777, owner_name="Safari", title="Rikvip Game Bài", bounds=(100, 100, 1200, 800))

        with patch.object(wm, "list_windows", return_value=[win]), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Test by WindowItem
            ok = wm.activate_window(win)
            assert ok is True
            assert mock_run.called

            # Test by window_id
            ok_id = wm.activate_window(7777)
            assert ok_id is True

            # Test by app name
            ok_str = wm.activate_window("Google Chrome")
            assert ok_str is True

    def test_macro_recorder_live_bounds_getter(self, qapp):
        from unittest.mock import patch, MagicMock
        from PySide6.QtCore import QPoint
        from app.automation.macro_recorder import MacroRecorder

        recorder = MacroRecorder()
        # Button state: False (debounce), then True x 5, then False (release)
        state_calls = [False, True, True, True, True, True, False]
        def fake_is_pressed():
            if state_calls:
                return state_calls.pop(0)
            return False

        # Live shrunk bounds: 600x400 at (200, 200)
        shrunk_bounds = (200, 200, 600, 400)
        getter = MagicMock(return_value=shrunk_bounds)

        # Simulate moving cursor from center (500, 400) to (550, 450)
        cursor_positions = [
            QPoint(500, 400),
            QPoint(510, 410),
            QPoint(520, 420),
            QPoint(530, 430),
            QPoint(540, 440),
        ]
        def fake_cursor():
            if cursor_positions:
                return cursor_positions.pop(0)
            return QPoint(540, 440)

        with patch.object(recorder, "is_left_button_pressed", side_effect=fake_is_pressed), \
             patch("PySide6.QtGui.QCursor.pos", side_effect=fake_cursor):
            sample_holder = []
            recorder.recording_finished.connect(lambda s: sample_holder.append(s))

            recorder.start_recording(
                source_slot=1,
                target_slot=2,
                sample_name="TestShrunk",
                win_bounds=(0, 0, 1920, 1080),  # Fullscreen fallback
                timeout_seconds=5.0,
                bounds_getter=getter,
            )
            recorder._thread.join(timeout=3.0)
            qapp.processEvents()

            assert len(sample_holder) == 1
            s = sample_holder[0]
            # First recorded trajectory point is at (510, 410) on bounds (200, 200, 600, 400):
            # rel_x = (510 - 200) / 600.0 = 0.516667
            # rel_y = (410 - 200) / 400.0 = 0.525000
            expected_rx = (510 - 200) / 600.0
            expected_ry = (410 - 200) / 400.0
            assert abs(s.points[0].rel_x - expected_rx) < 1e-4
            assert abs(s.points[0].rel_y - expected_ry) < 1e-4
            assert len(s.points) >= 3



