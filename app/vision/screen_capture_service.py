"""Screen Capture Service: Captures a single full-screen frame with Retina scaling support."""

from __future__ import annotations
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np
from app.vision.screen_capture import ScreenCapture


class ScreenCaptureService:
    """Provides high-performance single-frame whole-screen capture for multi-window analysis."""

    def __init__(self, display_index: int = 1) -> None:
        self.display_index = display_index
        self._retina_scale: float = 2.0  # Typical Retina scale factor on modern MacBooks

    def capture_frame(self) -> Tuple[Optional[np.ndarray], float]:
        """Captures a single full-screen frame and returns (image_bgr, scale_factor).

        Only 1 frame is captured per processing cycle, which is then cropped into 3 ROIs.
        """
        # Try native ScreenCapture first
        try:
            img = ScreenCapture.capture_full_screen(display_index=self.display_index)
            if img is not None:
                # Detect scale factor from pixel resolution vs standard point resolution
                screens = ScreenCapture.get_available_screens()
                if screens:
                    pt_w = screens[0].width
                    if pt_w > 0:
                        self._retina_scale = max(1.0, round(img.shape[1] / float(pt_w), 1))
                return img, self._retina_scale
        except Exception:
            pass

        # Fallback to screencapture utility
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            cmd = ["screencapture", "-x", "-C", str(tmp_path)]
            subprocess.run(cmd, check=True, timeout=3.0)
            img = cv2.imread(str(tmp_path))
            return img, self._retina_scale
        except Exception:
            return None, self._retina_scale
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
