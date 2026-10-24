"""Unit tests for Computer Vision, Template Matching, Screen Capture, and Recognition Validation."""

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
