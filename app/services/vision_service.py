"""Asynchronous worker for executing Computer Vision recognition without blocking UI thread."""

from __future__ import annotations
from typing import List, Optional
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from app.vision.card_detector import CardCrop, CardDetector
from app.vision.card_recognizer import CardRecognizer, DetectedCard


class VisionWorker(QObject):
    """Worker object executing card detection and recognition in background thread."""

    progress = Signal(int, int, str)       # current, total, status
    finished = Signal(list)                # list[DetectedCard]
    error = Signal(str)                    # error message

    def __init__(
        self,
        image: np.ndarray,
        detector: CardDetector,
        recognizer: CardRecognizer,
        mode: str = "AUTO",                # "AUTO", "CONTOURS", "STRIP_13", "GRID_3_5_5"
    ) -> None:
        super().__init__()
        self.image = image
        self.detector = detector
        self.recognizer = recognizer
        self.mode = mode

    def run(self) -> None:
        """Executes detection and recognition."""
        try:
            self.progress.emit(10, 100, "Đang định vị vị trí các lá bài...")

            # 1. Detection
            if self.mode == "STRIP_13":
                bboxes = self.detector.slice_horizontal_row(self.image, card_count=13)
                crops = self.detector._build_card_crops(self.image, bboxes)
            elif self.mode == "GRID_3_5_5":
                bboxes = self.detector.slice_three_rows_grid(self.image)
                crops = self.detector._build_card_crops(self.image, bboxes)
            else:
                crops = self.detector.detect_cards(self.image)

            if not crops:
                self.finished.emit([])
                return

            total_crops = len(crops)
            self.progress.emit(30, 100, f"Đã tìm thấy {total_crops} lá bài. Đang nhận diện...")

            # 2. Recognition
            detected_cards: List[DetectedCard] = []
            for idx, crop in enumerate(crops):
                det = self.recognizer.recognize_crop(crop)
                detected_cards.append(det)

                pct = 30 + int(((idx + 1) / total_crops) * 70)
                tag = det.card.unicode_name if det.card else "?"
                self.progress.emit(pct, 100, f"Đang nhận diện lá {idx + 1}/{total_crops}: {tag}...")

            self.progress.emit(100, 100, f"Hoàn thành nhận diện {len(detected_cards)} lá!")
            self.finished.emit(detected_cards)

        except Exception as e:
            self.error.emit(str(e))
