"""macOS native CoreGraphics Mouse Controller with failsafe safety."""

from __future__ import annotations
import ctypes
from ctypes import util
import math
import time
from typing import Callable, Dict, List, Optional, Tuple

from app.automation.gesture_models import GesturePoint


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


class MouseController:
    """Controls mouse on macOS using native CoreGraphics CGEvents."""

    # CoreGraphics event constants
    kCGEventNull = 0
    kCGEventLeftMouseDown = 1
    kCGEventLeftMouseUp = 2
    kCGEventLeftMouseDragged = 6
    kCGEventMouseMoved = 5
    kCGMouseButtonLeft = 0
    kCGHIDEventTap = 0

    def __init__(self) -> None:
        self._cg = None
        self._app_services = None
        self._init_libraries()
        self._stop_requested = False

    def _init_libraries(self) -> None:
        try:
            cg_lib = util.find_library("CoreGraphics")
            as_lib = util.find_library("ApplicationServices")
            if cg_lib:
                self._cg = ctypes.cdll.LoadLibrary(cg_lib)
                # Define types
                self._cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p
                self._cg.CGEventCreateMouseEvent.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_uint32,
                    CGPoint,
                    ctypes.c_uint32,
                ]
                self._cg.CGEventPost.restype = None
                self._cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]

                # CFRelease
                self._cg.CFRelease.restype = None
                self._cg.CFRelease.argtypes = [ctypes.c_void_p]

            if as_lib:
                self._app_services = ctypes.cdll.LoadLibrary(as_lib)
                self._app_services.AXIsProcessTrusted.restype = ctypes.c_bool
                self._app_services.AXIsProcessTrusted.argtypes = []
        except Exception as e:
            print(f"[MouseController] Failed to initialize CoreGraphics: {e}")

    def is_accessibility_granted(self) -> bool:
        """Checks if process has macOS Accessibility permissions to post events."""
        if self._app_services and hasattr(self._app_services, "AXIsProcessTrusted"):
            try:
                return bool(self._app_services.AXIsProcessTrusted())
            except Exception:
                return True
        return True

    def request_stop(self) -> None:
        """Signals to abort any ongoing playback immediately."""
        self._stop_requested = True

    def reset_stop(self) -> None:
        self._stop_requested = False

    def _post_mouse_event(self, event_type: int, x: float, y: float) -> None:
        """Posts a single native mouse event at screen coordinates (x, y)."""
        if not self._cg:
            return
        # Failsafe: abort if cursor forced to screen corner (0, 0)
        if x <= 1.0 and y <= 1.0:
            self._stop_requested = True
            return

        pos = CGPoint(x=float(x), y=float(y))
        event = self._cg.CGEventCreateMouseEvent(None, event_type, pos, self.kCGMouseButtonLeft)
        if event:
            self._cg.CGEventPost(self.kCGHIDEventTap, event)
            self._cg.CFRelease(event)

    def move_to(self, x: float, y: float) -> None:
        """Moves cursor to screen coordinate (x, y)."""
        self._post_mouse_event(self.kCGEventMouseMoved, x, y)

    def mouse_down(self, x: float, y: float) -> None:
        """Presses left mouse button down at (x, y)."""
        self._post_mouse_event(self.kCGEventLeftMouseDown, x, y)

    def mouse_drag(self, x: float, y: float) -> None:
        """Drags mouse with left button held down at (x, y)."""
        self._post_mouse_event(self.kCGEventLeftMouseDragged, x, y)

    def mouse_up(self, x: float, y: float) -> None:
        """Releases left mouse button at (x, y)."""
        self._post_mouse_event(self.kCGEventLeftMouseUp, x, y)

    def click(self, x: float, y: float, delay_ms: int = 50) -> None:
        """Executes a single click at (x, y)."""
        self.move_to(x, y)
        time.sleep(0.02)
        self.mouse_down(x, y)
        time.sleep(delay_ms / 1000.0)
        self.mouse_up(x, y)

    @staticmethod
    def rel_to_screen(rel_x: float, rel_y: float, win_bounds: Tuple[int, int, int, int]) -> Tuple[float, float]:
        """Converts relative coordinates [0.0, 1.0] to absolute screen coordinates.
        win_bounds: (x, y, width, height)
        """
        wx, wy, ww, wh = win_bounds
        return (wx + rel_x * ww, wy + rel_y * wh)

    @staticmethod
    def screen_to_rel(screen_x: float, screen_y: float, win_bounds: Tuple[int, int, int, int]) -> Tuple[float, float]:
        """Converts absolute screen coordinates to relative [0.0, 1.0]."""
        wx, wy, ww, wh = win_bounds
        if ww <= 0 or wh <= 0:
            return (0.0, 0.0)
        rel_x = max(0.0, min(1.0, (screen_x - wx) / float(ww)))
        rel_y = max(0.0, min(1.0, (screen_y - wy) / float(wh)))
        return (rel_x, rel_y)

    def smooth_move_to(
        self,
        target_x: float,
        target_y: float,
        duration_sec: float = 0.20,
        steps: int = 20,
        stop_check: Optional[Callable[[], bool]] = None,
    ) -> bool:
        """Smoothly moves the cursor from its current position to (target_x, target_y)
        using an ease-in-out curve to simulate natural human arm movement.
        """
        try:
            from PySide6.QtGui import QCursor
            pos = QCursor.pos()
            start_x, start_y = float(pos.x()), float(pos.y())
        except Exception:
            self.move_to(target_x, target_y)
            return True

        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.hypot(dx, dy)
        if dist < 6.0:
            self.move_to(target_x, target_y)
            return True

        actual_steps = max(10, min(30, int(dist / 25.0))) if steps == 20 else steps
        step_delay = max(0.005, duration_sec / float(actual_steps))

        for i in range(1, actual_steps + 1):
            if self._stop_requested or (stop_check and stop_check()):
                return False

            t = i / float(actual_steps)
            ease_t = t * t * (3.0 - 2.0 * t)  # Smooth cubic ease-in-out
            curr_x = start_x + dx * ease_t
            curr_y = start_y + dy * ease_t
            self.move_to(curr_x, curr_y)
            time.sleep(step_delay)

        self.move_to(target_x, target_y)
        return True

    def play_trajectory(
        self,
        points: List[GesturePoint],
        mouse_down_delay_ms: int = 80,
        mouse_up_delay_ms: int = 80,
        win_bounds: Optional[Tuple[int, int, int, int]] = None,
        speed_factor: float = 1.0,
        stop_check: Optional[Callable[[], bool]] = None,
        click_to_select: bool = True,
    ) -> bool:
        """Plays back a complete drag gesture along waypoints.
        If win_bounds is provided, points are scaled from relative [0.0, 1.0] to screen coordinates.
        1. Smoothly moves mouse from current position to first card.
        2. If click_to_select is True, clicks on the card to focus window and select card.
        3. Drags along trajectory waypoints and releases at target.
        """
        if not points:
            return False

        self.reset_stop()
        speed = max(0.2, min(5.0, speed_factor))

        def should_abort() -> bool:
            if self._stop_requested:
                return True
            if stop_check and stop_check():
                return True
            return False

        # Convert waypoints to absolute screen coords
        screen_points: List[Tuple[float, float, int]] = []
        for p in points:
            if win_bounds:
                sx, sy = self.rel_to_screen(p.rel_x, p.rel_y, win_bounds)
            else:
                sx, sy = p.rel_x, p.rel_y
            screen_points.append((sx, sy, p.time_ms))

        first_x, first_y, _ = screen_points[0]
        last_x, last_y, _ = screen_points[-1]

        # 1. Smoothly move cursor from current position to first card position
        if not self.smooth_move_to(first_x, first_y, duration_sec=0.20, stop_check=stop_check):
            return False
        time.sleep(0.04)

        if should_abort():
            return False

        # 2. Click on card to ensure window focus and card selection before dragging
        if click_to_select:
            self.click(first_x, first_y, delay_ms=45)
            time.sleep(0.08 * speed)

        if should_abort():
            return False

        # 3. Press Mouse Down to begin drag
        self.mouse_down(first_x, first_y)
        time.sleep((mouse_down_delay_ms / 1000.0) * speed)

        # 3. Drag along trajectory with accurate timing
        start_time = time.perf_counter()
        for i in range(1, len(screen_points)):
            if should_abort():
                self.mouse_up(screen_points[i - 1][0], screen_points[i - 1][1])
                return False

            curr_x, curr_y, target_offset_ms = screen_points[i]
            target_elapsed_sec = (target_offset_ms / 1000.0) * speed

            # Micro-wait until elapsed time matches
            while (time.perf_counter() - start_time) < target_elapsed_sec:
                time.sleep(0.001)

            self.mouse_drag(curr_x, curr_y)

        # 4. Final hold before releasing
        time.sleep((mouse_up_delay_ms / 1000.0) * speed)

        # 5. Release Mouse Up
        self.mouse_up(last_x, last_y)
        time.sleep(0.02)
        return True
