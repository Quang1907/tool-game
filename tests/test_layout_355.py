"""Unit and integration tests for Binh 13 (3-5-5 Layout) Analyzer, Missing Card Recovery, and Duplicate Resolution."""

from __future__ import annotations
import numpy as np
import pytest

from app.core.card import Card, Deck, Rank, Suit
from app.vision.card_detector import CardCrop, CardDetection, CardDetector
from app.vision.card_recognizer import CardRecognizer, DetectedCard
from app.vision.layout_analyzer import (
    Layout355Analyzer,
    LayoutRow,
    MissingSlotInfo,
    LayoutVerificationReport,
)
from app.vision.recognition_validator import RecognitionValidator
from app.services.vision_service import recognize_cards_pipeline


def _make_dummy_detected_card(
    rank: Rank,
    suit: Suit,
    bbox: tuple[int, int, int, int],
    confidence: float = 0.90,
    is_uncertain: bool = False,
    alt_candidates: list[tuple[str, float]] | None = None,
) -> DetectedCard:
    x, y, w, h = bbox
    patch = np.zeros((h, w, 3), dtype=np.uint8)
    patch[:, :] = (245, 245, 245)
    r_crop = np.zeros((30, 20, 3), dtype=np.uint8)
    s_crop = np.zeros((20, 20, 3), dtype=np.uint8)

    card = Card(rank, suit)
    return DetectedCard(
        card=card,
        confidence=confidence,
        bbox=bbox,
        raw_crop=patch,
        rank_confidence=confidence,
        suit_confidence=confidence,
        overall_confidence=confidence,
        rank_crop=r_crop,
        suit_crop=s_crop,
        is_uncertain=is_uncertain,
        alternative_candidates=alt_candidates or [],
        detection_confidence=0.95,
        detection_status="CONFIRMED",
        crop_status="VALID_CARD_CROP",
    )


class TestLayout355AnalyzerClusteringAndInference:
    """Verifies row clustering and missing slot coordinate inference for the 3-5-5 layout."""

    def test_cluster_into_3_rows(self):
        """13 cards are clustered cleanly into Chi 1 (3), Chi 2 (5), and Chi 3 (5)."""
        card_w, card_h = 60, 84
        cards = []

        # Row 1 (Chi Đầu: 3 cards, y=50)
        for i, x in enumerate([180, 260, 340]):
            cards.append(_make_dummy_detected_card(Rank.ACE, Suit.SPADES, (x, 50, card_w, card_h)))

        # Row 2 (Chi Giữa: 5 cards, y=160)
        for i, x in enumerate([100, 180, 260, 340, 420]):
            cards.append(_make_dummy_detected_card(Rank.KING, Suit.HEARTS, (x, 160, card_w, card_h)))

        # Row 3 (Chi Cuối: 5 cards, y=270)
        for i, x in enumerate([100, 180, 260, 340, 420]):
            cards.append(_make_dummy_detected_card(Rank.QUEEN, Suit.CLUBS, (x, 270, card_w, card_h)))

        rows = Layout355Analyzer.cluster_into_rows(cards, img_h=400)
        assert len(rows) == 3
        assert len(rows[0].cards) == 3
        assert len(rows[1].cards) == 5
        assert len(rows[2].cards) == 5
        assert rows[0].row_name == "front"
        assert rows[1].row_name == "middle"
        assert rows[2].row_name == "back"

    def test_infer_missing_slot_in_middle_row_internal_gap(self):
        """When Row 2 has 4 cards with an internal gap at index 2, infers exact missing bounding box."""
        card_w, card_h = 60, 84
        cards = []

        # Row 1: 3 cards
        for x in [180, 260, 340]:
            cards.append(_make_dummy_detected_card(Rank.ACE, Suit.SPADES, (x, 50, card_w, card_h)))

        # Row 2: 4 cards with gap where x=260 should be (xs: 100, 180, [gap], 340, 420)
        for x in [100, 180, 340, 420]:
            cards.append(_make_dummy_detected_card(Rank.KING, Suit.HEARTS, (x, 160, card_w, card_h)))

        # Row 3: 5 cards
        for x in [100, 180, 260, 340, 420]:
            cards.append(_make_dummy_detected_card(Rank.QUEEN, Suit.CLUBS, (x, 270, card_w, card_h)))

        table_img = np.zeros((400, 600, 3), dtype=np.uint8)
        missing_slots = Layout355Analyzer.infer_missing_slot_bboxes(table_img, cards)

        assert len(missing_slots) == 1
        miss = missing_slots[0]
        assert miss.row_name == "middle"
        assert miss.row_index == 1
        assert miss.slot_number == 6  # Slot 6 is Chi Giữa position 3 (Slot 4, 5, 6, 7, 8)
        # Expected x is around 260
        assert abs(miss.estimated_bbox[0] - 260) <= 15
        assert abs(miss.estimated_bbox[1] - 160) <= 10

    def test_infer_missing_slot_in_front_row(self):
        """When Row 1 has 2 cards and 1 is missing, infers the missing slot bounding box."""
        card_w, card_h = 60, 84
        cards = []

        # Row 1: 2 cards (xs: 180, 340, missing center card x=260)
        for x in [180, 340]:
            cards.append(_make_dummy_detected_card(Rank.ACE, Suit.SPADES, (x, 50, card_w, card_h)))

        # Row 2: 5 cards
        for x in [100, 180, 260, 340, 420]:
            cards.append(_make_dummy_detected_card(Rank.KING, Suit.HEARTS, (x, 160, card_w, card_h)))

        # Row 3: 5 cards
        for x in [100, 180, 260, 340, 420]:
            cards.append(_make_dummy_detected_card(Rank.QUEEN, Suit.CLUBS, (x, 270, card_w, card_h)))

        table_img = np.zeros((400, 600, 3), dtype=np.uint8)
        missing_slots = Layout355Analyzer.infer_missing_slot_bboxes(table_img, cards)

        assert len(missing_slots) == 1
        miss = missing_slots[0]
        assert miss.row_name == "front"
        assert miss.slot_number == 2
        assert abs(miss.estimated_bbox[0] - 260) <= 15
        assert abs(miss.estimated_bbox[1] - 50) <= 10


class TestLayout355VerificationAndDuplicateResolution:
    """Verifies physical crop validation, candidate validation, and duplicate misreading resolution."""

    def test_candidate_validation_rejects_empty_table_felt(self):
        """When a missing slot bbox points to empty green felt without card paper, verification returns None."""
        table_img = np.zeros((400, 600, 3), dtype=np.uint8)
        table_img[:, :] = (20, 80, 25)  # Dark green felt

        slot_info = MissingSlotInfo(
            slot_number=6,
            row_name="middle",
            row_index=1,
            col_index=3,
            estimated_bbox=(260, 160, 60, 84),
        )

        detector = CardDetector()
        recognizer = CardRecognizer()

        recovered = Layout355Analyzer.verify_and_crop_missing_card(
            table_image=table_img,
            slot_info=slot_info,
            detector=detector,
            recognizer=recognizer,
        )
        # MUST NOT fabricate a fake card on empty felt
        assert recovered is None

    def test_duplicate_cards_resolution_with_alternatives(self):
        """Two cards misread as 7c: the less confident one is disambiguated to its non-conflicting alternative Jc."""
        cards = []
        all_deck = Deck().cards
        # Create 11 unique cards
        for i in range(11):
            cards.append(_make_dummy_detected_card(all_deck[i].rank, all_deck[i].suit, (50 + i * 40, 100, 40, 60)))

        # Card 12: 7c with high confidence
        c12 = _make_dummy_detected_card(Rank.SEVEN, Suit.CLUBS, (490, 100, 40, 60), confidence=0.92)
        # Card 13: also detected as 7c due to misreading, but has alternative Jc (Jack of Clubs)
        c13 = _make_dummy_detected_card(
            Rank.SEVEN,
            Suit.CLUBS,
            (530, 100, 40, 60),
            confidence=0.68,
            alt_candidates=[("7C", 0.68), ("JC", 0.65)],
        )

        cards.extend([c12, c13])

        recognizer = CardRecognizer()
        resolved, disambiguated = Layout355Analyzer.resolve_duplicate_cards(cards, recognizer)

        # All 13 cards must now have unique card_codes
        codes = [c.card_code for c in resolved]
        assert len(codes) == len(set(codes)) == 13
        assert len(disambiguated) == 1
        assert disambiguated[0][0] == "7C"
        assert disambiguated[0][1] == "JC"


class TestComplete355LayoutEndToEnd:
    """Verifies end-to-end recovery of 13 cards arranged in 3-5-5 layout from synthesized game table."""

    def test_recover_13th_card_from_table_image(self):
        """Synthesizes a table where 1 card was initially missed: complete_and_verify_355_layout recovers the card."""
        table = np.zeros((450, 600, 3), dtype=np.uint8)
        table[:, :] = (20, 60, 25)  # Dark green felt

        card_w, card_h = 56, 80
        detector = CardDetector()
        recognizer = CardRecognizer()

        # Render 13 cards in 3-5-5 layout:
        # Chi 1 (y=40): 3 cards (x: 150, 215, 280)
        # Chi 2 (y=125): 5 cards (x: 90, 150, 210, 270, 330)
        # Chi 3 (y=210): 5 cards (x: 90, 150, 210, 270, 330)
        all_coords = []
        for x in (150, 215, 280):
            all_coords.append((x, 40))
        for x in (90, 150, 210, 270, 330):
            all_coords.append((x, 125))
        for x in (90, 150, 210, 270, 330):
            all_coords.append((x, 210))

        deck = Deck().cards[:13]
        for (x, y), c in zip(all_coords, deck):
            table[y : y + card_h, x : x + card_w] = (245, 245, 245)
            # Add simple rank glyph marker
            table[y + 5 : y + 25, x + 5 : x + 20] = (10, 10, 10)

        # Suppose initial detection only had 12 cards (Slot 7 in Middle row was missed)
        initial_12_cards = []
        for i, ((x, y), c) in enumerate(zip(all_coords, deck)):
            if i == 6:  # Skip 7th card (Chi Giữa pos 4)
                continue
            initial_12_cards.append(
                _make_dummy_detected_card(c.rank, c.suit, (x, y, card_w, card_h), confidence=0.88)
            )

        assert len(initial_12_cards) == 12

        completed_cards, report = Layout355Analyzer.complete_and_verify_355_layout(
            table_image=table,
            detected_cards=initial_12_cards,
            raw_detected=None,
            detector=detector,
            recognizer=recognizer,
        )

        # Should recover the missing card!
        assert len(completed_cards) == 13
        assert report.is_complete_13 is True
        assert report.front_count == 3
        assert report.middle_count == 5
        assert report.back_count == 5

        # Verify slots 1..13 ordering
        slot_nums = [c.slot_number for c in completed_cards]
        assert slot_nums == list(range(1, 14))

    def test_recognize_cards_pipeline_with_355_recovery(self):
        """Unified recognize_cards_pipeline produces 13 cards structured in 3-5-5 layout."""
        table = np.zeros((450, 600, 3), dtype=np.uint8)
        table[:, :] = (20, 60, 25)

        card_w, card_h = 56, 80
        all_coords = (
            [(150, 40), (215, 40), (280, 40)]
            + [(90, 125), (150, 125), (210, 125), (270, 125), (330, 125)]
            + [(90, 210), (150, 210), (210, 210), (270, 210), (330, 210)]
        )

        for x, y in all_coords:
            table[y : y + card_h, x : x + card_w] = (245, 245, 245)
            table[y + 5 : y + 25, x + 5 : x + 20] = (10, 10, 10)

        # Run pipeline
        detector = CardDetector()
        recognizer = CardRecognizer()
        crops, _ = detector.detect_card_objects(table)
        assert len(crops) == 13

        # Validation report verifies 3-5-5 compliance
        detected = [
            _make_dummy_detected_card(
                Rank(r), Suit.SPADES, c.bbox
            )
            for r, c in zip(range(2, 15), crops)
        ]
        for idx, d in enumerate(detected[:3], start=1):
            d.slot_number = idx
            d.row_name = "front"
        for idx, d in enumerate(detected[3:8], start=4):
            d.slot_number = idx
            d.row_name = "middle"
        for idx, d in enumerate(detected[8:13], start=9):
            d.slot_number = idx
            d.row_name = "back"

        val_report = RecognitionValidator.validate(detected)
        assert val_report.is_valid is True
        assert val_report.is_layout_355_valid is True
        assert val_report.front_count == 3
        assert val_report.middle_count == 5
        assert val_report.back_count == 5
