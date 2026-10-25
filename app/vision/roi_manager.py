"""ROI Manager: Extracts individual game window ROIs from a common full-screen capture frame."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np


@dataclass
class WindowROI:
    """Defines the search region for an individual game window."""
    window_id: int
    name: str
    bounds_pts: Tuple[int, int, int, int]  # (x, y, w, h) in macOS screen points
    titlebar_inset_pts: int = 28           # Inset to exclude window titlebar
    is_active: bool = True
    is_occluded: bool = False
    occlusion_ratio: float = 0.0


class ROIManager:
    """Manages cropping multiple window ROIs from a single screen capture frame with Retina scaling."""

    def __init__(self, retina_scale: float = 2.0) -> None:
        self.retina_scale = retina_scale

    def crop_window_roi(
        self, full_frame: np.ndarray, roi: WindowROI
    ) -> Optional[np.ndarray]:
        """Crops an individual window ROI from the common frame, scaling points to pixels."""
        if full_frame is None or full_frame.size == 0 or not roi.is_active:
            return None

        img_h, img_w = full_frame.shape[:2]
        x_pts, y_pts, w_pts, h_pts = roi.bounds_pts

        # Apply macOS titlebar inset so we capture only the content/game area
        content_y_pts = y_pts + roi.titlebar_inset_pts
        content_h_pts = max(10, h_pts - roi.titlebar_inset_pts)

        # Scale from screen points to Retina pixels
        px = int(round(x_pts * self.retina_scale))
        py = int(round(content_y_pts * self.retina_scale))
        pw = int(round(w_pts * self.retina_scale))
        ph = int(round(content_h_pts * self.retina_scale))

        # Boundary clamping
        clamped_x = max(0, min(px, img_w - 1))
        clamped_y = max(0, min(py, img_h - 1))
        clamped_w = max(1, min(pw, img_w - clamped_x))
        clamped_h = max(1, min(ph, img_h - clamped_y))

        crop = full_frame[clamped_y : clamped_y + clamped_h, clamped_x : clamped_x + clamped_w]
        return crop if crop.size > 0 else None

    def crop_all_rois(
        self, full_frame: np.ndarray, rois: List[WindowROI]
    ) -> Dict[int, Optional[np.ndarray]]:
        """Extracts all window crops from a single capture frame."""
        results: Dict[int, Optional[np.ndarray]] = {}
        for roi in rois:
            results[roi.window_id] = self.crop_window_roi(full_frame, roi)
        return results
