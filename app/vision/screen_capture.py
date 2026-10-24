"""Screen capture utilities tailored for macOS."""

from __future__ import annotations
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Tuple
import cv2
import numpy as np


class ScreenCapture:
    """Provides screen capture operations on macOS with Retina display awareness."""

    @staticmethod
    def capture_interactive_region() -> np.ndarray | None:
        """Invokes the native macOS interactive screen capture tool (`screencapture -i -r`).

        Allows the user to drag and select a region on their screen.
        Returns the captured image as a BGR numpy array, or None if cancelled.
        """
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # -i: capture screen interactively
            # -r: do not add drop shadow to window capture
            cmd = ["/usr/sbin/screencapture", "-i", "-r", tmp_path]
            res = subprocess.run(cmd, capture_output=True, text=True)

            if res.returncode != 0:
                # Check for permission error
                if "could not create image" in res.stderr.lower():
                    raise PermissionError(
                        "macOS Screen Recording permission is required. "
                        "Please go to System Settings -> Privacy & Security -> Screen Recording "
                        "and grant access."
                    )
                return None

            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                # User pressed Escape to cancel
                return None

            img = cv2.imread(tmp_path, cv2.IMREAD_COLOR)
            return img

        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    @staticmethod
    def load_image_file(file_path: str | Path) -> np.ndarray:
        """Loads an image file (PNG, JPG, WebP) into an OpenCV BGR numpy array."""
        path_str = str(file_path)
        if not os.path.exists(path_str):
            raise FileNotFoundError(f"Image file not found: {file_path}")

        img = cv2.imread(path_str, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Failed to decode image from {file_path}")
        return img

    @staticmethod
    def crop_region(image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """Crops a region (x, y, w, h) from an image."""
        x, y, w, h = bbox
        img_h, img_w = image.shape[:2]
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img_w, x + w)
        y2 = min(img_h, y + h)
        return image[y1:y2, x1:x2].copy()
