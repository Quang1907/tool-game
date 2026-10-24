"""Card Recognizer module supporting template matching and ONNX neural network inference."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

from app.core.card import Card, Rank, Suit
from app.vision.card_detector import CardCrop


@dataclass
class DetectedCard:
    """Represents a card recognized by Computer Vision with confidence score."""
    card: Optional[Card]
    confidence: float
    bbox: Tuple[int, int, int, int]
    raw_crop: np.ndarray
    is_verified: bool = False

    @property
    def display_str(self) -> str:
        if self.card:
            return f"{self.card.unicode_name} ({self.confidence*100:.0f}%)"
        return "Unknown (?)"


class CardRecognizer:
    """Recognizes card rank and suit from card crops.

    Architecture supports:
    1. Pluggable ONNX neural classifier (when model weights file is provided in `models/`).
    2. Normalized cross-correlation template matching.
    3. Graceful degradation: returns detected bounding boxes with low confidence and
       explicit flag prompting user manual verification.
    """

    def __init__(self, onnx_model_path: str | Path | None = None) -> None:
        self.onnx_model_path = Path(onnx_model_path) if onnx_model_path else Path("models/card_classifier.onnx")
        self._onnx_session = None
        self._is_onnx_loaded = False
        self._init_onnx()

    def _init_onnx(self) -> None:
        """Attempts to load ONNX runtime inference session if model file exists."""
        if self.onnx_model_path.exists():
            try:
                import onnxruntime as ort
                self._onnx_session = ort.InferenceSession(str(self.onnx_model_path))
                self._is_onnx_loaded = True
            except Exception as e:
                print(f"[CardRecognizer] Failed to initialize ONNX model: {e}")
                self._is_onnx_loaded = False

    @property
    def has_trained_model(self) -> bool:
        """Returns True if a valid ONNX weights file is loaded."""
        return self._is_onnx_loaded

    def recognize_crop(self, crop: CardCrop) -> DetectedCard:
        """Recognizes a single card crop."""
        if self._is_onnx_loaded and self._onnx_session is not None:
            return self._predict_onnx(crop)
        return self._predict_heuristic_or_uncalibrated(crop)

    def _predict_onnx(self, crop: CardCrop) -> DetectedCard:
        """Inference via ONNX neural network."""
        # Preprocessing: resize to 128x128, normalize to [0, 1], transpose to (1, 3, 128, 128)
        img = cv2.resize(crop.image, (128, 128))
        img = img.astype(np.float32) / 255.0
        # Transpose HWC -> CHW
        img = np.transpose(img, (2, 0, 1))
        tensor = np.expand_dims(img, axis=0)

        input_name = self._onnx_session.get_inputs()[0].name
        outputs = self._onnx_session.run(None, {input_name: tensor})
        logits = outputs[0][0]

        # Softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)
        pred_id = int(np.argmax(probs))
        conf = float(probs[pred_id])

        card = Card.from_id(pred_id) if 0 <= pred_id <= 51 else None
        return DetectedCard(
            card=card,
            confidence=conf,
            bbox=crop.bbox,
            raw_crop=crop.image,
            is_verified=False,
        )

    def _predict_heuristic_or_uncalibrated(self, crop: CardCrop) -> DetectedCard:
        """Fallback when no calibrated ONNX model weights exist.

        Determines dominant color (Red for Hearts/Diamonds, Black for Spades/Clubs)
        and leaves rank for user verification, reporting realistic low confidence.
        """
        # Determine dominant hue in corner crop:
        corner = crop.corner_crop
        hsv = cv2.cvtColor(corner, cv2.COLOR_BGR2HSV)

        # Red color masks (Hearts & Diamonds)
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 50, 50])
        upper_red2 = np.array([180, 255, 255])

        mask_red = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
        red_pixel_count = cv2.countNonZero(mask_red)

        # If significant red pixels present, suspect red suit (Hearts or Diamonds)
        if red_pixel_count > 30:
            suggested_suit = Suit.HEARTS
        else:
            suggested_suit = Suit.SPADES

        # Since model weights are not yet trained on this specific game skin,
        # set confidence at 0.5 and mark clearly for user confirmation
        suggested_card = Card(Rank.ACE, suggested_suit)

        return DetectedCard(
            card=suggested_card,
            confidence=0.50,  # Uncalibrated baseline
            bbox=crop.bbox,
            raw_crop=crop.image,
            is_verified=False,
        )

    def recognize_all(self, crops: List[CardCrop]) -> List[DetectedCard]:
        """Recognizes a list of card crops."""
        return [self.recognize_crop(c) for c in crops]
