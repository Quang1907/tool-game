"""Computer Vision, Template Engine, and Screen Capture package for Binh 13 Analyzer."""

from app.vision.screen_capture import ScreenCapture, ScreenInfo
from app.vision.image_preprocessor import ImagePreprocessor
from app.vision.card_detector import CardDetector, CardCrop
from app.vision.template_engine import CardTemplateEngine
from app.vision.card_recognizer import CardRecognizer, DetectedCard
from app.vision.recognition_validator import RecognitionValidator, ValidationReport
from app.vision.card_reference_library import (
    CardReference,
    CardReferenceLibrary,
    CardReferenceMatch,
)

__all__ = [
    "ScreenCapture",
    "ScreenInfo",
    "ImagePreprocessor",
    "CardDetector",
    "CardCrop",
    "CardTemplateEngine",
    "CardRecognizer",
    "DetectedCard",
    "RecognitionValidator",
    "ValidationReport",
    "CardReference",
    "CardReferenceLibrary",
    "CardReferenceMatch",
]
