"""Card Recognizer using color classification and multi-scale template matching."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

from app.core.card import Card, Rank, Suit
from app.vision.card_detector import CardCrop
from app.vision.template_engine import CardTemplateEngine


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
    """Recognizes playing cards from image crops using color analysis and pattern matching.

    Architecture:
    1. ONNX Neural Network Classifier (when `models/card_classifier.onnx` is present).
    2. Multi-scale Normalized Cross-Correlation Template Matching + HSV Color Segmentation.
    """

    def __init__(self, onnx_model_path: str | Path | None = None) -> None:
        self.onnx_model_path = Path(onnx_model_path) if onnx_model_path else Path("models/card_classifier.onnx")
        self._onnx_session = None
        self._is_onnx_loaded = False
        self._template_engine = CardTemplateEngine()
        self._init_onnx()

    def _init_onnx(self) -> None:
        """Attempts to load ONNX runtime session if model weights exist."""
        if self.onnx_model_path.exists():
            try:
                import onnxruntime as ort
                self._onnx_session = ort.InferenceSession(str(self.onnx_model_path))
                self._is_onnx_loaded = True
            except Exception as e:
                print(f"[CardRecognizer] ONNX model load skipped: {e}")
                self._is_onnx_loaded = False

    @property
    def has_trained_model(self) -> bool:
        """Returns True if a pre-trained ONNX model is loaded."""
        return self._is_onnx_loaded

    def recognize_crop(self, crop: CardCrop) -> DetectedCard:
        """Classifies an individual card crop into a Card(Rank, Suit) with confidence score."""
        if self._is_onnx_loaded and self._onnx_session is not None:
            return self._predict_onnx(crop)
        return self._predict_template(crop)

    def _predict_onnx(self, crop: CardCrop) -> DetectedCard:
        """Inference via ONNX neural network."""
        img = cv2.resize(crop.image, (128, 128))
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        tensor = np.expand_dims(img, axis=0)

        input_name = self._onnx_session.get_inputs()[0].name
        outputs = self._onnx_session.run(None, {input_name: tensor})
        logits = outputs[0][0]

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

    def _predict_template(self, crop: CardCrop) -> DetectedCard:
        """Accurate template matching with HSV color discrimination."""
        corner = crop.corner_crop
        corner_h, corner_w = corner.shape[:2]

        if corner_h < 10 or corner_w < 10:
            return DetectedCard(card=None, confidence=0.0, bbox=crop.bbox, raw_crop=crop.image)

        # 1. Color discrimination: Red vs Black
        # Red in HSV has two hue ranges: [0..12] and [165..180]
        hsv = cv2.cvtColor(corner, cv2.COLOR_BGR2HSV)
        mask_r1 = cv2.inRange(hsv, np.array([0, 45, 45]), np.array([12, 255, 255]))
        mask_r2 = cv2.inRange(hsv, np.array([165, 45, 45]), np.array([180, 255, 255]))
        mask_red = mask_r1 | mask_r2
        red_count = cv2.countNonZero(mask_red)

        is_red = red_count >= 15

        # 2. Divide corner crop into Rank patch (top ~ 55%) and Suit patch (bottom ~ 45%)
        split_y = int(corner_h * 0.55)
        rank_crop_bgr = corner[0:split_y, :]
        suit_crop_bgr = corner[split_y:corner_h, :]

        rank_gray = cv2.cvtColor(rank_crop_bgr, cv2.COLOR_BGR2GRAY)
        suit_gray = cv2.cvtColor(suit_crop_bgr, cv2.COLOR_BGR2GRAY)

        # 3. Match Rank & Suit
        pred_rank, rank_conf = self._template_engine.match_rank(rank_gray)
        pred_suit, suit_conf = self._template_engine.match_suit(suit_gray, is_red=is_red)

        # If suit patch is mostly empty/white, base confidence on rank match
        _, suit_bin = cv2.threshold(suit_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        non_white = cv2.countNonZero(255 - suit_bin) if np.mean(suit_bin) > 127 else cv2.countNonZero(suit_bin)

        if non_white > 10:
            total_conf = max(0.15, min(0.98, (rank_conf * 0.55) + (suit_conf * 0.45)))
        else:
            total_conf = max(0.15, min(0.98, rank_conf * 0.85))

        card = Card(pred_rank, pred_suit)

        return DetectedCard(
            card=card,
            confidence=total_conf,
            bbox=crop.bbox,
            raw_crop=crop.image,
            is_verified=False,
        )

    def recognize_all(self, crops: List[CardCrop]) -> List[DetectedCard]:
        """Recognizes a list of card crops."""
        return [self.recognize_crop(c) for c in crops]
