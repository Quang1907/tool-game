"""Asynchronous worker for executing Computer Vision recognition without blocking UI thread."""

from __future__ import annotations
from typing import List, Optional
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

import time
from typing import Callable, Dict, List, Optional, Tuple
from app.vision.card_detector import CardCrop, CardDetector, DetectionDebugInfo
from app.vision.card_recognizer import CardRecognizer, DetectedCard


def recognize_cards_pipeline(
    image: np.ndarray,
    detector: Optional[CardDetector] = None,
    recognizer: Optional[CardRecognizer] = None,
    min_confidence: float = 0.65,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[List[DetectedCard], DetectionDebugInfo]:
    """Unified, single source-of-truth Computer Vision pipeline for detecting and recognizing cards.
    Used by both Tab 2 (Quét màn hình CV) and Tab 6 (Bot 3 Cửa Sổ) to guarantee 100% identical results.
    """
    if detector is None:
        detector = CardDetector()
    if recognizer is None:
        recognizer = CardRecognizer()

    if image is None or image.size == 0:
        return [], DetectionDebugInfo()
    if progress_callback:
        progress_callback(10, 100, "Đang quét và định vị hình ảnh các lá bài...")

    crops, debug_info = detector.detect_card_objects(image)
    if not crops:
        if progress_callback:
            progress_callback(100, 100, "Không tìm thấy lá bài nào trong vùng tìm kiếm.")
        return [], debug_info

    total_crops = len(crops)
    if progress_callback:
        progress_callback(30, 100, f"Đã tìm thấy {total_crops} lá bài thực tế. Đang nhận diện rank và suit...")

    start_recog = time.perf_counter()
    raw_detected: List[DetectedCard] = []

    for idx, crop in enumerate(crops):
        det = recognizer.recognize_crop(crop)
        raw_detected.append(det)

        if progress_callback:
            pct = 30 + int(((idx + 1) / total_crops) * 60)
            tag = det.card.unicode_name if det.card else "?"
            progress_callback(pct, 100, f"Đang nhận diện lá {idx + 1}/{total_crops}: {tag}...")

    debug_info.recognition_time_ms = (time.perf_counter() - start_recog) * 1000.0

    # Strict Validation and Filtering identical across both Tab 2 and Tab 6
    strict_detected: List[DetectedCard] = []
    seen_codes: Dict[str, DetectedCard] = {}

    for det in raw_detected:
        if det.card is None:
            continue

        if det.rank_crop is None or det.suit_crop is None:
            continue

        crop_st = getattr(det, "crop_status", "")
        if crop_st in ("NON_CARD_OBJECT", "INVALID_CARD_CROP"):
            continue

        rank_conf = getattr(det, "rank_confidence", 0.0)
        suit_conf = getattr(det, "suit_confidence", 0.0)

        # Both Rank and Suit confidence must meet the minimum threshold
        if rank_conf < min_confidence or suit_conf < min_confidence:
            continue

        det.is_uncertain = False
        det.recognition_status = "CONFIRMED"

        # Deduplication: If the same card code is detected multiple times, keep the one with higher confidence
        code = det.card_code
        if code in seen_codes:
            if det.confidence > seen_codes[code].confidence:
                idx_old = strict_detected.index(seen_codes[code])
                strict_detected[idx_old] = det
                seen_codes[code] = det
        else:
            seen_codes[code] = det
            strict_detected.append(det)

    debug_info.confirmed_count = len(strict_detected)
    debug_info.uncertain_count = len([d for d in raw_detected if d not in strict_detected])

    if progress_callback:
        progress_callback(100, 100, f"Hoàn thành: {len(strict_detected)} lá bài đạt chuẩn.")

    return strict_detected, debug_info


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
        """Executes unified detection and recognition pipeline."""
        try:
            detected_cards, debug_info = recognize_cards_pipeline(
                image=self.image,
                detector=self.detector,
                recognizer=self.recognizer,
                progress_callback=self.progress.emit,
            )
            self.finished.emit(detected_cards, debug_info)
        except Exception as e:
            self.error.emit(str(e))

