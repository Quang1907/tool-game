"""Asynchronous worker for executing Computer Vision recognition without blocking UI thread."""

from __future__ import annotations
from typing import List, Optional
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

import time
from app.vision.card_detector import CardCrop, CardDetector, DetectionDebugInfo
from app.vision.card_recognizer import CardRecognizer, DetectedCard


class VisionWorker(QObject):
    """Worker object executing card detection and recognition in background thread."""

    progress = Signal(int, int, str)       # current, total, status
    finished = Signal(list, object)        # list[DetectedCard], DetectionDebugInfo
    error = Signal(str)                    # error message

    def __init__(
        self,
        image: np.ndarray,
        detector: CardDetector,
        recognizer: CardRecognizer,
        mode: str = "AUTO",
    ) -> None:
        super().__init__()
        self.image = image
        self.detector = detector
        self.recognizer = recognizer
        self.mode = mode

    def run(self) -> None:
        """Executes detection and recognition."""
        try:
            self.progress.emit(10, 100, "Đang quét và định vị hình ảnh các lá bài...")

            # 1. Real Computer Vision Card Detection
            crops, debug_info = self.detector.detect_card_objects(self.image)

            if not crops:
                self.progress.emit(100, 100, "Không tìm thấy lá bài nào trong vùng tìm kiếm.")
                self.finished.emit([], debug_info)
                return

            total_crops = len(crops)
            self.progress.emit(30, 100, f"Đã tìm thấy {total_crops} lá bài thực tế. Đang nhận diện rank và suit...")

            # 2. Card Recognition
            start_recog = time.perf_counter()
            detected_cards: List[DetectedCard] = []
            for idx, crop in enumerate(crops):
                det = self.recognizer.recognize_crop(crop)
                detected_cards.append(det)

                if det.is_uncertain:
                    debug_info.uncertain_count += 1
                else:
                    debug_info.confirmed_count += 1

                pct = 30 + int(((idx + 1) / total_crops) * 70)
                tag = det.card.unicode_name if det.card else "?"
                self.progress.emit(pct, 100, f"Đang nhận diện lá {idx + 1}/{total_crops}: {tag}...")

            debug_info.recognition_time_ms = (time.perf_counter() - start_recog) * 1000.0

            self.progress.emit(100, 100, f"Hoàn thành: {len(detected_cards)} lá ({debug_info.confirmed_count} xác nhận, {debug_info.uncertain_count} nghi ngờ)")
            self.finished.emit(detected_cards, debug_info)

        except Exception as e:
            self.error.emit(str(e))

