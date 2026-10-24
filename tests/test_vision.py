"""Unit tests for Computer Vision and Recognition Validation modules."""

import numpy as np
import pytest
from app.core.card import Card, Rank, Suit
from app.vision.card_detector import CardCrop
from app.vision.card_recognizer import CardRecognizer, DetectedCard
from app.vision.image_preprocessor import ImagePreprocessor
from app.vision.recognition_validator import RecognitionValidator


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


class TestCardRecognizer:
    def test_uncalibrated_model_behavior(self):
        recognizer = CardRecognizer(onnx_model_path="models/nonexistent.onnx")
        assert recognizer.has_trained_model is False

        # Create dummy CardCrop
        dummy_img = np.zeros((140, 100, 3), dtype=np.uint8)
        dummy_corner = np.zeros((60, 35, 3), dtype=np.uint8)
        crop = CardCrop(bbox=(10, 10, 100, 140), image=dummy_img, corner_crop=dummy_corner)

        detected = recognizer.recognize_crop(crop)
        assert detected.card is not None
        assert detected.confidence == 0.50  # Realistic uncalibrated baseline
        assert detected.is_verified is False


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
