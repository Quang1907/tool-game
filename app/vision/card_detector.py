"""Card Detector module for locating and segmenting card regions."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import cv2
import numpy as np

from app.vision.image_preprocessor import ImagePreprocessor


@dataclass(frozen=True)
class CardCrop:
    """Cropped card image with bounding box coordinates."""
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    image: np.ndarray                # Rectified card patch (100x140)
    corner_crop: np.ndarray          # Top-left rank & suit corner area


class CardDetector:
    """Detects and isolates card crops from table images."""

    def __init__(self, preprocessor: ImagePreprocessor | None = None) -> None:
        self.preprocessor = preprocessor or ImagePreprocessor()

    def detect_cards(self, table_image: np.ndarray) -> List[CardCrop]:
        """Detects playing card patches in table image and extracts normalized crops."""
        bboxes = self.preprocessor.find_card_bounding_boxes(table_image)
        crops: List[CardCrop] = []

        for bbox in bboxes:
            x, y, w, h = bbox
            card_img = table_image[y : y + h, x : x + w]
            rectified = self.preprocessor.rectify_card(card_img)

            # Top-left corner index region (typically contains rank symbol + suit symbol)
            # Roughly top 45% of height and left 35% of width
            corner_h = int(ImagePreprocessor.CARD_TARGET_HEIGHT * 0.45)
            corner_w = int(ImagePreprocessor.CARD_TARGET_WIDTH * 0.35)
            corner_crop = rectified[0:corner_h, 0:corner_w]

            crops.append(CardCrop(bbox=bbox, image=rectified, corner_crop=corner_crop))

        return crops
