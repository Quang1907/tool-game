"""Image preprocessing utilities with dynamic resolution scaling."""

from __future__ import annotations
from typing import List, Tuple
import cv2
import numpy as np


class ImagePreprocessor:
    """Preprocesses table screenshots and extracts individual card candidate patches."""

    CARD_TARGET_WIDTH = 120
    CARD_TARGET_HEIGHT = 168  # 1.4 aspect ratio

    @staticmethod
    def to_gray(image: np.ndarray) -> np.ndarray:
        """Converts BGR or RGB image to Grayscale."""
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def enhance_contrast(gray: np.ndarray) -> np.ndarray:
        """Applies Contrast Limited Adaptive Histogram Equalization (CLAHE)."""
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        return clahe.apply(gray)

    @classmethod
    def find_card_bounding_boxes(
        cls,
        image: np.ndarray,
        min_area_ratio: float = 0.002,   # Minimum 0.2% of total image area
        max_area_ratio: float = 0.35,    # Maximum 35% of total image area
    ) -> List[Tuple[int, int, int, int]]:
        """Finds candidate card bounding boxes (x, y, w, h) dynamically scaled to image size.

        Filters by aspect ratio (standard playing card aspect ratio is ~ 1.2 to 1.8).
        """
        img_h, img_w = image.shape[:2]
        total_pixels = img_h * img_w
        min_area = int(total_pixels * min_area_ratio)
        max_area = int(total_pixels * max_area_ratio)

        gray = cls.to_gray(image)
        enhanced = cls.enhance_contrast(gray)
        blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)

        # Multi-scale edge detection
        edges = cv2.Canny(blurred, 30, 120)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(edges, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates: List[Tuple[int, int, int, int]] = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            aspect = h / float(w) if w > 0 else 0

            # Card aspect ratio usually ranges from 1.15 to 1.85
            if 1.1 <= aspect <= 1.95:
                candidates.append((x, y, w, h))

        # Sort candidate cards top-to-bottom, left-to-right
        candidates.sort(key=lambda b: (b[1] // max(1, img_h // 10), b[0]))
        return candidates

    @classmethod
    def rectify_card(cls, card_crop: np.ndarray) -> np.ndarray:
        """Resizes a card patch to normalized target dimensions (120x168)."""
        return cv2.resize(card_crop, (cls.CARD_TARGET_WIDTH, cls.CARD_TARGET_HEIGHT))
