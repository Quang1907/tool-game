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
    """Represents a card recognized by Computer Vision with independent detection and rank/suit confidences."""
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
    matched_similarity: float = 0.0
    reference_crop: Optional[np.ndarray] = None
    detection_id: str = "card_000"
    polygon: List[Tuple[int, int]] = field(default_factory=list)
    detection_confidence: float = 1.0
    detection_status: str = "CONFIRMED"
    crop_status: str = "VALID_CARD_CROP"
    duplicate_group: str = ""
    rejection_reason: str = ""
    is_overlapping: bool = False
    is_partially_occluded: bool = False
    recognition_status: str = "CONFIRMED"

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
            "detection_id": self.detection_id,
            "card_code": self.card_code,
            "rank": self.rank_char,
            "suit": self.suit_char,
            "detection_confidence": round(self.detection_confidence, 4),
            "rank_confidence": round(self.rank_confidence, 4),
            "suit_confidence": round(self.suit_confidence, 4),
            "overall_confidence": round(self.overall_confidence, 4),
            "confidence": round(self.confidence, 4),
            "detection_status": self.detection_status,
            "recognition_status": self.recognition_status,
            "crop_status": self.crop_status,
            "duplicate_group": self.duplicate_group,
            "rejection_reason": self.rejection_reason,
            "bbox": list(self.bbox),
            "polygon": [list(pt) for pt in self.polygon],
            "is_overlapping": self.is_overlapping,
            "is_partially_occluded": self.is_partially_occluded,
            "is_verified": self.is_verified,
            "is_reference_match": self.is_reference_match,
            "is_uncertain": self.is_uncertain,
            "uncertain_reason": self.uncertain_reason,
            "alternative_candidates": self.alternative_candidates,
            "matched_reference_id": self.matched_reference_id,
            "matched_similarity": round(self.matched_similarity, 4),
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
        if crop.crop_status in (
            "INVALID_CARD_CROP",
            "NON_CARD_OBJECT",
            "MISSING_RANK_REGION",
            "MISSING_SUIT_REGION",
            "INVALID_CARD",
        ):
            reason_text = crop.detection.rejection_reason if (crop.detection and crop.detection.rejection_reason) else crop.crop_status
            return DetectedCard(
                card=None,
                confidence=0.0,
                bbox=crop.bbox,
                raw_crop=crop.image if crop.image is not None else np.zeros((168, 120, 3), dtype=np.uint8),
                detection_confidence=crop.detection.detection_confidence if crop.detection else 0.0,
                detection_status="DETECTION_FAILED",
                crop_status=crop.crop_status,
                rejection_reason=reason_text,
                recognition_status=crop.crop_status,
                uncertain_reason=f"Đối tượng không phải lá bài hợp lệ ({reason_text})",
                is_uncertain=True,
            )

        if crop.image is None or crop.image.size == 0 or crop.bbox[2] < 10 or crop.bbox[3] < 10:
            return DetectedCard(
                card=None,
                confidence=0.0,
                bbox=crop.bbox,
                raw_crop=np.zeros((168, 120, 3), dtype=np.uint8),
                crop_status="INVALID_CARD_CROP",
                recognition_status="CROP_FAILED",
                uncertain_reason="Crop ảnh rỗng hoặc không hợp lệ",
                is_uncertain=True,
            )

        norm_img = crop.image
        has_custom_corner = crop.corner_crop is not None and crop.corner_crop.size > 0

        # Check corner paper whiteness to reject avatars/photos passed directly
        corner_h, corner_w = min(65, norm_img.shape[0]), min(45, norm_img.shape[1])
        c_patch = norm_img[0:corner_h, 0:corner_w]
        hsv_c = cv2.cvtColor(c_patch, cv2.COLOR_BGR2HSV)
        gray_c = cv2.cvtColor(c_patch, cv2.COLOR_BGR2GRAY)
        is_white_c = (hsv_c[:, :, 1] <= 90) & (hsv_c[:, :, 2] >= 130) & (gray_c >= 125)
        c_white_ratio = float(np.mean(is_white_c))

        if c_white_ratio < 0.35 and not has_custom_corner:
            return DetectedCard(
                card=None,
                confidence=0.0,
                bbox=crop.bbox,
                raw_crop=norm_img,
                detection_confidence=crop.detection.detection_confidence if crop.detection else 0.0,
                detection_status="DETECTION_FAILED",
                crop_status="NON_CARD_OBJECT",
                rejection_reason="MISSING_WHITE_CORNER_INDEX",
                recognition_status="NON_CARD_OBJECT",
                uncertain_reason="Vùng góc không có nền trắng lá bài (đối tượng không phải lá bài)",
                is_uncertain=True,
            )

        gray_corner = cv2.cvtColor(norm_img[0:105, 0:50], cv2.COLOR_BGR2GRAY) if (norm_img is not None and norm_img.shape[0] >= 105 and norm_img.shape[1] >= 50) else None
        has_norm_corner = cv2.countNonZero(gray_corner < 240) > 20 if gray_corner is not None else False

        if has_norm_corner:
            d_rank, d_suit = self.reference_library.extract_dynamic_corner_patches(norm_img)
            rank_crop = d_rank if (d_rank is not None and d_rank.size > 0) else norm_img[8:55, 6:46]
            suit_crop = d_suit if (d_suit is not None and d_suit.size > 0) else norm_img[52:95, 6:46]
        elif crop.rank_crop is not None and crop.rank_crop.size > 0 and crop.suit_crop is not None and crop.suit_crop.size > 0:
            rank_crop = crop.rank_crop
            suit_crop = crop.suit_crop
        elif has_custom_corner:
            split_y = int(crop.corner_crop.shape[0] * 0.55)
            rank_crop = crop.corner_crop[0:split_y, :]
            suit_crop = crop.corner_crop[split_y:, :]
        else:
            rank_crop = norm_img[8:55, 6:46] if norm_img is not None else np.zeros((47, 40, 3), dtype=np.uint8)
            suit_crop = norm_img[52:95, 6:46] if norm_img is not None else np.zeros((43, 40, 3), dtype=np.uint8)

        # 1. Color discrimination: Red vs Black
        is_red = self.reference_library.check_image_is_red(suit_crop) or self.reference_library.check_image_is_red(rank_crop)

        # 2. Extract isolated binary primary glyphs
        q_rank_glyph = self.reference_library.extract_primary_glyph(rank_crop, (24, 36))
        q_suit_glyph = self.reference_library.extract_primary_glyph(suit_crop, (28, 28))

        # 3. Independent Rank Recognition (Part B: Decoupled from Suit)
        algo_rank, algo_rank_conf = self._template_engine.match_rank(cv2.cvtColor(rank_crop, cv2.COLOR_BGR2GRAY))
        ref_rank, ref_rank_score, _ = self.reference_library.match_rank_glyph(q_rank_glyph, min_score=0.68)

        final_rank = None
        final_rank_conf = 0.0

        if ref_rank is not None and ref_rank_score >= 0.75:
            final_rank = ref_rank
            final_rank_conf = ref_rank_score
        elif algo_rank is not None and algo_rank_conf >= 0.65:
            final_rank = algo_rank
            final_rank_conf = algo_rank_conf
            if ref_rank == algo_rank and ref_rank_score >= 0.50:
                final_rank_conf = min(0.99, (algo_rank_conf + ref_rank_score) / 2.0 + 0.10)
        elif ref_rank is not None and ref_rank_score >= 0.68:
            final_rank = ref_rank
            final_rank_conf = ref_rank_score
        else:
            final_rank = algo_rank
            final_rank_conf = algo_rank_conf

        # 4. Independent Suit Recognition (Part B: Decoupled from Rank)
        algo_suit, algo_suit_conf = self._template_engine.match_suit(cv2.cvtColor(suit_crop, cv2.COLOR_BGR2GRAY), is_red=is_red)
        ref_suit, ref_suit_score, _ = self.reference_library.match_suit_glyph(q_suit_glyph, is_red=is_red, min_score=0.68)

        final_suit = None
        final_suit_conf = 0.0

        if ref_suit is not None and ref_suit_score >= 0.75:
            final_suit = ref_suit
            final_suit_conf = ref_suit_score
        elif algo_suit is not None and algo_suit_conf >= 0.65:
            final_suit = algo_suit
            final_suit_conf = algo_suit_conf
            if ref_suit == algo_suit and ref_suit_score >= 0.50:
                final_suit_conf = min(0.99, (algo_suit_conf + ref_suit_score) / 2.0 + 0.10)
        elif ref_suit is not None and ref_suit_score >= 0.68:
            final_suit = ref_suit
            final_suit_conf = ref_suit_score
        else:
            final_suit = algo_suit
            final_suit_conf = algo_suit_conf

        # Reject false positive predictions if glyph confidence is very low without reference match
        if (ref_rank is None and algo_rank_conf < 0.38) or (ref_rank is None and ref_suit is None and algo_rank_conf < 0.45 and algo_suit_conf < 0.38):
            final_rank = None
            final_suit = None

        # 5. Full Card Reference Matching & Validation
        ref_match = self.reference_library.match_crop(
            crop_image=crop.image,
            corner_crop=crop.corner_crop,
            rank_crop=rank_crop,
            suit_crop=suit_crop,
            min_confidence=0.68,
        )

        is_ref_match = False
        matched_ref_id = None
        matched_similarity = 0.0
        ref_crop_img = None
        alternatives: List[Tuple[str, float]] = []

        if ref_match is not None:
            alternatives = list(ref_match.alternative_candidates)
            # CRITICAL ARCHITECTURAL CONSTRAINT (Part B, C, G):
            # A reference match is ONLY accepted as ground truth if its rank and suit
            # EXACTLY MATCH the independently recognized rank and suit, with high scores!
            # Under NO CIRCUMSTANCES can a sample of 9D change an image of QD into 9D!
            if (
                ref_match.card is not None
                and ref_match.card.rank == final_rank
                and ref_match.card.suit == final_suit
                and ref_match.rank_score >= 0.70
                and ref_match.suit_score >= 0.70
                and ref_match.score >= 0.70
            ):
                is_ref_match = True
                matched_ref_id = ref_match.reference_id
                matched_similarity = ref_match.score
                ref_crop_img = self.reference_library.get_reference_image(ref_match.reference_id)
                final_rank_conf = max(final_rank_conf, ref_match.rank_score)
                final_suit_conf = max(final_suit_conf, ref_match.suit_score)

        # 6. Compute overall confidence and uncertainty
        card = Card(final_rank, final_suit) if (final_rank and final_suit) else None
        det_conf = crop.detection.detection_confidence if crop.detection else 1.0

        if card is None:
            recog_conf = 0.0
            overall_conf = 0.0
            final_rank_conf = 0.0
            final_suit_conf = 0.0
            is_uncertain = True
            uncertain_reason = "Không nhận diện được rank hoặc suit hợp lệ (không phải lá bài)"
        else:
            recog_conf = round(final_rank_conf * 0.50 + final_suit_conf * 0.50, 4)
            if is_ref_match:
                recog_conf = max(recog_conf, round(matched_similarity, 4))

            overall_conf = round(0.15 * det_conf + 0.85 * recog_conf, 4)

            if crop.crop_status == "LOW_QUALITY_CROP":
                overall_conf = round(overall_conf * 0.85, 4)

            is_uncertain = (
                (overall_conf < 0.65)
                or (final_rank_conf < 0.55)
                or (final_suit_conf < 0.55)
                or (det_conf < 0.65)
            )
            uncertain_reason = ""
            if is_uncertain:
                if det_conf < 0.65:
                    uncertain_reason = f"Độ tin cậy vị trí lá bài thấp ({int(det_conf*100)}%)"
                elif final_rank_conf < 0.55 and final_suit_conf < 0.55:
                    uncertain_reason = f"Độ tin cậy rank ({int(final_rank_conf*100)}%) và suit ({int(final_suit_conf*100)}%) đều thấp"
                elif final_rank_conf < 0.55:
                    uncertain_reason = f"Độ tin cậy rank thấp ({int(final_rank_conf*100)}%)"
                elif final_suit_conf < 0.55:
                    uncertain_reason = f"Độ tin cậy suit thấp ({int(final_suit_conf*100)}%)"
                else:
                    uncertain_reason = f"Độ tin cậy tổng thể thấp ({int(overall_conf*100)}%)"

        has_saved_ref = False
        if card:
            code = f"{card.rank.char}{card.suit.char.upper()}"
            has_saved_ref = len(self.reference_library.get_references_for_card(code)) > 0

        det_id = crop.detection.detection_id if crop.detection else "card_000"
        poly = list(crop.detection.polygon) if (crop.detection and crop.detection.polygon) else []
        is_overlap = crop.detection.is_overlapping if crop.detection else False
        is_occluded = crop.detection.is_partially_occluded if crop.detection else False
        det_status = crop.detection.detection_status if crop.detection else "CONFIRMED"

        # Separate 6 distinct diagnostic statuses (Part D)
        if det_status == "DETECTION_FAILED":
            recog_status = "DETECTION_FAILED"
        elif det_status == "INVALID_CARD_BOUNDS":
            recog_status = "INVALID_CARD_BOUNDS"
        elif card is None:
            recog_status = "RECOGNITION_FAILED"
        elif is_uncertain:
            recog_status = "UNCERTAIN"
        elif has_saved_ref and not is_ref_match:
            recog_status = "REFERENCE_NOT_USED"
            if not uncertain_reason:
                uncertain_reason = f"Ảnh mẫu có trong thư viện ({int(matched_similarity*100)}%) nhưng chưa được sử dụng"
        else:
            recog_status = "CONFIRMED"

        source_crop = crop.raw_patch if (crop.raw_patch is not None and crop.raw_patch.size > 0) else crop.image
        return DetectedCard(
            card=card,
            confidence=overall_conf,
            bbox=crop.bbox,
            raw_crop=source_crop,
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
            matched_similarity=round(matched_similarity, 4),
            reference_crop=ref_crop_img,
            detection_id=det_id,
            polygon=poly,
            detection_confidence=round(det_conf, 4),
            detection_status=det_status,
            crop_status=crop.crop_status,
            duplicate_group=crop.detection.duplicate_group if crop.detection else "",
            rejection_reason=crop.detection.rejection_reason if crop.detection else "",
            is_overlapping=is_overlap,
            is_partially_occluded=is_occluded,
            recognition_status=recog_status,
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
