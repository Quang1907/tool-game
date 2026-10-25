"""Card Recognizer fusing Reference Library, multi-scale templates, and color classification."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

from app.core.card import Card, Rank, Suit
from app.vision.card_detector import CardCrop
from app.vision.card_reference_library import CardReferenceLibrary, CardReferenceMatch
from app.vision.template_engine import CardTemplateEngine


@dataclass
class DetectedCard:
    """Represents a card recognized by Computer Vision with confidence score."""
    card: Optional[Card]
    confidence: float
    bbox: Tuple[int, int, int, int]
    raw_crop: np.ndarray
    is_verified: bool = False
    is_reference_match: bool = False
    is_uncertain: bool = False
    uncertain_reason: str = ""
    alternative_candidates: List[Tuple[str, float]] = field(default_factory=list)
    matched_reference_id: Optional[str] = None

    @property
    def display_str(self) -> str:
        if self.card:
            tag = f"{self.card.unicode_name} ({self.confidence*100:.0f}%)"
            if self.is_reference_match:
                tag += " [Mẫu]"
            elif self.is_uncertain:
                tag += " [Nghi ngờ]"
            return tag
        return "Unknown (?)"

    @property
    def card_code(self) -> str:
        if self.card:
            return f"{self.card.rank.char}{self.card.suit.char.upper()}"
        return "??"

    @property
    def rank_char(self) -> str:
        return self.card.rank.char if self.card else "?"

    @property
    def suit_char(self) -> str:
        return self.card.suit.char.upper() if self.card else "?"

    def to_dict(self) -> dict:
        return {
            "card_code": self.card_code,
            "rank": self.rank_char,
            "suit": self.suit_char,
            "bbox": list(self.bbox),
            "confidence": round(self.confidence, 4),
            "is_verified": self.is_verified,
            "is_reference_match": self.is_reference_match,
            "is_uncertain": self.is_uncertain,
            "uncertain_reason": self.uncertain_reason,
            "alternative_candidates": self.alternative_candidates,
            "matched_reference_id": self.matched_reference_id,
        }


class CardRecognizer:
    """Recognizes playing cards from image crops using confirmed reference samples,
    algorithmic template matching, and color classification.

    Architecture:
    1. Confirmed Reference Library: prioritizes user-confirmed reference images of actual game cards.
    2. Multi-scale Normalized Cross-Correlation Template Matching + HSV Color Segmentation.
    3. Multi-source fusion and conflict resolution with uncertainty detection.
    4. ONNX Neural Network Classifier (when `models/card_classifier.onnx` is present).
    """

    def __init__(
        self,
        onnx_model_path: str | Path | None = None,
        reference_library: Optional[CardReferenceLibrary] = None,
    ) -> None:
        self.onnx_model_path = Path(onnx_model_path) if onnx_model_path else Path("models/card_classifier.onnx")
        self._onnx_session = None
        self._is_onnx_loaded = False
        self._template_engine = CardTemplateEngine()
        self.reference_library = reference_library or CardReferenceLibrary()
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
        """Classifies an individual card crop by fusing Reference Library with algorithmic analysis."""
        # 1. Query Confirmed Reference Library
        ref_match = self.reference_library.match_crop(
            crop_image=crop.image,
            corner_crop=crop.corner_crop,
            min_confidence=0.60,
        )

        # 2. Query Algorithmic Pipeline (ONNX or Synthetic Template Matching)
        if self._is_onnx_loaded and self._onnx_session is not None:
            algo_card, algo_conf = self._predict_onnx_raw(crop)
        else:
            algo_card, algo_conf = self._predict_template_raw(crop)

        # 3. Multi-source Fusion & Conflict Resolution
        return self._fuse_predictions(crop, ref_match, algo_card, algo_conf)

    def _fuse_predictions(
        self,
        crop: CardCrop,
        ref_match: Optional[CardReferenceMatch],
        algo_card: Optional[Card],
        algo_conf: float,
    ) -> DetectedCard:
        """Combines reference library match and algorithmic prediction safely."""
        # Case A: Strong confident match from Confirmed Reference Library
        if ref_match is not None and ref_match.is_confident:
            if algo_card is not None and algo_card == ref_match.card:
                # Perfect agreement
                total_conf = min(0.99, max(ref_match.score, algo_conf) + 0.05)
                return DetectedCard(
                    card=ref_match.card,
                    confidence=total_conf,
                    bbox=crop.bbox,
                    raw_crop=crop.image,
                    is_verified=False,
                    is_reference_match=True,
                    is_uncertain=False,
                    alternative_candidates=ref_match.alternative_candidates,
                    matched_reference_id=ref_match.reference_id,
                )
            else:
                # Reference library has confirmed real samples from user
                if ref_match.score >= 0.85:
                    total_conf = ref_match.score * 0.95
                    alts = list(ref_match.alternative_candidates)
                    if algo_card:
                        alts.insert(0, (f"{algo_card.rank.char}{algo_card.suit.char.upper()}", round(algo_conf, 3)))
                    return DetectedCard(
                        card=ref_match.card,
                        confidence=total_conf,
                        bbox=crop.bbox,
                        raw_crop=crop.image,
                        is_verified=False,
                        is_reference_match=True,
                        is_uncertain=False,
                        alternative_candidates=alts,
                        matched_reference_id=ref_match.reference_id,
                    )
                else:
                    # Conflicting predictions and neither has overwhelming confidence
                    alts = list(ref_match.alternative_candidates)
                    if algo_card:
                        alts.insert(0, (f"{algo_card.rank.char}{algo_card.suit.char.upper()}", round(algo_conf, 3)))
                    best_card = ref_match.card if ref_match.score >= algo_conf else algo_card
                    return DetectedCard(
                        card=best_card,
                        confidence=max(0.35, min(0.60, max(ref_match.score, algo_conf))),
                        bbox=crop.bbox,
                        raw_crop=crop.image,
                        is_verified=False,
                        is_reference_match=False,
                        is_uncertain=True,
                        uncertain_reason="Mâu thuẫn giữa ảnh mẫu và thuật toán",
                        alternative_candidates=alts,
                        matched_reference_id=ref_match.reference_id,
                    )

        # Case B: Moderate match from Reference Library (0.65 <= score < 0.82)
        if ref_match is not None and ref_match.score >= 0.65:
            if algo_card is not None and algo_card == ref_match.card:
                # Corroborating evidence
                total_conf = min(0.95, (ref_match.score + algo_conf) / 2.0 + 0.10)
                return DetectedCard(
                    card=ref_match.card,
                    confidence=total_conf,
                    bbox=crop.bbox,
                    raw_crop=crop.image,
                    is_verified=False,
                    is_reference_match=True,
                    is_uncertain=False,
                    alternative_candidates=ref_match.alternative_candidates,
                    matched_reference_id=ref_match.reference_id,
                )
            else:
                # Moderate reference differs from algorithmic prediction
                alts = [(ref_match.card_code, ref_match.score)]
                if algo_card:
                    alts.append((f"{algo_card.rank.char}{algo_card.suit.char.upper()}", round(algo_conf, 3)))
                best_card = algo_card if algo_conf > ref_match.score else ref_match.card
                return DetectedCard(
                    card=best_card,
                    confidence=max(0.35, min(0.60, max(ref_match.score, algo_conf))),
                    bbox=crop.bbox,
                    raw_crop=crop.image,
                    is_verified=False,
                    is_reference_match=False,
                    is_uncertain=True,
                    uncertain_reason="Ảnh mẫu và thuật toán cho kết quả khác nhau",
                    alternative_candidates=alts,
                    matched_reference_id=ref_match.reference_id,
                )

        # Case C: No reference samples or weak match -> Rely on Algorithmic Pipeline
        is_uncertain = algo_card is None or algo_conf < 0.65
        reason = "Độ tin cậy nhận diện thấp" if is_uncertain else ""

        return DetectedCard(
            card=algo_card,
            confidence=algo_conf,
            bbox=crop.bbox,
            raw_crop=crop.image,
            is_verified=False,
            is_reference_match=False,
            is_uncertain=is_uncertain,
            uncertain_reason=reason,
            alternative_candidates=[] if ref_match is None else ref_match.alternative_candidates,
            matched_reference_id=None,
        )

    def _predict_template_raw(self, crop: CardCrop) -> Tuple[Optional[Card], float]:
        """Raw template matching with HSV color discrimination returning (Card, confidence)."""
        corner = crop.corner_crop
        corner_h, corner_w = corner.shape[:2]

        if corner_h < 10 or corner_w < 10:
            return None, 0.0

        # 1. Color discrimination: Red vs Black
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
        return card, total_conf

    def _predict_onnx_raw(self, crop: CardCrop) -> Tuple[Optional[Card], float]:
        """Raw ONNX neural network inference returning (Card, confidence)."""
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
        return card, conf

    def recognize_all(self, crops: List[CardCrop]) -> List[DetectedCard]:
        """Recognizes a list of card crops."""
        return [self.recognize_crop(c) for c in crops]
