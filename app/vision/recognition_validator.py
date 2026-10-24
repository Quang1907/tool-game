"""Validation and consistency checker for card recognition results."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Sequence

from app.core.card import Card
from app.vision.card_recognizer import DetectedCard


@dataclass(frozen=True)
class ValidationReport:
    """Summary of card recognition validation."""
    is_valid: bool
    card_count: int
    missing_count: int
    duplicates: List[Card]
    unrecognized_count: int
    low_confidence_indices: List[int]
    message: str


class RecognitionValidator:
    """Validates the output of Computer Vision recognition before passing to the solver."""

    REQUIRED_CARD_COUNT: int = 13
    LOW_CONFIDENCE_THRESHOLD: float = 0.70

    @classmethod
    def validate(cls, detected_cards: Sequence[DetectedCard]) -> ValidationReport:
        """Performs comprehensive checks on recognized cards."""
        card_count = len(detected_cards)
        unrecognized = [i for i, d in enumerate(detected_cards) if d.card is None]
        low_conf = [
            i for i, d in enumerate(detected_cards)
            if d.card is not None and d.confidence < cls.LOW_CONFIDENCE_THRESHOLD
        ]

        # Extract non-None cards
        valid_cards = [d.card for d in detected_cards if d.card is not None]

        # Check duplicates
        seen: set[int] = set()
        duplicates: List[Card] = []
        for c in valid_cards:
            if c.card_id in seen:
                if c not in duplicates:
                    duplicates.append(c)
            seen.add(c.card_id)

        # Build diagnostic message
        errors = []
        if card_count != cls.REQUIRED_CARD_COUNT:
            errors.append(f"Cần đúng 13 lá bài, hiện tại có {card_count} lá.")

        if unrecognized:
            errors.append(f"Có {len(unrecognized)} lá chưa nhận diện được.")

        if duplicates:
            dup_names = ", ".join(c.unicode_name for c in duplicates)
            errors.append(f"Phát hiện bài bị trùng: {dup_names}.")

        is_valid = (
            card_count == cls.REQUIRED_CARD_COUNT
            and len(unrecognized) == 0
            and len(duplicates) == 0
        )

        if is_valid:
            if low_conf:
                message = f"Đủ 13 lá hợp lệ (có {len(low_conf)} lá độ tin cậy thấp cần kiểm tra)."
            else:
                message = "Đủ 13 lá bài hợp lệ, sẵn sàng phân tích!"
        else:
            message = " ".join(errors)

        return ValidationReport(
            is_valid=is_valid,
            card_count=card_count,
            missing_count=max(0, cls.REQUIRED_CARD_COUNT - card_count),
            duplicates=duplicates,
            unrecognized_count=len(unrecognized),
            low_confidence_indices=low_conf,
            message=message,
        )
