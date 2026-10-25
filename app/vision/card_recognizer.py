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
    """Represents a card recognized by Computer Vision with independent rank/suit confidences."""
    card: Optional[Card]
    confidence: float
    bbox: Tuple[int, int, int, int]
    raw_crop: np.ndarray
    rank_confidence: float = 0.0
    suit_confidence: float = 0.0
    overall_confidence: float = 0.0
    rank_crop: Optional[np.ndarray] = None
    suit_crop: Optional[np.ndarray] = None
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
            "rank_confidence": round(self.rank_confidence, 4),
            "suit_confidence": round(self.suit_confidence, 4),
            "overall_confidence": round(self.overall_confidence, 4),
            "confidence": round(self.confidence, 4),
            "bbox": list(self.bbox),
            "is_verified": self.is_verified,
            "is_reference_match": self.is_reference_match,
            "is_uncertain": self.is_uncertain,
            "uncertain_reason": self.uncertain_reason,
            "alternative_candidates": self.alternative_candidates,
            "matched_reference_id": self.matched_reference_id,
        }


class CardRecognizer:
    """Recognizes playing cards from image crops using confirmed reference samples,
    independent rank/suit extraction, algorithmic template matching, and color classification.

    Architecture:
    1. Independent Rank & Suit Extraction: Decouples rank glyph and suit symbol from middle illustration & UI banners.
    2. Confirmed Reference Library: prioritizes user-confirmed reference images of actual game cards.
    3. Multi-scale Normalized Cross-Correlation Template Matching + HSV Color Segmentation.
    4. Multi-source fusion and conflict resolution with uncertainty detection.
    5. ONNX Neural Network Classifier (when `models/card_classifier.onnx` is present).
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
        """Classifies an individual card crop by decoupling Rank and Suit recognition."""
        norm_img = crop.image
        if crop.rank_crop is not None and crop.rank_crop.size > 0:
            rank_crop = crop.rank_crop
        elif crop.corner_crop is not None and crop.corner_crop.size > 0:
            split_y = int(crop.corner_crop.shape[0] * 0.55)
            rank_crop = crop.corner_crop[0:split_y, :]
        else:
            rank_crop = norm_img[8:48, 8:44]

        if crop.suit_crop is not None and crop.suit_crop.size > 0:
            suit_crop = crop.suit_crop
        elif crop.corner_crop is not None and crop.corner_crop.size > 0:
            split_y = int(crop.corner_crop.shape[0] * 0.55)
            suit_crop = crop.corner_crop[split_y:, :]
        else:
            suit_crop = norm_img[46:82, 8:44]

        # 1. Color discrimination: Red vs Black
        is_red = self.reference_library.check_image_is_red(suit_crop) or self.reference_library.check_image_is_red(rank_crop)

        # 2. Extract isolated binary primary glyphs
        q_rank_glyph = self.reference_library.extract_primary_glyph(rank_crop, (24, 36))
        q_suit_glyph = self.reference_library.extract_primary_glyph(suit_crop, (28, 28))

        # 3. Query Confirmed Reference Library
        ref_match = self.reference_library.match_crop(
            crop_image=crop.image,
            corner_crop=crop.corner_crop,
            rank_crop=rank_crop,
            suit_crop=suit_crop,
            min_confidence=0.60,
        )
        ref_rank, ref_rank_score, _ = self.reference_library.match_rank_glyph(q_rank_glyph)
        ref_suit, ref_suit_score, _ = self.reference_library.match_suit_glyph(q_suit_glyph, is_red=is_red)

        # 4. Query Algorithmic Pipeline
        algo_rank, algo_rank_conf = self._template_engine.match_rank(cv2.cvtColor(rank_crop, cv2.COLOR_BGR2GRAY))
        algo_suit, algo_suit_conf = self._template_engine.match_suit(cv2.cvtColor(suit_crop, cv2.COLOR_BGR2GRAY), is_red=is_red)

        # 5. Fuse Rank prediction
        if ref_rank is not None and ref_rank_score >= 0.70:
            final_rank = ref_rank
            final_rank_conf = ref_rank_score
        elif ref_rank is not None and ref_rank == algo_rank:
            final_rank = ref_rank
            final_rank_conf = min(0.99, (ref_rank_score + algo_rank_conf) / 2.0 + 0.10)
        elif ref_rank is not None and ref_rank_score > algo_rank_conf:
            final_rank = ref_rank
            final_rank_conf = ref_rank_score
        else:
            final_rank = algo_rank
            final_rank_conf = algo_rank_conf

        # 6. Fuse Suit prediction
        if ref_suit is not None and ref_suit_score >= 0.70:
            final_suit = ref_suit
            final_suit_conf = ref_suit_score
        elif ref_suit is not None and ref_suit == algo_suit:
            final_suit = ref_suit
            final_suit_conf = min(0.99, (ref_suit_score + algo_suit_conf) / 2.0 + 0.10)
        elif ref_suit is not None and ref_suit_score > algo_suit_conf:
            final_suit = ref_suit
            final_suit_conf = ref_suit_score
        else:
            final_suit = algo_suit
            final_suit_conf = algo_suit_conf

        # 7. Cross-check with Full Reference Match
        is_ref_match = False
        matched_ref_id = None
        alternatives: List[Tuple[str, float]] = []

        if ref_match is not None:
            alternatives = list(ref_match.alternative_candidates)
            if ref_match.is_confident:
                matched_ref_id = ref_match.reference_id
                if ref_match.card is not None and ref_match.card.rank == final_rank and ref_match.card.suit == final_suit:
                    final_rank_conf = min(0.99, max(final_rank_conf, ref_match.rank_score, 0.92))
                    final_suit_conf = min(0.99, max(final_suit_conf, ref_match.suit_score, 0.92))
                    is_ref_match = True
                elif ref_match.score >= 0.86 and ref_match.card is not None:
                    final_rank = ref_match.card.rank
                    final_suit = ref_match.card.suit
                    final_rank_conf = max(final_rank_conf, ref_match.rank_score)
                    final_suit_conf = max(final_suit_conf, ref_match.suit_score)
                    is_ref_match = True

        if not is_ref_match and ref_rank is not None and ref_suit is not None:
            if ref_rank == final_rank and ref_suit == final_suit and ref_rank_score >= 0.78 and ref_suit_score >= 0.78:
                is_ref_match = True

        # 8. Compute overall confidence and uncertainty
        card = Card(final_rank, final_suit) if (final_rank and final_suit) else None
        overall_conf = round(final_rank_conf * 0.50 + final_suit_conf * 0.50, 4)

        is_uncertain = (card is None) or (overall_conf < 0.65) or (final_rank_conf < 0.60) or (final_suit_conf < 0.60)
        uncertain_reason = ""
        if is_uncertain:
            if card is None:
                uncertain_reason = "Không nhận diện được rank hoặc suit"
            elif final_rank_conf < 0.60 and final_suit_conf < 0.60:
                uncertain_reason = f"Độ tin cậy rank ({int(final_rank_conf*100)}%) và suit ({int(final_suit_conf*100)}%) đều thấp"
            elif final_rank_conf < 0.60:
                uncertain_reason = f"Độ tin cậy rank thấp ({int(final_rank_conf*100)}%)"
            elif final_suit_conf < 0.60:
                uncertain_reason = f"Độ tin cậy suit thấp ({int(final_suit_conf*100)}%)"
            else:
                uncertain_reason = f"Độ tin cậy tổng thể thấp ({int(overall_conf*100)}%)"

        return DetectedCard(
            card=card,
            confidence=overall_conf,
            bbox=crop.bbox,
            raw_crop=crop.image,
            rank_confidence=round(final_rank_conf, 4),
            suit_confidence=round(final_suit_conf, 4),
            overall_confidence=overall_conf,
            rank_crop=rank_crop,
            suit_crop=suit_crop,
            is_verified=False,
            is_reference_match=is_ref_match,
            is_uncertain=is_uncertain,
            uncertain_reason=uncertain_reason,
            alternative_candidates=alternatives,
            matched_reference_id=matched_ref_id,
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
