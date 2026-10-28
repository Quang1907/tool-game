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
