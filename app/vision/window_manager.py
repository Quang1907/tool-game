"""Window Manager for macOS: Tracks on-screen game windows, bounds, and Z-order occlusion."""

from __future__ import annotations
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class WindowItem:
    """Represents an on-screen macOS application window."""
    window_id: int
    owner_name: str
    title: str
    bounds: Tuple[int, int, int, int]  # (x, y, w, h) in screen points
    layer: int = 0
    is_occluded: bool = False
    occlusion_ratio: float = 0.0

    @property
    def display_label(self) -> str:
        name = self.owner_name or "Window"
        t = f": {self.title}" if self.title else ""
        return f"[{self.window_id}] {name}{t} ({self.bounds[2]}x{self.bounds[3]})"


class WindowManager:
    """Tracks and updates window positions and computes Z-order occlusion on macOS."""

    def __init__(self, helper_path: Optional[str | Path] = None) -> None:
        self.helper_path = (
            Path(helper_path)
            if helper_path
            else Path(__file__).resolve().parent.parent.parent / "build" / "macos_window_helper"
        )

    def list_windows(self) -> List[WindowItem]:
        """Queries on-screen windows via native Swift helper or fallback."""
        ignored_owners = {
            "loginwindow",
            "Spotlight",
            "UserNotificationCenter",
            "Open and Save Panel Service",
            "LocalAuthenticationRemoteServic",
            "Control Center",
            "Notification Center",
            "Dock",
            "SystemUIServer",
            "WindowManager",
        }
        if self.helper_path.exists() and os.access(self.helper_path, os.X_OK):
            try:
                out = subprocess.check_output([str(self.helper_path)], timeout=2.0)
                data = json.loads(out.decode("utf-8"))
                windows: List[WindowItem] = []
                for item in data:
                    owner = item.get("ownerName", "")
                    title = item.get("windowTitle", "")
                    if owner in ignored_owners:
                        continue
                    if not title and owner in ("Safari", "Google Chrome", "QuickTime Player"):
                        # Skip blank sub-windows/helpers without titles
                        continue

                    x = int(item.get("x", 0))
                    y = int(item.get("y", 0))
                    w = int(item.get("width", 0))
                    h = int(item.get("height", 0))
                    windows.append(
                        WindowItem(
                            window_id=item.get("windowId", 0),
                            owner_name=owner,
                            title=title,
                            bounds=(x, y, w, h),
                            layer=item.get("layer", 0),
                        )
                    )
                return windows
            except Exception:
                pass
        return []

    def get_window_bounds(self, window_id: int) -> Optional[Tuple[int, int, int, int]]:
        """Queries the live, real-time bounds (x, y, w, h) of a specific window by its CGWindowID."""
        if not window_id:
            return None
        all_wins = self.list_windows()
        for w in all_wins:
            if w.window_id == window_id:
                return w.bounds
        return None

    def get_window_by_id(self, window_id: int) -> Optional[WindowItem]:
        """Queries the live WindowItem of a specific window by its CGWindowID."""
        if not window_id:
            return None
        all_wins = self.list_windows()
        for w in all_wins:
            if w.window_id == window_id:
                return w
        return None

    def activate_window(self, target: WindowItem | int | str, title: str = "") -> bool:
        """Brings the target application and window to the foreground on macOS using AppleScript.
        target can be a WindowItem, a CGWindowID (int), or an owner application name (str).
        """
        owner_name = ""
        win_title = title
        if isinstance(target, WindowItem):
            owner_name = target.owner_name
            win_title = target.title or title
        elif isinstance(target, int):
            item = self.get_window_by_id(target)
            if item:
                owner_name = item.owner_name
                win_title = item.title or title
        elif isinstance(target, str):
            owner_name = target

        if not owner_name:
            return False

        clean_owner = owner_name.replace('"', '\\"')
        clean_title = (win_title[:40] if win_title else "").replace('"', '\\"').strip()

        if clean_title:
            script = f'''
            tell application "{clean_owner}" to activate
            tell application "System Events"
                tell process "{clean_owner}"
                    set frontmost to true
                    try
                        perform action "AXRaise" of (first window whose name contains "{clean_title}")
                    end try
                end tell
            end tell
            '''
        else:
            script = f'''
            tell application "{clean_owner}" to activate
            tell application "System Events"
                tell process "{clean_owner}"
                    set frontmost to true
                end tell
            end tell
            '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=1.5)
            return res.returncode == 0
        except Exception:
            try:
                fallback = f'tell application "{clean_owner}" to activate'
                res = subprocess.run(["osascript", "-e", fallback], capture_output=True, timeout=1.0)
                return res.returncode == 0
            except Exception:
                return False

    def compute_occlusion(self, target_window: WindowItem, all_windows: List[WindowItem]) -> WindowItem:
        """Calculates if target_window is occluded by higher Z-order windows."""
        tx, ty, tw, th = target_window.bounds
        target_area = float(tw * th)
        if target_area <= 0:
            target_window.is_occluded = True
            target_window.occlusion_ratio = 1.0
            return target_window

        # Check if target window exists in window list
        found_target = any(win.window_id == target_window.window_id for win in all_windows)
        if not found_target:
            target_window.is_occluded = False
            target_window.occlusion_ratio = 0.0
            return target_window

        occluded_area = 0.0
        # In CGWindowList order, windows earlier in the list are in front of windows later
        for win in all_windows:
            if win.window_id == target_window.window_id:
                break

            # Binh 13 Analyzer app itself must not block game analysis
            if "Binh 13 Analyzer" in win.title or win.owner_name in ("Python", "Binh13Analyzer"):
                continue

            wx, wy, ww, wh = win.bounds
            ix1 = max(tx, wx)
            iy1 = max(ty, wy)
            ix2 = min(tx + tw, wx + ww)
            iy2 = min(ty + th, wy + wh)

            iw = max(0, ix2 - ix1)
            ih = max(0, iy2 - iy1)
            overlap = float(iw * ih)
            occluded_area += overlap

        ratio = min(1.0, occluded_area / target_area)
        target_window.occlusion_ratio = round(ratio, 3)
        target_window.is_occluded = ratio > 0.05
        return target_window
