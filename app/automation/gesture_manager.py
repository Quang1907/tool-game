"""Gesture Manager: Orchestrates card slots, 156 directed pair samples, and auto-binh execution."""

from __future__ import annotations
import time
from typing import Callable, Dict, List, Optional, Set, Tuple

from PySide6.QtCore import QObject, QThread, Signal

from app.automation.gesture_models import (
    CardSlot,
    GestureConfig,
    GesturePoint,
    GestureSample,
    MoveAction,
    MovePlan,
)
from app.automation.gesture_selector import GestureSelector
from app.automation.mouse_controller import MouseController
from app.database.repository import AnalysisRepository


class GestureManager(QObject):
    """High-level facade connecting SQLite storage, 156-pair gestures, and execution engine."""

    action_started = Signal(int, int, str)    # step_index, total_steps, description
    action_completed = Signal(int, int)       # step_index, total_steps
    execution_finished = Signal(bool, str)    # success, message

    def __init__(self, repository: Optional[AnalysisRepository] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.repository = repository or AnalysisRepository()
        self.selector = GestureSelector()
        self.mouse = MouseController()
        self.config = GestureConfig()

        self._slots: Dict[int, CardSlot] = {}
        self._samples: List[GestureSample] = []
        self.reload_data()

    def reload_data(self) -> None:
        """Loads all slots and gesture samples from the database."""
        slots_list = self.repository.get_all_card_slots()
        self._slots = {s.slot_number: s for s in slots_list}
        self._samples = self.repository.get_gesture_samples()

    def get_slots(self) -> Dict[int, CardSlot]:
        """Returns the 13 card slots."""
        if not self._slots:
            self.reload_data()
        return self._slots

    def get_slot(self, slot_num: int) -> Optional[CardSlot]:
        return self._slots.get(slot_num)

    def save_slot(self, slot: CardSlot) -> None:
        """Saves a card slot and updates memory cache."""
        self.repository.save_card_slot(slot)
        self._slots[slot.slot_number] = slot

    def get_all_samples(self) -> List[GestureSample]:
        return list(self._samples)

    def get_samples_for_pair(self, source_slot: int, target_slot: int) -> List[GestureSample]:
        return [s for s in self._samples if s.source_slot == source_slot and s.target_slot == target_slot]

    def get_pair_stats_matrix(self) -> Dict[Tuple[int, int], Tuple[int, bool]]:
        """Returns a mapping of (source, target) -> (sample_count, has_verified_sample) for all 156 pairs."""
        stats: Dict[Tuple[int, int], Tuple[int, bool]] = {}
        for s in range(1, 14):
            for d in range(1, 14):
                if s == d:
                    continue
                pair_samples = [smp for smp in self._samples if smp.source_slot == s and smp.target_slot == d]
                count = len(pair_samples)
                has_verified = any(smp.is_verified for smp in pair_samples)
                stats[(s, d)] = (count, has_verified)
        return stats

    def save_sample(self, sample: GestureSample) -> None:
        """Saves or updates a sample in database and memory."""
        self.repository.save_gesture_sample(sample)
        # Update cache
        self._samples = [s for s in self._samples if s.id != sample.id]
        self._samples.append(sample)

    def delete_sample(self, sample_id: str) -> bool:
        """Deletes a sample by ID."""
        success = self.repository.delete_gesture_sample(sample_id)
        if success:
            self._samples = [s for s in self._samples if s.id != sample_id]
        return success

    def generate_missing_bezier_samples(self, overwrite_all: bool = False) -> int:
        """Generates natural Bézier trajectories for all 156 pairs based on slot coordinates."""
        slots = self.get_slots()
        created_count = 0

        for s in range(1, 14):
            for d in range(1, 14):
                if s == d:
                    continue

                existing = self.get_samples_for_pair(s, d)
                if existing and not overwrite_all:
                    continue

                s_slot = slots.get(s)
                d_slot = slots.get(d)
                s_coords = (s_slot.rel_x, s_slot.rel_y) if s_slot else (0.2, 0.2)
                d_coords = (d_slot.rel_x, d_slot.rel_y) if d_slot else (0.8, 0.8)

                sample = self.selector.generate_natural_bezier_sample(
                    source_slot=s,
                    target_slot=d,
                    start_coord=s_coords,
                    end_coord=d_coords,
                    is_verified=True,
                )
                sample.name = f"Bézier Chuẩn: {s} ➔ {d}"
                self.save_sample(sample)
                created_count += 1

        return created_count

    @staticmethod
    def adapt_trajectory_to_endpoints(
        points: List[GesturePoint],
        target_start: Tuple[float, float],
        target_end: Tuple[float, float],
    ) -> List[GesturePoint]:
        """Adapts a recorded gesture trajectory so that it begins exactly at target_start
        and ends exactly at target_end, while preserving intermediate curvature, speed,
        and human kinematic wavers across any window size (fullscreen, shrunk, or moved).
        """
        if not points:
            return [
                GesturePoint(rel_x=target_start[0], rel_y=target_start[1], time_ms=0),
                GesturePoint(rel_x=target_end[0], rel_y=target_end[1], time_ms=300),
            ]

        n = len(points)
        if n == 1:
            return [GesturePoint(rel_x=target_start[0], rel_y=target_start[1], time_ms=points[0].time_ms)]

        orig_start_x = points[0].rel_x
        orig_start_y = points[0].rel_y
        orig_end_x = points[-1].rel_x
        orig_end_y = points[-1].rel_y

        tgt_start_x, tgt_start_y = target_start
        tgt_end_x, tgt_end_y = target_end

        orig_dx = orig_end_x - orig_start_x
        orig_dy = orig_end_y - orig_start_y
        tgt_dx = tgt_end_x - tgt_start_x
        tgt_dy = tgt_end_y - tgt_start_y

        # Scale factors for human hand deviations
        scale_x = abs(tgt_dx / orig_dx) if abs(orig_dx) > 0.02 else 1.0
        scale_y = abs(tgt_dy / orig_dy) if abs(orig_dy) > 0.02 else 1.0
        scale_x = max(0.2, min(2.5, scale_x))
        scale_y = max(0.2, min(2.5, scale_y))

        adapted: List[GesturePoint] = []
        for i, pt in enumerate(points):
            alpha = i / float(n - 1)

            # Original baseline linear point
            l_orig_x = (1.0 - alpha) * orig_start_x + alpha * orig_end_x
            l_orig_y = (1.0 - alpha) * orig_start_y + alpha * orig_end_y

            # Human deviation from baseline
            dev_x = pt.rel_x - l_orig_x
            dev_y = pt.rel_y - l_orig_y

            # Target baseline linear point
            l_tgt_x = (1.0 - alpha) * tgt_start_x + alpha * tgt_end_x
            l_tgt_y = (1.0 - alpha) * tgt_start_y + alpha * tgt_end_y

            # Adapted coordinates
            new_x = l_tgt_x + dev_x * scale_x
            new_y = l_tgt_y + dev_y * scale_y

            # Clamp within [0.0, 1.0]
            new_x = max(0.0, min(1.0, new_x))
            new_y = max(0.0, min(1.0, new_y))

            adapted.append(GesturePoint(rel_x=new_x, rel_y=new_y, time_ms=pt.time_ms))

        # Guarantee exact endpoints
        adapted[0].rel_x = max(0.0, min(1.0, tgt_start_x))
        adapted[0].rel_y = max(0.0, min(1.0, tgt_start_y))
        adapted[-1].rel_x = max(0.0, min(1.0, tgt_end_x))
        adapted[-1].rel_y = max(0.0, min(1.0, tgt_end_y))

        return adapted

    def execute_move_plan(
        self,
        plan: MovePlan,
        win_bounds: Tuple[int, int, int, int],
        config: Optional[GestureConfig] = None,
        stop_check: Optional[Callable[[], bool]] = None,
        live_slot_coords: Optional[Dict[int, Tuple[float, float]]] = None,
    ) -> bool:
        """Executes the complete sequence of swap moves on the game window, dynamically adapting
        trajectories to live detected card slot positions if available.
        """
        cfg = config or self.config
        total = len(plan.actions)
        if total == 0:
            self.execution_finished.emit(True, "Bài đã ở vị trí tối ưu, không cần xếp thêm!")
            return True

        self.mouse.reset_stop()
        slots = self.get_slots()

        for idx, action in enumerate(plan.actions, start=1):
            if stop_check and stop_check():
                self.execution_finished.emit(False, "Đã hủy tự động binh bài (User cancelled)")
                return False

            self.action_started.emit(idx, total, action.description)

            # Retrieve slot coordinates (prefer live detected coords on active window frame)
            s_slot = slots.get(action.source_slot)
            d_slot = slots.get(action.target_slot)
            default_s_coords = (s_slot.rel_x, s_slot.rel_y) if s_slot else (0.3, 0.3)
            default_d_coords = (d_slot.rel_x, d_slot.rel_y) if d_slot else (0.7, 0.7)

            if live_slot_coords and action.source_slot in live_slot_coords and action.target_slot in live_slot_coords:
                s_coords = live_slot_coords[action.source_slot]
                d_coords = live_slot_coords[action.target_slot]
            else:
                s_coords = default_s_coords
                d_coords = default_d_coords

            # Select gesture sample (with weighted random & repeat avoidance)
            sample = self.selector.select_gesture(
                source_slot=action.source_slot,
                target_slot=action.target_slot,
                available_samples=self._samples,
                config=cfg,
                source_coords=s_coords,
                target_coords=d_coords,
            )

            # Adapt trajectory waypoints to the exact live card coordinates
            adapted_points = self.adapt_trajectory_to_endpoints(sample.points, s_coords, d_coords)

            # Execute drag trajectory on game window
            success = self.mouse.play_trajectory(
                points=adapted_points,
                mouse_down_delay_ms=sample.mouse_down_delay_ms,
                mouse_up_delay_ms=sample.mouse_up_delay_ms,
                win_bounds=win_bounds,
                speed_factor=cfg.speed_factor,
                stop_check=stop_check,
            )

            if not success:
                self.execution_finished.emit(False, f"Thao tác bị gián đoạn ở bước {idx}/{total}")
                return False

            self.action_completed.emit(idx, total)

            # Inter-move delay to allow game swap animation to settle
            if idx < total:
                time.sleep(cfg.inter_move_delay_ms / 1000.0)

        self.execution_finished.emit(True, f"Đã tự động binh xong 13 lá bài trong {total} lượt kéo!")
        return True


class AutoBinhWorker(QThread):
    """Executes a move plan in background QThread to prevent UI freezing."""

    step_started = Signal(int, int, str)
    step_completed = Signal(int, int)
    finished_result = Signal(bool, str)

    def __init__(
        self,
        manager: GestureManager,
        plan: MovePlan,
        win_bounds: Tuple[int, int, int, int],
        config: Optional[GestureConfig] = None,
        live_slot_coords: Optional[Dict[int, Tuple[float, float]]] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self.plan = plan
        self.win_bounds = win_bounds
        self.config = config
        self.live_slot_coords = live_slot_coords
        self._is_aborted = False

        self.manager.action_started.connect(self.step_started)
        self.manager.action_completed.connect(self.step_completed)
        self.manager.execution_finished.connect(self.finished_result)

    def stop(self) -> None:
        self._is_aborted = True
        self.manager.mouse.request_stop()

    def run(self) -> None:
        try:
            self.manager.execute_move_plan(
                plan=self.plan,
                win_bounds=self.win_bounds,
                config=self.config,
                stop_check=lambda: self._is_aborted,
                live_slot_coords=self.live_slot_coords,
            )
        finally:
            try:
                self.manager.action_started.disconnect(self.step_started)
            except Exception:
                pass
            try:
                self.manager.action_completed.disconnect(self.step_completed)
            except Exception:
                pass
            try:
                self.manager.execution_finished.disconnect(self.finished_result)
            except Exception:
                pass


