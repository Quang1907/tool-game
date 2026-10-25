"""Card Detector supporting contour extraction and horizontal/grid hand slicing."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import cv2
import numpy as np

from app.vision.image_preprocessor import ImagePreprocessor


@dataclass(frozen=True)
class CardCrop:
    """Cropped card image with bounding box coordinates and dedicated rank/suit crops."""
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    image: np.ndarray                # Rectified card patch (120x168)
    corner_crop: np.ndarray          # Top-left rank & suit corner area
    rank_crop: Optional[np.ndarray] = None  # Dedicated crop of Rank glyph (~36x40)
    suit_crop: Optional[np.ndarray] = None  # Dedicated crop of Suit symbol (~36x36)


class CardDetector:
    """Detects and isolates individual playing card crops from table images."""

    def __init__(self, preprocessor: ImagePreprocessor | None = None) -> None:
        self.preprocessor = preprocessor or ImagePreprocessor()

    def detect_cards(self, table_image: np.ndarray) -> List[CardCrop]:
        """Detects playing card patches in table image.

        If contour detection finds fewer than 10 cards and the image aspect ratio
        indicates a horizontal hand bar (w > 2.5 * h), automatically applies
        intelligent 13-card strip slicing.
        """
        img_h, img_w = table_image.shape[:2]
        bboxes = self.preprocessor.find_card_bounding_boxes(table_image)

        # If contour detection found at least 10 cards, use them
        if len(bboxes) >= 10:
            return self._build_card_crops(table_image, bboxes)

        # If user cropped a horizontal strip of cards (e.g. 13 cards side-by-side)
        aspect = img_w / float(img_h) if img_h > 0 else 1.0
        if aspect >= 2.2:
            # Automatic 13-card horizontal partition
            slice_bboxes = self.slice_horizontal_row(table_image, card_count=13)
            return self._build_card_crops(table_image, slice_bboxes)

        # Default to whatever bboxes were detected
        return self._build_card_crops(table_image, bboxes)

    @staticmethod
    def slice_horizontal_row(
        table_image: np.ndarray, card_count: int = 13
    ) -> List[Tuple[int, int, int, int]]:
        """Slices a horizontal strip of overlapping cards into equal card slots."""
        img_h, img_w = table_image.shape[:2]
        bboxes: List[Tuple[int, int, int, int]] = []

        step_x = img_w / float(card_count)
        card_w = min(img_w, int(step_x * 1.6))
        card_h = img_h

        for i in range(card_count):
            x = int(i * step_x)
            w = min(card_w, img_w - x)
            bboxes.append((x, 0, w, card_h))

        return bboxes

    @staticmethod
    def slice_three_rows_grid(
        table_image: np.ndarray,
        front_count: int = 3,
        middle_count: int = 5,
        back_count: int = 5,
    ) -> List[Tuple[int, int, int, int]]:
        """Slices an image containing 3 hand rows (Chi Đầu, Chi Giữa, Chi Cuối)."""
        img_h, img_w = table_image.shape[:2]
        row_h = img_h // 3
        bboxes: List[Tuple[int, int, int, int]] = []

        # Row 1: Front hand (3 cards)
        step_f = img_w / float(front_count)
        for i in range(front_count):
            bboxes.append((int(i * step_f), 0, int(step_f), row_h))

        # Row 2: Middle hand (5 cards)
        step_m = img_w / float(middle_count)
        for i in range(middle_count):
            bboxes.append((int(i * step_m), row_h, int(step_m), row_h))

        # Row 3: Back hand (5 cards)
        step_b = img_w / float(back_count)
        for i in range(back_count):
            bboxes.append((int(i * step_b), row_h * 2, int(step_b), img_h - row_h * 2))

        return bboxes

    def _build_card_crops(
        self, table_image: np.ndarray, bboxes: List[Tuple[int, int, int, int]]
    ) -> List[CardCrop]:
        """Constructs normalized CardCrop objects from bounding box rectangles."""
        crops: List[CardCrop] = []

        for bbox in bboxes:
            x, y, w, h = bbox
            if w < 10 or h < 10:
                continue

            card_img = table_image[y : y + h, x : x + w]
            rectified = self.preprocessor.rectify_card(card_img)

            # Top-left corner index region (rank + suit glyphs)
            corner_h = int(ImagePreprocessor.CARD_TARGET_HEIGHT * 0.50)
            corner_w = int(ImagePreprocessor.CARD_TARGET_WIDTH * 0.42)
            corner_crop = rectified[0:corner_h, 0:corner_w]

            # Separate dedicated crops for Rank and Suit
            rank_crop = rectified[8:48, 8:44]
            suit_crop = rectified[46:82, 8:44]

            crops.append(
                CardCrop(
                    bbox=bbox,
                    image=rectified,
                    corner_crop=corner_crop,
                    rank_crop=rank_crop,
                    suit_crop=suit_crop,
                )
            )

        return crops
