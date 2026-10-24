"""Image preprocessing and card contour detection utilities."""

from __future__ import annotations
from typing import List, Tuple
import cv2
import numpy as np


class ImagePreprocessor:
    """Preprocesses table screenshots and extracts individual card candidate patches."""

    CARD_TARGET_WIDTH = 100
    CARD_TARGET_HEIGHT = 140

    @staticmethod
    def to_gray(image: np.ndarray) -> np.ndarray:
        """Converts BGR or RGB image to Grayscale."""
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def enhance_contrast(gray: np.ndarray) -> np.ndarray:
        """Applies Contrast Limited Adaptive Histogram Equalization (CLAHE)."""
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    @classmethod
    def find_card_bounding_boxes(
        cls,
        image: np.ndarray,
        min_area: int = 1500,
        max_area: int | None = None,
    ) -> List[Tuple[int, int, int, int]]:
        """Finds candidate card bounding boxes (x, y, w, h) in the image.

        Filters by aspect ratio (standard card is ~ 0.65 - 0.75 w/h or ~ 1.3 - 1.5 h/w).
        """
        gray = cls.to_gray(image)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 30, 150)

        # Dilate edges to close gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(edges, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        img_h, img_w = image.shape[:2]
        if max_area is None:
            max_area = int(img_h * img_w * 0.5)

        candidates: List[Tuple[int, int, int, int]] = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            aspect = h / float(w) if w > 0 else 0

            # Typical card aspect ratio is 1.2 to 1.7
            if 1.1 <= aspect <= 1.9:
                candidates.append((x, y, w, h))

        # Sort candidate cards left-to-right (by x coordinate)
        candidates.sort(key=lambda b: (b[1] // 50, b[0]))
        return candidates

    @classmethod
    def rectify_card(cls, card_crop: np.ndarray) -> np.ndarray:
        """Resizes a card patch to normalized target dimensions (100x140)."""
        return cv2.resize(card_crop, (cls.CARD_TARGET_WIDTH, cls.CARD_TARGET_HEIGHT))
