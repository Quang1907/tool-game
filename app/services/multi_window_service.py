"""Multi-Window Coordinator: Orchestrates single-frame capture, 3 ROI cropping, card detection, and selective solving."""

from __future__ import annotations
import time
from typing import Dict, List, Optional
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.core.card import Card
from app.core.solver import HandArrangement, Solver
from app.vision.card_detector import CardDetector
from app.vision.card_recognizer import CardRecognizer, DetectedCard
from app.vision.card_state import CardStateManager, WindowCardState
from app.vision.roi_manager import ROIManager, WindowROI
from app.vision.screen_capture import ScreenCapture
from app.vision.screen_capture_service import ScreenCaptureService
from app.vision.window_manager import WindowItem, WindowManager


class MultiWindowWorker(QObject):
    """Background worker executing capture, detection, recognition, and solving across 3 game windows."""

    frame_processed = Signal(int, object, object)  # window_id, WindowCardState, crop_image
    solution_found = Signal(int, object)          # window_id, solver_result
    fps_updated = Signal(float)                   # current cycles per second
    status_updated = Signal(str)                  # status message

    def __init__(
        self,
        rois: List[WindowROI],
        detector: Optional[CardDetector] = None,
        recognizer: Optional[CardRecognizer] = None,
        poll_interval_sec: float = 0.20,
    ) -> None:
        super().__init__()
        self.rois = rois
        self.detector = detector or CardDetector()
        self.recognizer = recognizer or CardRecognizer()
        self.solver = Solver()
        self.capture_service = ScreenCaptureService()
        self.roi_manager = ROIManager(retina_scale=2.0)
        self.window_manager = WindowManager()
        self.state_manager = CardStateManager(debounce_frames=2)
        self.poll_interval = poll_interval_sec
        self._is_running = False

    def start_loop(self) -> None:
        """Main execution loop running in background thread."""
        self._is_running = True
        last_t = time.perf_counter()

        while self._is_running:
            loop_start = time.perf_counter()

            try:
                all_wins = self.window_manager.list_windows()
                window_crops: Dict[int, Optional[np.ndarray]] = {}

                # 1. Capture each active window directly by its CGWindowID
                for roi in self.rois:
                    if not roi.is_active:
                        continue

                    target_wid = roi.cg_window_id if roi.cg_window_id > 0 else roi.window_id
                    img = None
                    if target_wid > 0:
                        img = ScreenCapture.capture_window_by_id(target_wid)

                    window_crops[roi.window_id] = img

                    # Compute occlusion for telemetry
                    win_item = WindowItem(
                        window_id=target_wid,
                        owner_name="",
                        title=roi.name,
                        bounds=roi.bounds_pts,
                    )
                    occluded_item = self.window_manager.compute_occlusion(win_item, all_wins)
                    roi.is_occluded = occluded_item.is_occluded
                    roi.occlusion_ratio = occluded_item.occlusion_ratio

                # Fallback to full-screen crop for any ROI without direct capture (e.g. mock/test)
                missing = [r for r in self.rois if r.is_active and window_crops.get(r.window_id) is None]
                if missing:
                    full_frame, scale = self.capture_service.capture_frame()
                    if full_frame is not None:
                        self.roi_manager.retina_scale = scale
                        fb_crops = self.roi_manager.crop_all_rois(full_frame, missing)
                        for r in missing:
                            window_crops[r.window_id] = fb_crops.get(r.window_id)

                # 2. Independent Card Detection & Recognition for each window
                for roi in self.rois:
                    if not roi.is_active:
                        continue

                    crop_img = window_crops.get(roi.window_id)
                    if crop_img is None or crop_img.size == 0:
                        state, _ = self.state_manager.update_window_cards(
                            roi.window_id, [], is_occluded=False
                        )
                        self.frame_processed.emit(roi.window_id, state, None)
                        continue

                    # Card Detection (discovering real card objects, no fixed grid)
                    crops = self.detector.detect_cards(crop_img)

                    # Card Recognition
                    detected_cards = self.recognizer.recognize_all(crops)

                    # Update position-invariant state
                    state, should_solve = self.state_manager.update_window_cards(
                        roi.window_id, detected_cards, is_occluded=False
                    )

                    # Emit visual update for UI
                    self.frame_processed.emit(roi.window_id, state, crop_img)

                    # 3. Solving: if 13 cards are present, calculate optimal 3-chi arrangement
                    valid_cards: List[Card] = []
                    seen_codes = set()
                    for d in sorted(detected_cards, key=lambda x: x.confidence, reverse=True):
                        if d.card is not None and d.card_code not in seen_codes:
                            seen_codes.add(d.card_code)
                            valid_cards.append(d.card)
                            if len(valid_cards) == 13:
                                break

                    if len(valid_cards) == 13:
                        self.status_updated.emit(f"Cửa sổ #{roi.window_id}: Đang tính toán 13 lá...")
                        try:
                            arrangements = self.solver.solve_heuristic(valid_cards)
                            if arrangements:
                                self.solution_found.emit(roi.window_id, arrangements[0])
                        except Exception as e:
                            self.status_updated.emit(f"Cửa sổ #{roi.window_id}: Lỗi giải bài — {e}")

                # Calculate loop FPS
                elapsed = time.perf_counter() - loop_start
                fps = 1.0 / max(0.001, time.perf_counter() - last_t)
                last_t = time.perf_counter()
                self.fps_updated.emit(round(fps, 1))

                # Sleep remainder of poll interval
                sleep_t = max(0.01, self.poll_interval - elapsed)
                time.sleep(sleep_t)

            except Exception as e:
                self.status_updated.emit(f"Lỗi: {e}")
                time.sleep(self.poll_interval)

    def stop_loop(self) -> None:
        self._is_running = False
