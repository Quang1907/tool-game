"""Screen capture utilities tailored for macOS with multi-monitor, window, and Retina support."""

from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np


@dataclass(frozen=True)
class ScreenInfo:
    """Metadata describing an available display monitor."""
    index: int                  # 1-based display index for macOS `screencapture -D`
    name: str                   # Human-readable display name
    width: int                  # Physical or logical width
    height: int                 # Physical or logical height
    is_primary: bool            # True if main display


class ScreenCapture:
    """macOS screen capture engine supporting window, full-screen, multi-monitor, and drag region capture."""

    @staticmethod
    def get_available_screens() -> List[ScreenInfo]:
        """Enumerates all connected monitors on macOS."""
        screens: List[ScreenInfo] = []

        try:
            from PySide6.QtGui import QGuiApplication
            q_screens = QGuiApplication.screens()
            if q_screens:
                for idx, s in enumerate(q_screens, start=1):
                    geom = s.geometry()
                    name = s.name() or f"Màn hình {idx}"
                    is_main = (idx == 1)
                    screens.append(ScreenInfo(
                        index=idx,
                        name=name,
                        width=geom.width(),
                        height=geom.height(),
                        is_primary=is_main,
                    ))
                return screens
        except Exception:
            pass

        # Fallback if Qt application not yet initialized: assume at least Display 1
        screens.append(ScreenInfo(index=1, name="Màn hình chính (Display 1)", width=1920, height=1080, is_primary=True))
        return screens

    @staticmethod
    def _verify_capture_result(tmp_path: str, stderr_text: str) -> np.ndarray | None:
        """Verifies screencapture output, checks for macOS permission blocks and black screens."""
        if "could not create image" in stderr_text.lower() or "not permitted" in stderr_text.lower():
            raise PermissionError(
                "macOS chặn quyền Screen Recording (Ghi màn hình).\n\n"
                "Cách mở quyền:\n"
                "1. Mở 'System Settings' (Cài đặt hệ thống).\n"
                "2. Vào mục 'Privacy & Security' (Quyền riêng tư & Bảo mật) -> 'Screen Recording' (Ghi màn hình).\n"
                "3. Bật công tắc cho ứng dụng Binh13Analyzer hoặc Terminal / IDE đang chạy."
            )

        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            # User cancelled interactive capture via ESC key
            return None

        img = cv2.imread(tmp_path, cv2.IMREAD_COLOR)
        if img is None:
            return None

        # Check for black screen (typical symptom when macOS denies screen recording silently)
        if img.size > 0 and np.max(img) == 0 and img.shape[0] > 100 and img.shape[1] > 100:
            raise PermissionError(
                "Ảnh chụp hoàn toàn màu đen do macOS chưa cấp quyền Screen Recording.\n"
                "Vui lòng vào System Settings -> Privacy & Security -> Screen Recording để cấp quyền."
            )

        return img

    @classmethod
    def capture_interactive_region(cls) -> np.ndarray | None:
        """Captures an arbitrary rectangular region by dragging the mouse across ANY screen."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # -i: interactive
            # -s: selection mode (mouse drag crosshair)
            # -r: do not add drop shadow
            # -x: silent (no shutter sound)
            cmd = ["/usr/sbin/screencapture", "-i", "-s", "-r", "-x", tmp_path]
            res = subprocess.run(cmd, capture_output=True, text=True)
            return cls._verify_capture_result(tmp_path, res.stderr)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    @classmethod
    def capture_window(cls) -> np.ndarray | None:
        """Captures a specific application window (Chrome, Safari, Game, etc.) when clicked."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # -i: interactive
            # -w: window selection mode (camera cursor, user clicks any window)
            # -o: exclude window drop shadow
            # -x: silent
            cmd = ["/usr/sbin/screencapture", "-i", "-w", "-o", "-x", tmp_path]
            res = subprocess.run(cmd, capture_output=True, text=True)
            return cls._verify_capture_result(tmp_path, res.stderr)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    @classmethod
    def capture_window_by_id(cls, window_id: int) -> np.ndarray | None:
        """Captures a specific window directly by its macOS CGWindowID without user interaction.
        Captures the exact window content directly from the window server even if another window
        is in front of it on screen.
        """
        if window_id <= 0:
            return None

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # -l <window_id>: window-specific capture
            # -o: exclude window drop shadow
            # -x: silent (mute shutter sound)
            cmd = ["/usr/sbin/screencapture", f"-l{window_id}", "-o", "-x", tmp_path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3.0)
            return cls._verify_capture_result(tmp_path, res.stderr)
        except Exception:
            return None
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    @classmethod
    def capture_full_screen(cls, display_index: int = 1) -> np.ndarray | None:
        """Captures an entire display (Display 1, Display 2, etc.) without user interaction."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # -x: silent
            # -D <n>: capture specific display number
            cmd = ["/usr/sbin/screencapture", "-x", f"-D{display_index}", tmp_path]
            res = subprocess.run(cmd, capture_output=True, text=True)
            return cls._verify_capture_result(tmp_path, res.stderr)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    @staticmethod
    def load_image_file(file_path: str | Path) -> np.ndarray:
        """Loads an image file (PNG, JPG, JPEG, WebP, BMP) into a BGR numpy array."""
        path_str = str(file_path)
        if not os.path.exists(path_str):
            raise FileNotFoundError(f"Không tìm thấy file ảnh: {file_path}")

        img = cv2.imread(path_str, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Không thể giải mã định dạng ảnh từ file: {file_path}")
        return img

    @staticmethod
    def crop_region(image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """Crops a region (x, y, w, h) from an image safely within image bounds."""
        x, y, w, h = bbox
        img_h, img_w = image.shape[:2]
        x1 = max(0, min(img_w, x))
        y1 = max(0, min(img_h, y))
        x2 = max(x1, min(img_w, x + w))
        y2 = max(y1, min(img_h, y + h))
        return image[y1:y2, x1:x2].copy()
