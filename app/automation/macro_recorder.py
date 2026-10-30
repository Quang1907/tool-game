"""Real-time mouse macro recorder for capturing human drag-and-drop trajectories."""

from __future__ import annotations
import ctypes
from ctypes import util
import datetime
import threading
import time
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QCursor

from app.automation.gesture_models import GesturePoint, GestureSample
from app.automation.mouse_controller import MouseController


class MacroRecorder(QObject):
    """Listens to global mouse events to record drag-and-drop trajectories."""

    recording_started = Signal()
    recording_progress = Signal(int)       # Waypoint count
    recording_finished = Signal(object)    # GestureSample
    recording_cancelled = Signal(str)      # Reason

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._cg = None
        self._init_cg()
        self._is_recording = False
        self._thread: Optional[threading.Thread] = None

    def _init_cg(self) -> None:
        try:
            cg_lib = util.find_library("CoreGraphics")
            if cg_lib:
                self._cg = ctypes.cdll.LoadLibrary(cg_lib)
                self._cg.CGEventSourceButtonState.restype = ctypes.c_bool
                self._cg.CGEventSourceButtonState.argtypes = [ctypes.c_int32, ctypes.c_uint32]
        except Exception as e:
            print(f"[MacroRecorder] CoreGraphics button state init failed: {e}")

    def is_left_button_pressed(self) -> bool:
        """Returns True if the left mouse button is currently held down on macOS."""
        if self._cg and hasattr(self._cg, "CGEventSourceButtonState"):
            try:
                # 0 = kCGEventSourceStateCombinedSessionState, 0 = kCGMouseButtonLeft
                return bool(self._cg.CGEventSourceButtonState(0, 0))
            except Exception:
                return False
        return False

    def start_recording(
        self,
        source_slot: int,
        target_slot: int,
        sample_name: str,
        win_bounds: Tuple[int, int, int, int],
        timeout_seconds: float = 60.0,
        bounds_getter: Optional[Callable[[], Optional[Tuple[int, int, int, int]]]] = None,
    ) -> bool:
        """Starts a background thread to wait for mouse drag and record waypoints.
        If bounds_getter is provided, live window bounds are queried dynamically to support resized or shrunk windows.
        """
        if self._is_recording:
            return False

        self._is_recording = True
        self._thread = threading.Thread(
            target=self._record_loop,
            args=(source_slot, target_slot, sample_name, win_bounds, timeout_seconds, bounds_getter),
            daemon=True,
        )
        self._thread.start()
        return True

    def cancel_recording(self) -> None:
        """Cancels an active recording session."""
        self._is_recording = False

    def _record_loop(
        self,
        source_slot: int,
        target_slot: int,
        sample_name: str,
        win_bounds: Tuple[int, int, int, int],
        timeout_seconds: float,
        bounds_getter: Optional[Callable[[], Optional[Tuple[int, int, int, int]]]] = None,
    ) -> None:
        # Debounce: wait for button to be released if user just clicked a UI button
        debounce_start = time.perf_counter()
        while self._is_recording and self.is_left_button_pressed():
            if time.perf_counter() - debounce_start > 2.0:
                break
            time.sleep(0.02)

        self.recording_started.emit()
        start_wait = time.perf_counter()

        # Phase 1: Wait for left mouse button to go DOWN on the game window
        while self._is_recording:
            if self.is_left_button_pressed():
                cursor_pos = QCursor.pos()
                screen_x = float(cursor_pos.x())
                screen_y = float(cursor_pos.y())

                # Validate if click happened within live game window bounds
                active_bounds = (bounds_getter() if bounds_getter else None) or win_bounds
                win_x, win_y, win_w, win_h = active_bounds
                if win_w > 0 and win_h > 0:
                    in_window = (win_x - 30 <= screen_x <= win_x + win_w + 30 and
                                 win_y - 30 <= screen_y <= win_y + win_h + 30)
                    if not in_window:
                        # Clicked outside game window, wait for release and keep listening
                        while self._is_recording and self.is_left_button_pressed():
                            time.sleep(0.02)
                        continue

                # Mouse is down inside target window -> begin recording trajectory
                break

            if (time.perf_counter() - start_wait) > timeout_seconds:
                self._is_recording = False
                self.recording_cancelled.emit("Hết thời gian chờ nhấn chuột (Timeout)")
                return
            time.sleep(0.015)

        if not self._is_recording:
            self.recording_cancelled.emit("Đã hủy ghi")
            return

        # Phase 2: Mouse button is DOWN. Record waypoints at 60 Hz until button goes UP
        t_start = time.perf_counter()
        raw_points: List[Tuple[float, float, int]] = []

        while self._is_recording and self.is_left_button_pressed():
            elapsed_ms = int((time.perf_counter() - t_start) * 1000)
            cursor_pos = QCursor.pos()
            screen_x = float(cursor_pos.x())
            screen_y = float(cursor_pos.y())

            # Use live window bounds to ensure accurate relative coords on resized/shrunk windows
            active_bounds = (bounds_getter() if bounds_getter else None) or win_bounds
            rel_x, rel_y = MouseController.screen_to_rel(screen_x, screen_y, active_bounds)

            # Avoid recording redundant stationary points
            if not raw_points or (
                abs(rel_x - raw_points[-1][0]) > 0.001 or abs(rel_y - raw_points[-1][1]) > 0.001
            ):
                raw_points.append((rel_x, rel_y, elapsed_ms))
                self.recording_progress.emit(len(raw_points))

            time.sleep(0.016)  # ~60 Hz sampling rate

        self._is_recording = False
        total_duration_ms = int((time.perf_counter() - t_start) * 1000)

        if len(raw_points) < 3 or total_duration_ms < 50:
            self.recording_cancelled.emit("Thao tác quá ngắn hoặc không có chuyển động chuột")
            return

        points = [GesturePoint(rel_x=p[0], rel_y=p[1], time_ms=p[2]) for p in raw_points]
        sample = GestureSample.create_new(
            source_slot=source_slot,
            target_slot=target_slot,
            name=sample_name or f"Macro #{datetime.datetime.now().strftime('%H:%M:%S')}",
            points=points,
            mouse_down_delay_ms=80,
            mouse_up_delay_ms=80,
            total_duration_ms=total_duration_ms,
            is_verified=True,
            weight=1.0,
            metadata={"source": "real_macro_recorder", "points_count": len(points)},
        )

        self.recording_finished.emit(sample)
