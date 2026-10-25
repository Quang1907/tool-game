"""Unit tests for Computer Vision, Template Matching, Screen Capture, and Recognition Validation."""

from pathlib import Path
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.core.card import Card, Rank, Suit
from app.vision.card_detector import CardCrop, CardDetector
from app.vision.card_recognizer import CardRecognizer, DetectedCard
from app.vision.image_preprocessor import ImagePreprocessor
from app.vision.recognition_validator import RecognitionValidator
from app.vision.screen_capture import ScreenCapture
from app.vision.template_engine import CardTemplateEngine


class TestImagePreprocessor:
    def test_to_gray_and_rectify(self):
        # 3-channel synthetic image (200x200 BGR)
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        img[50:150, 50:150] = (255, 255, 255)  # White box

        gray = ImagePreprocessor.to_gray(img)
        assert len(gray.shape) == 2
        assert gray.shape == (200, 200)

        rectified = ImagePreprocessor.rectify_card(img[50:150, 50:150])
        assert rectified.shape == (
            ImagePreprocessor.CARD_TARGET_HEIGHT,
            ImagePreprocessor.CARD_TARGET_WIDTH,
            3,
        )


class TestCardTemplateEngine:
    def test_rank_and_suit_template_generation(self):
        engine = CardTemplateEngine()
        assert len(engine._rank_templates) == 13
        assert len(engine._suit_templates) == 4

        # Render synthetic 'A' glyph and test matching
        img_a = Image.new("L", (30, 40), 255)  # White bg
        draw = ImageDraw.Draw(img_a)
        draw.text((5, 5), "A", fill=0)          # Black text
        patch_a = np.array(img_a, dtype=np.uint8)

        rank_match, conf = engine.match_rank(patch_a)
        assert rank_match == Rank.ACE
        assert conf > 0.60

    def test_suit_color_discrimination(self):
        engine = CardTemplateEngine()
        # Test Red suit matching with diamond geometry
        diamond_patch = np.zeros((30, 30), dtype=np.uint8)
        pts = np.array([[15, 3], [27, 15], [15, 27], [3, 15]], dtype=np.int32)
        import cv2
        cv2.fillConvexPoly(diamond_patch, pts, 255)

        suit_match, conf = engine.match_suit(diamond_patch, is_red=True)
        assert suit_match in (Suit.DIAMONDS, Suit.HEARTS)
        assert conf > 0.50


class TestCardDetectorSlicing:
    def test_slice_horizontal_13_cards(self):
        img = np.zeros((150, 1300, 3), dtype=np.uint8)  # Wide 13-card bar
        detector = CardDetector()
        crops = detector.detect_cards(img)
        assert len(crops) == 13
        for idx, crop in enumerate(crops):
            assert crop.image.shape == (
                ImagePreprocessor.CARD_TARGET_HEIGHT,
                ImagePreprocessor.CARD_TARGET_WIDTH,
                3,
            )

    def test_slice_three_rows_grid(self):
        img = np.zeros((300, 500, 3), dtype=np.uint8)
        bboxes = CardDetector.slice_three_rows_grid(img)
        assert len(bboxes) == 13  # 3 + 5 + 5 = 13


class TestScreenCaptureMultiMonitor:
    def test_screen_enumeration_and_crop(self):
        screens = ScreenCapture.get_available_screens()
        assert len(screens) >= 1
        assert screens[0].index == 1

        # Test safe cropping within bounds
        dummy_img = np.zeros((500, 800, 3), dtype=np.uint8)
        crop = ScreenCapture.crop_region(dummy_img, (50, 50, 200, 150))
        assert crop.shape == (150, 200, 3)

        # Test out of bounds clamping
        crop_clamped = ScreenCapture.crop_region(dummy_img, (-20, -30, 200, 150))
        assert crop_clamped.shape[0] <= 150
        assert crop_clamped.shape[1] <= 200


class TestCardRecognizer:
    def test_recognizer_template_matching(self):
        recognizer = CardRecognizer()
        assert recognizer.has_trained_model is False

        # Create a synthetic card patch: White card with black top-left 'A'
        card_img = np.ones((ImagePreprocessor.CARD_TARGET_HEIGHT, ImagePreprocessor.CARD_TARGET_WIDTH, 3), dtype=np.uint8) * 255
        corner_h = int(ImagePreprocessor.CARD_TARGET_HEIGHT * 0.50)
        corner_w = int(ImagePreprocessor.CARD_TARGET_WIDTH * 0.42)
        corner = card_img[0:corner_h, 0:corner_w].copy()

        # Draw black 'A' in rank area
        pil_corner = Image.fromarray(corner)
        draw = ImageDraw.Draw(pil_corner)
        draw.text((4, 2), "A", fill=(0, 0, 0))
        corner_with_glyph = np.array(pil_corner)

        crop = CardCrop(
            bbox=(0, 0, 120, 168),
            image=card_img,
            corner_crop=corner_with_glyph,
        )

        detected = recognizer.recognize_crop(crop)
        assert detected.card is not None
        assert detected.card.rank == Rank.ACE
        assert detected.confidence > 0.40


class TestRecognitionValidator:
    def test_validation_success_with_13_unique_cards(self):
        detected_cards = [
            DetectedCard(
                card=Card.from_id(i),
                confidence=0.95,
                bbox=(i * 10, 0, 100, 140),
                raw_crop=np.zeros((140, 100, 3), dtype=np.uint8),
            )
            for i in range(13)
        ]

        report = RecognitionValidator.validate(detected_cards)
        assert report.is_valid is True
        assert report.card_count == 13
        assert len(report.duplicates) == 0
        assert report.unrecognized_count == 0

    def test_validation_failure_on_duplicate(self):
        detected_cards = [
            DetectedCard(
                card=Card.from_id(i % 12),  # Card 0 will appear twice!
                confidence=0.95,
                bbox=(i * 10, 0, 100, 140),
                raw_crop=np.zeros((140, 100, 3), dtype=np.uint8),
            )
            for i in range(13)
        ]

        report = RecognitionValidator.validate(detected_cards)
        assert report.is_valid is False
        assert len(report.duplicates) > 0
        assert "trùng" in report.message

    def test_validation_failure_on_missing_cards(self):
        detected_cards = [
            DetectedCard(
                card=Card.from_id(i),
                confidence=0.95,
                bbox=(i * 10, 0, 100, 140),
                raw_crop=np.zeros((140, 100, 3), dtype=np.uint8),
            )
            for i in range(11)  # Only 11 cards
        ]

        report = RecognitionValidator.validate(detected_cards)
        assert report.is_valid is False
        assert report.card_count == 11
        assert report.missing_count == 2
        assert "13 lá" in report.message


class TestCardReferenceLibrary:
    """Unit tests for CardReferenceLibrary persistence, deduplication, matching, and recognizer fusion."""

    @pytest.fixture
    def test_lib(self, tmp_path):
        from app.database.db import DatabaseManager
        from app.vision.card_reference_library import CardReferenceLibrary
        db = DatabaseManager(db_path=tmp_path / "test.db")
        return CardReferenceLibrary(db_manager=db, storage_dir=tmp_path / "refs")

    def _create_synthetic_card_image(self, rank_str: str, is_red: bool) -> np.ndarray:
        """Helper to create a recognizable synthetic card crop (120x168 BGR)."""
        img = np.full((168, 120, 3), 245, dtype=np.uint8)  # Off-white card surface
        color = (20, 20, 210) if is_red else (20, 20, 20)   # Red or Black in BGR

        # Draw border
        import cv2
        cv2.rectangle(img, (2, 2), (117, 165), (180, 180, 180), 1)

        # Draw rank character on corner
        cv2.putText(img, rank_str, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
        # Draw suit symbol representation
        cv2.circle(img, (22, 55), 8, color, -1)
        return img

    def test_reference_library_add_and_deduplicate(self, test_lib, tmp_path):
        card = Card(Rank.ACE, Suit.SPADES)
        img = self._create_synthetic_card_image("A", is_red=False)

        # 1. Add reference
        ref1 = test_lib.add_reference(image=img, card=card, source="user_confirmed")
        assert ref1.card_code == "AS"
        assert ref1.confirmed is True
        assert Path(ref1.image_path).exists()

        # 2. Add identical image -> Deduplication check
        ref2 = test_lib.add_reference(image=img, card=card, source="user_confirmed")
        assert ref2.id == ref1.id  # Same ID returned, deduplicated!

        refs = test_lib.get_references_for_card("AS")
        assert len(refs) == 1

    def test_reference_library_multiple_samples_for_same_card(self, test_lib):
        card = Card(Rank.KING, Suit.HEARTS)
        img1 = self._create_synthetic_card_image("K", is_red=True)
        img2 = np.copy(img1)
        # Modify img2 slightly so it has a different hash
        img2[100:120, 50:70] = (0, 0, 180)

        ref1 = test_lib.add_reference(image=img1, card=card)
        ref2 = test_lib.add_reference(image=img2, card=card)

        assert ref1.id != ref2.id
        refs = test_lib.get_references_for_card("KH")
        assert len(refs) == 2

        summary = test_lib.get_summary()
        assert summary["counts"]["KH"] == 2
        assert summary["total_samples"] >= 2

    def test_reference_library_matching_and_alternatives(self, test_lib):
        card_10d = Card(Rank.TEN, Suit.DIAMONDS)
        img_10d = self._create_synthetic_card_image("10", is_red=True)
        test_lib.add_reference(image=img_10d, card=card_10d)

        # Query with exact image
        match = test_lib.match_crop(img_10d)
        assert match is not None
        assert match.card_code == "10D"
        assert match.card == card_10d
        assert match.score >= 0.85
        assert match.is_confident is True

        # Query with empty image
        assert test_lib.match_crop(np.zeros((5, 5, 3), dtype=np.uint8)) is None

    def test_reference_library_deletion(self, test_lib):
        card = Card(Rank.QUEEN, Suit.CLUBS)
        img = self._create_synthetic_card_image("Q", is_red=False)
        ref = test_lib.add_reference(image=img, card=card)

        path = Path(ref.image_path)
        assert path.exists()

        # Delete single reference
        deleted = test_lib.delete_reference(ref.id)
        assert deleted is True
        assert not path.exists()
        assert len(test_lib.get_references_for_card("QC")) == 0

    def test_reference_library_persistence_across_reloads(self, tmp_path):
        from app.database.db import DatabaseManager
        from app.vision.card_reference_library import CardReferenceLibrary

        db_path = tmp_path / "persistent.db"
        storage_path = tmp_path / "persistent_refs"

        # Instance 1: add reference
        db1 = DatabaseManager(db_path=db_path)
        lib1 = CardReferenceLibrary(db_manager=db1, storage_dir=storage_path)
        card = Card(Rank.JACK, Suit.SPADES)
        img = self._create_synthetic_card_image("J", is_red=False)
        lib1.add_reference(image=img, card=card)

        # Instance 2: reload from same DB and storage
        db2 = DatabaseManager(db_path=db_path)
        lib2 = CardReferenceLibrary(db_manager=db2, storage_dir=storage_path)

        match = lib2.match_crop(img)
        assert match is not None
        assert match.card_code == "JS"
        assert match.card == card
        assert match.score >= 0.85

    def test_card_recognizer_fusion_with_reference_library(self, test_lib):
        card_as = Card(Rank.ACE, Suit.SPADES)
        img_as = self._create_synthetic_card_image("A", is_red=False)
        test_lib.add_reference(image=img_as, card=card_as)

        recognizer = CardRecognizer(reference_library=test_lib)

        # Build CardCrop
        crop = CardCrop(
            bbox=(0, 0, 120, 168),
            image=img_as,
            corner_crop=img_as[0:70, 0:50],
        )

        det = recognizer.recognize_crop(crop)
        assert det.card == card_as
        assert det.card_code == "AS"
        assert det.is_reference_match is True
        assert det.confidence >= 0.85
        assert det.is_uncertain is False

    def test_detected_card_to_dict_format(self):
        card = Card(Rank.KING, Suit.HEARTS)
        det = DetectedCard(
            card=card,
            confidence=0.96,
            bbox=(10, 20, 80, 120),
            raw_crop=np.zeros((120, 80, 3), dtype=np.uint8),
            is_verified=True,
            is_reference_match=True,
            is_uncertain=False,
            alternative_candidates=[("KH", 0.96), ("KD", 0.65)],
        )
        d = det.to_dict()
        assert d["card_code"] == "KH"
        assert d["rank"] == "K"
        assert d["suit"] == "H"
        assert d["confidence"] == 0.96
        assert d["is_verified"] is True
        assert d["is_reference_match"] is True
        assert d["is_uncertain"] is False
        assert len(d["alternative_candidates"]) == 2

