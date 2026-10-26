"""Card Detector discovering card objects at arbitrary positions, overlapping clusters, and perspective warps.

Replaces fixed-frame slicing with computer vision saliency, Sobel-X vertical edge peak analysis,
non-card UI rejection (buttons, circular avatars, empty slots), and independent detection confidence.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

from app.vision.image_preprocessor import ImagePreprocessor


class CardDetectionStatus:
    CONFIRMED = "CONFIRMED"
    UNCERTAIN = "UNCERTAIN"
    INVALID_CARD_BOUNDS = "INVALID_CARD_BOUNDS"
    DETECTION_FAILED = "DETECTION_FAILED"


@dataclass
class CardDetection:
    """Represents an isolated card object detected in the image."""
    detection_id: str
    bbox: Tuple[int, int, int, int]         # (x, y, w, h)
    polygon: List[Tuple[int, int]]          # 4 points [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
    detection_confidence: float             # Confidence that object is a real card [0.0, 1.0]
    is_overlapping: bool = False            # True if card belongs to cascaded/fanned cluster
    is_partially_occluded: bool = False     # True if card is covered by an adjacent card
    area: float = 0.0
    aspect_ratio: float = 0.0
    rejection_reason: str = ""
    detection_status: str = "CONFIRMED"     # CONFIRMED, UNCERTAIN, INVALID_CARD_BOUNDS, DETECTION_FAILED
    crop_status: str = "VALID_CARD_CROP"    # VALID_CARD_CROP, INVALID_CARD_CROP, MULTIPLE_CARDS_IN_CROP, PARTIALLY_OCCLUDED, LOW_QUALITY_CROP
    duplicate_group: str = ""

    def to_dict(self) -> dict:
        return {
            "detection_id": self.detection_id,
            "bbox": list(self.bbox),
            "width": self.bbox[2],
            "height": self.bbox[3],
            "aspect_ratio": self.aspect_ratio,
            "polygon": [list(pt) for pt in self.polygon],
            "detection_confidence": round(self.detection_confidence, 4),
            "occlusion": self.is_partially_occluded,
            "is_overlapping": self.is_overlapping,
            "detection_status": self.detection_status,
            "crop_status": self.crop_status,
            "duplicate_group": self.duplicate_group,
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class CardCrop:
    """Cropped and rectified card patch with dedicated corner, rank, and suit crops."""
    bbox: Tuple[int, int, int, int]
    image: np.ndarray                       # Rectified normalized patch (120x168)
    corner_crop: np.ndarray                 # Top-left index area
    rank_crop: Optional[np.ndarray] = None  # Dedicated rank glyph crop (~36x40)
    suit_crop: Optional[np.ndarray] = None  # Dedicated suit symbol crop (~36x36)
    raw_patch: Optional[np.ndarray] = None  # Unmodified patch from source image
    detection: Optional[CardDetection] = None
    crop_status: str = "VALID_CARD_CROP"

    def __post_init__(self) -> None:
        if self.detection is None:
            # Construct synthetic detection for backward compatibility
            x, y, w, h = self.bbox
            poly = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
            object.__setattr__(
                self,
                "detection",
                CardDetection(
                    detection_id="card_000",
                    bbox=self.bbox,
                    polygon=poly,
                    detection_confidence=0.95,
                    detection_status="CONFIRMED",
                    crop_status=self.crop_status,
                ),
            )


@dataclass
class DetectionDebugInfo:
    """Comprehensive diagnostic metrics from detection pipeline."""
    total_detected: int = 0
    total_rejected: int = 0
    rejection_breakdown: Dict[str, int] = field(default_factory=dict)
    detection_time_ms: float = 0.0
    recognition_time_ms: float = 0.0
    uncertain_count: int = 0
    confirmed_count: int = 0
    raw_candidates_found: int = 0
    accepted_detections: List[CardDetection] = field(default_factory=list)
    duplicate_detections: List[CardDetection] = field(default_factory=list)
    rejected_detections: List[CardDetection] = field(default_factory=list)
    uncertain_detections: List[CardDetection] = field(default_factory=list)
    original_frame: Optional[np.ndarray] = None
    detection_overlay: Optional[np.ndarray] = None
    status: str = "OK"                      # OK, DETECTION_FAILED, INVALID_CARD_BOUNDS

    def summary_str(self) -> str:
        rejected_details = ", ".join(f"{k}: {v}" for k, v in self.rejection_breakdown.items()) or "0"
        return (
            f"Phát hiện hợp lệ: {self.total_detected} lá | "
            f"Trùng lặp: {len(self.duplicate_detections)} | "
            f"Bị loại: {self.total_rejected} đối tượng ({rejected_details}) | "
            f"Nghi ngờ: {self.uncertain_count} lá | "
            f"Trạng thái: {self.status} | "
            f"Thời gian quét: {self.detection_time_ms:.1f}ms"
        )


class CardDetector:
    """Discovers real card objects in arbitrary layouts without fixed slot grids."""

    def __init__(self, preprocessor: Optional[ImagePreprocessor] = None) -> None:
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.last_debug_info: Optional[DetectionDebugInfo] = None

    def detect_cards(self, table_image: np.ndarray) -> List[CardCrop]:
        """Convenience method returning list of CardCrops."""
        crops, debug_info = self.detect_card_objects(table_image)
        self.last_debug_info = debug_info
        return crops

    def detect_card_objects(
        self, table_image: np.ndarray
    ) -> Tuple[List[CardCrop], DetectionDebugInfo]:
        """Performs true computer vision detection across the given image/ROI.

        Pipeline:
        1. Color & Lightness Saliency Mask (white card body vs dark felt/UI).
        2. External Contour Discovery & Oriented Bounding Box calculation.
        3. Non-card UI Filter (rejects saturated buttons, circular avatars, empty slots).
        4. Overlapping / Cascaded Cluster Dissection via Sobel-X column gradient peaks.
        5. Non-Maximum Suppression (NMS).
        6. Spatial Ordering (row-by-row, left-to-right).
        7. Perspective Warp & Normalization into 120x168 CardCrop patches.
        """
        start_t = time.perf_counter()
        debug_info = DetectionDebugInfo()

        if table_image is None or table_image.size == 0:
            self.last_debug_info = debug_info
            return [], debug_info

        img_h, img_w = table_image.shape[:2]
        if img_h < 20 or img_w < 20:
            self.last_debug_info = debug_info
            return [], debug_info

        # Handle case where the input image is already a single pre-cropped card patch
        if 50 <= img_w <= 300 and 70 <= img_h <= 400 and 0.50 <= (img_w / float(img_h)) <= 0.90:
            single_det = CardDetection(
                detection_id="card_001",
                bbox=(0, 0, img_w, img_h),
                polygon=[(0, 0), (img_w - 1, 0), (img_w - 1, img_h - 1), (0, img_h - 1)],
                detection_confidence=0.98,
                is_overlapping=False,
                is_partially_occluded=False,
                area=float(img_w * img_h),
                aspect_ratio=img_w / float(img_h),
            )
            crop = self._build_single_crop(table_image, single_det)
            debug_info.total_detected = 1
            debug_info.detection_time_ms = (time.perf_counter() - start_t) * 1000.0
            self.last_debug_info = debug_info
            return [crop], debug_info

        # 1. Color and Lightness Saliency Mask (Pure White Card Body)
        hsv = cv2.cvtColor(table_image, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(table_image, cv2.COLOR_BGR2GRAY)

        # Standard card faces are white/off-white (low saturation, high brightness)
        # Exclude green selection halos and table felt
        is_green_glow = (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] > 50)
        is_white = (hsv[:, :, 1] <= 110) & (hsv[:, :, 2] >= 115) & (gray >= 120) & (~is_green_glow)
        card_mask = is_white.astype(np.uint8) * 255

        # Light morphological close with small 3x3 kernel to bridge text/glyphs without merging adjacent cards
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        cleaned_mask = cv2.morphologyEx(card_mask, cv2.MORPH_OPEN, kernel)
        closed_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel)

        # Explicitly detect prominent colored UI elements (buttons, banners) for rejection diagnostics
        is_colored_ui = (hsv[:, :, 1] >= 120) & (hsv[:, :, 2] >= 110)
        ui_contours, _ = cv2.findContours(is_colored_ui.astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for u_cnt in ui_contours:
            if cv2.contourArea(u_cnt) > 300:
                ux, uy, uw, uh = cv2.boundingRect(u_cnt)
                u_roi_hsv = hsv[uy : uy + uh, ux : ux + uw]
                if np.mean(u_roi_hsv[:, :, 1]) > 130:
                    self._record_rejection(debug_info, "ui_button")

        # 2. External Contour Discovery
        contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        debug_info.raw_candidates_found = len(contours)

        candidates: List[CardDetection] = []
        min_card_area = max(350, int(img_h * img_w * 0.002))
        max_card_area = int(img_h * img_w * 0.92)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_card_area:
                self._record_rejection(debug_info, "too_small")
                continue
            if area > max_card_area:
                self._record_rejection(debug_info, "too_large")
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            if w < 16 or h < 24:
                self._record_rejection(debug_info, "too_narrow")
                continue

            roi_hsv = hsv[y : y + h, x : x + w]
            roi_gray = gray[y : y + h, x : x + w]
            roi_white_count = np.count_nonzero(
                (roi_hsv[:, :, 1] <= 110) & (roi_hsv[:, :, 2] >= 115) & (roi_gray >= 120)
            )
            whiteness_ratio = roi_white_count / float(w * h)

            # 3. Non-card UI Rejection Filters
            # A. Highly saturated Game Buttons
            mean_sat = float(np.mean(roi_hsv[:, :, 1]))
            if mean_sat > 130 and whiteness_ratio < 0.25:
                self._record_rejection(debug_info, "ui_button")
                continue

            # B. Circular Player Avatars
            perimeter = cv2.arcLength(cnt, True)
            circularity = (4.0 * np.pi * area) / (perimeter * perimeter) if perimeter > 0 else 0.0
            if circularity > 0.82 and whiteness_ratio < 0.35:
                self._record_rejection(debug_info, "ui_avatar")
                continue

            # C. Empty card slots or table felt
            mean_val = float(np.mean(roi_hsv[:, :, 2]))
            if mean_val < 90 and whiteness_ratio < 0.15:
                self._record_rejection(debug_info, "empty_slot_or_felt")
                continue

            # D. Extreme aspect ratios (banners or separators)
            aspect = w / float(h)
            if aspect < 0.20 or aspect > 6.0:
                self._record_rejection(debug_info, "extreme_aspect")
                continue

            # 4. Overlapping Cluster vs. Single Card Detection
            ideal_card_w = int(h * 0.714)
            is_cluster = (aspect >= 0.95 and w >= int(ideal_card_w * 1.35)) and w >= 60

            if is_cluster:
                # Horizontal cascaded or fanned overlapping cards
                cluster_dets = self._dissect_overlapping_cluster(
                    table_image, (x, y, w, h), roi_gray
                )
                candidates.extend(cluster_dets)
            else:
                # Single card: Refine bounding box to snugly fit physical white card body
                rx, ry, rw, rh = ImagePreprocessor.refine_card_boundary(table_image, (x, y, w, h))

                min_rect = cv2.minAreaRect(cnt)
                box_pts = cv2.boxPoints(min_rect)
                box_pts_ordered = ImagePreprocessor.order_quadrilateral_points(box_pts)
                poly = [(int(p[0]), int(p[1])) for p in box_pts_ordered]

                # Aspect ratio fidelity to typical playing card (0.71)
                ideal_aspect = 0.714
                card_aspect = min(rw, rh) / float(max(rw, rh)) if max(rw, rh) > 0 else 0.7
                aspect_score = max(0.0, 1.0 - abs(card_aspect - ideal_aspect) / 0.45)
                det_conf = round(
                    float(min(0.99, 0.70 + 0.28 * (aspect_score * 0.5 + whiteness_ratio * 0.5))),
                    4,
                )

                det_status = "CONFIRMED"
                is_occluded = (0.18 <= card_aspect < 0.60) and (whiteness_ratio >= 0.25)
                if is_occluded:
                    # Expand width to full card size so crop captures rank/suit in top-left
                    rw = min(int(rh * 0.714), table_image.shape[1] - rx)
                elif det_conf < 0.75:
                    det_status = "UNCERTAIN"
                elif card_aspect < 0.40 or card_aspect > 0.98 or whiteness_ratio < 0.28:
                    det_status = "INVALID_CARD_BOUNDS"

                candidates.append(
                    CardDetection(
                        detection_id="",
                        bbox=(rx, ry, rw, rh),
                        polygon=poly,
                        detection_confidence=det_conf,
                        is_overlapping=is_occluded,
                        is_partially_occluded=is_occluded,
                        area=float(rw * rh),
                        aspect_ratio=round(rw / float(rh), 3),
                        detection_status=det_status,
                        crop_status="PARTIALLY_OCCLUDED" if is_occluded else "VALID_CARD_CROP",
                    )
                )

        # 5. Non-Maximum Suppression (NMS) with Object-Level Deduplication
        filtered_dets = self._apply_nms(candidates, debug_info=debug_info, iou_threshold=0.48)

        # 6. Natural Spatial Ordering (row-by-row top to bottom, then left to right)
        if filtered_dets:
            avg_h = np.median([d.bbox[3] for d in filtered_dets])
            row_tolerance = max(20.0, avg_h * 0.45)
            filtered_dets.sort(key=lambda d: (int(d.bbox[1] / row_tolerance), d.bbox[0]))

        # 7. Crop Validation & Normalization into CardCrop patches
        crops: List[CardCrop] = []
        accepted_dets: List[CardDetection] = []
        for idx, det in enumerate(filtered_dets):
            det.detection_id = f"card_{idx + 1:03d}"
            crop_status, reason = self.validate_crop(table_image, det)
            det.crop_status = crop_status

            if crop_status == "INVALID_CARD_CROP":
                det.rejection_reason = reason or "INVALID_CARD_CROP"
                det.detection_status = "INVALID_CARD_BOUNDS"
                debug_info.rejected_detections.append(det)
                self._record_rejection(debug_info, det.rejection_reason)
                continue

            crop = self._build_single_crop(table_image, det)
            crop.crop_status = crop_status
            crops.append(crop)
            accepted_dets.append(det)

            if det.detection_status == "UNCERTAIN" or crop_status == "LOW_QUALITY_CROP":
                debug_info.uncertain_detections.append(det)
                debug_info.uncertain_count += 1
            else:
                debug_info.confirmed_count += 1

        debug_info.accepted_detections = accepted_dets
        debug_info.total_detected = len(crops)
        debug_info.detection_time_ms = (time.perf_counter() - start_t) * 1000.0
        debug_info.original_frame = table_image.copy()
        debug_info.detection_overlay = self.generate_detection_overlay(table_image, accepted_dets)

        if not crops:
            debug_info.status = "DETECTION_FAILED"
        elif any(d.detection_status == "INVALID_CARD_BOUNDS" for d in accepted_dets):
            debug_info.status = "INVALID_CARD_BOUNDS"
        else:
            debug_info.status = "OK"

        self.last_debug_info = debug_info
        return crops, debug_info

    def _dissect_overlapping_cluster(
        self,
        table_image: np.ndarray,
        cluster_bbox: Tuple[int, int, int, int],
        cluster_gray: np.ndarray,
    ) -> List[CardDetection]:
        """Dissects overlapping/fanned cards using vertical edge transitions in top/bottom margin strips.

        Analyzes the top 16% and bottom 16% margin strips of the cluster, avoiding center
        drawings of face cards (J, Q, K) to eliminate false internal edge peaks.
        """
        bx, by, bw, bh = cluster_bbox
        detections: List[CardDetection] = []

        # Analyze clean margin strips (top 16% and bottom 16%) where illustrations don't exist
        margin_h = max(6, int(bh * 0.16))
        top_strip = cluster_gray[:margin_h, :]
        bot_strip = cluster_gray[-margin_h:, :]

        sobel_top = np.abs(cv2.Sobel(top_strip, cv2.CV_32F, 1, 0, ksize=3))
        sobel_bot = np.abs(cv2.Sobel(bot_strip, cv2.CV_32F, 1, 0, ksize=3))
        col_sums = np.sum(sobel_top, axis=0) + np.sum(sobel_bot, axis=0)

        # Smooth column gradient profile with Gaussian kernel
        kernel_size = 5
        smoothed = cv2.GaussianBlur(col_sums.reshape(1, -1), (kernel_size, 1), 0).flatten()

        est_card_w = max(40, int(bh * 0.714))
        min_card_step = max(28, int(bh * 0.20))
        max_possible_cards = min(5, max(2, int((bw - est_card_w) / min_card_step) + 1))

        mean_val = float(np.mean(smoothed))
        std_val = float(np.std(smoothed))
        max_peak = float(np.max(smoothed))
        thresh = max(mean_val + 0.85 * std_val, max_peak * 0.40)

        # Collect candidate transition peaks
        candidate_peaks: List[Tuple[int, float]] = []
        for col in range(min_card_step, bw - min_card_step):
            if smoothed[col] > thresh:
                window = smoothed[max(0, col - 8) : min(bw, col + 9)]
                if smoothed[col] == np.max(window):
                    candidate_peaks.append((col, float(smoothed[col])))

        # Pick the most prominent peaks with minimum separation
        candidate_peaks.sort(key=lambda p: p[1], reverse=True)
        chosen_peaks: List[int] = [0]
        for col, _ in candidate_peaks:
            if len(chosen_peaks) >= max_possible_cards:
                break
            if all(abs(col - cp) >= min_card_step for cp in chosen_peaks):
                chosen_peaks.append(col)

        chosen_peaks.sort()

        for i, left_col in enumerate(chosen_peaks):
            is_last = (i == len(chosen_peaks) - 1)
            is_occluded = not is_last

            abs_x = bx + left_col
            abs_w = min(est_card_w, table_image.shape[1] - abs_x)
            if is_last:
                abs_w = min(est_card_w, bw - left_col)

            if abs_w < 20:
                continue

            poly = [
                (abs_x, by),
                (abs_x + abs_w, by),
                (abs_x + abs_w, by + bh),
                (abs_x, by + bh),
            ]

            det = CardDetection(
                detection_id="",
                bbox=(abs_x, by, abs_w, bh),
                polygon=poly,
                detection_confidence=0.92 if not is_occluded else 0.88,
                is_overlapping=True,
                is_partially_occluded=is_occluded,
                area=float(abs_w * bh),
                aspect_ratio=round(abs_w / float(bh), 3),
                detection_status="CONFIRMED",
                crop_status="PARTIALLY_OCCLUDED" if is_occluded else "VALID_CARD_CROP",
            )
            detections.append(det)

        return detections

    def _build_single_crop(
        self, table_image: np.ndarray, det: CardDetection
    ) -> CardCrop:
        """Warps and rectifies card patch into normalized 120x168 crop with dedicated glyph crops."""
        x, y, w, h = det.bbox
        img_h, img_w = table_image.shape[:2]

        # Extract normalized 120x168 patch
        if len(det.polygon) == 4 and not det.is_overlapping:
            rectified = self.preprocessor.warp_perspective_polygon(table_image, det.polygon)
        else:
            raw = table_image[max(0, y) : min(img_h, y + h), max(0, x) : min(img_w, x + w)]
            rectified = self.preprocessor.rectify_card(raw)

        # Dedicated crops matching verified card geometry
        corner_h = int(ImagePreprocessor.CARD_TARGET_HEIGHT * 0.50)
        corner_w = int(ImagePreprocessor.CARD_TARGET_WIDTH * 0.42)
        corner_crop = rectified[0:corner_h, 0:corner_w]

        rank_crop = rectified[8:48, 8:44]
        suit_crop = rectified[46:82, 8:44]
        raw_patch = table_image[max(0, y) : min(img_h, y + h), max(0, x) : min(img_w, x + w)].copy()

        return CardCrop(
            bbox=det.bbox,
            image=rectified,
            corner_crop=corner_crop,
            rank_crop=rank_crop,
            suit_crop=suit_crop,
            raw_patch=raw_patch,
            detection=det,
        )

    def _build_card_crops(
        self, table_image: np.ndarray, bboxes: List[Tuple[int, int, int, int]]
    ) -> List[CardCrop]:
        """Constructs CardCrop objects from bounding box rectangles."""
        crops: List[CardCrop] = []
        for idx, (x, y, w, h) in enumerate(bboxes):
            det = CardDetection(
                detection_id=f"card_{idx + 1:03d}",
                bbox=(x, y, w, h),
                polygon=[(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
                detection_confidence=0.95,
                detection_status="CONFIRMED",
            )
            crops.append(self._build_single_crop(table_image, det))
        return crops

    @staticmethod
    def _record_rejection(debug_info: DetectionDebugInfo, reason: str) -> None:
        debug_info.total_rejected += 1
        debug_info.rejection_breakdown[reason] = (
            debug_info.rejection_breakdown.get(reason, 0) + 1
        )

    @staticmethod
    def generate_detection_overlay(
        image: np.ndarray,
        detections: List[CardDetection],
    ) -> np.ndarray:
        """Draws bounding boxes, polygons, IDs, confidence, and status on a copy of the image."""
        if image is None or image.size == 0:
            return np.zeros((100, 100, 3), dtype=np.uint8)
        overlay = image.copy()
        for idx, det in enumerate(detections):
            x, y, w, h = det.bbox
            status = getattr(det, "detection_status", "CONFIRMED")
            if status == "CONFIRMED":
                color = (0, 220, 50)  # Green
            elif status == "UNCERTAIN":
                color = (0, 180, 255)  # Orange
            else:
                color = (40, 40, 255)  # Red

            if len(det.polygon) == 4 and not det.is_overlapping:
                pts = np.array(det.polygon, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(overlay, [pts], isClosed=True, color=color, thickness=2)
            else:
                cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 2)

            det_pct = int(det.detection_confidence * 100)
            tag = f"{det.detection_id or f'#{idx+1}'}: {w}x{h} ({det_pct}%) [{status}]"
            cv2.putText(overlay, tag, (x, max(14, y - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)

        return overlay

    @classmethod
    def validate_crop(
        cls,
        table_image: np.ndarray,
        det: CardDetection,
    ) -> Tuple[str, str]:
        """Validates a candidate card crop based on size, aspect ratio, whiteness, and content.

        Returns (crop_status, reason):
        - VALID_CARD_CROP: Clean, isolated card with visible rank and suit area.
        - PARTIALLY_OCCLUDED: Legitimate card in an overlapping fan.
        - INVALID_CARD_CROP: Non-card UI, dark table felt, or invalid geometry.
        - MULTIPLE_CARDS_IN_CROP: Contains two full unseparated cards.
        - LOW_QUALITY_CROP: Degraded, noisy, or extreme low contrast.
        """
        x, y, w, h = det.bbox
        img_h, img_w = table_image.shape[:2]

        if w < 24 or h < 35:
            return "INVALID_CARD_CROP", "TOO_SMALL"

        aspect = w / float(h)
        if aspect < 0.35 or aspect > 1.45:
            return "INVALID_CARD_CROP", "INVALID_ASPECT_RATIO"

        raw_patch = table_image[max(0, y) : min(img_h, y + h), max(0, x) : min(img_w, x + w)]
        if raw_patch.size == 0 or raw_patch.shape[0] < 20 or raw_patch.shape[1] < 15:
            return "INVALID_CARD_CROP", "EMPTY_PATCH"

        hsv = cv2.cvtColor(raw_patch, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(raw_patch, cv2.COLOR_BGR2GRAY)

        is_white = (hsv[:, :, 1] <= 110) & (hsv[:, :, 2] >= 115) & (gray >= 115)
        white_ratio = np.count_nonzero(is_white) / float(raw_patch.shape[0] * raw_patch.shape[1])

        mean_sat = float(np.mean(hsv[:, :, 1]))
        if white_ratio < 0.20 or (mean_sat > 140 and white_ratio < 0.28):
            return "INVALID_CARD_CROP", "UI_OBJECT_OR_FELT"

        if white_ratio < 0.28:
            return "LOW_QUALITY_CROP", "LOW_PAPER_WHITENESS"

        if aspect > 1.25 and not det.is_overlapping:
            return "MULTIPLE_CARDS_IN_CROP", "MULTIPLE_CARDS_IN_CROP"

        if det.is_partially_occluded or (0.38 <= aspect <= 0.65):
            return "PARTIALLY_OCCLUDED", ""

        return "VALID_CARD_CROP", ""

    @classmethod
    def _apply_nms(
        cls,
        candidates: List[CardDetection],
        debug_info: Optional[DetectionDebugInfo] = None,
        iou_threshold: float = 0.48,
    ) -> List[CardDetection]:
        """Applies rigorous 3-stage object deduplication:
        1. Sub-box / Containment suppression (eliminates inner contours and drawings).
        2. IoU-based deduplication (eliminates jittered / shifted duplicate boxes).
        3. Preserves genuine distinct overlapping cards in a fan.
        """
        if not candidates:
            return []

        # Sort by detection confidence descending, then by area descending
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (c.detection_confidence, c.area),
            reverse=True,
        )

        keep: List[CardDetection] = []
        duplicates: List[CardDetection] = []

        for cand in sorted_candidates:
            cx, cy, cw, ch = cand.bbox
            cand_area = float(cw * ch)
            is_dup = False
            suppression_reason = ""
            dup_group = ""

            for kept in keep:
                kx, ky, kw, kh = kept.bbox
                kept_area = float(kw * kh)

                # Intersection rectangle
                ix1 = max(cx, kx)
                iy1 = max(cy, ky)
                ix2 = min(cx + cw, kx + kw)
                iy2 = min(cy + ch, ky + kh)

                iw = max(0, ix2 - ix1)
                ih = max(0, iy2 - iy1)
                intersection = float(iw * ih)

                if intersection <= 0:
                    continue

                union = cand_area + kept_area - intersection
                iou = intersection / union if union > 0 else 0.0
                containment_cand = intersection / cand_area if cand_area > 0 else 0.0
                containment_kept = intersection / kept_area if kept_area > 0 else 0.0

                # Check if in same horizontal row
                vert_diff = abs(cy - ky)
                max_h = max(ch, kh)
                same_row = vert_diff <= (0.28 * max_h)

                # Check left edge separation
                horiz_diff = abs(cx - kx)
                min_step = max(26, int(min(ch, kh) * 0.20))

                # CASE 1: High IoU -> Duplicate detection of the same card
                if iou >= iou_threshold:
                    is_dup = True
                    suppression_reason = "DUPLICATE_BOX"
                    dup_group = kept.detection_id or "group_001"
                    break

                # CASE 2: Sub-box containment (cand is a smaller child contour inside kept)
                if containment_cand >= 0.70:
                    is_dup = True
                    suppression_reason = "CONTAINED_IN_ANOTHER_CARD"
                    dup_group = kept.detection_id or "group_001"
                    break

                # CASE 3: Moderate IoU or overlap in the same row
                if same_row:
                    if horiz_diff < min_step:
                        # Left edges start at almost the same spot -> same card!
                        is_dup = True
                        suppression_reason = "DUPLICATE_BOX"
                        dup_group = kept.detection_id or "group_001"
                        break
                    elif cand.is_overlapping or kept.is_overlapping:
                        # Genuine separate overlapping cards in a fan!
                        # Both have valid left edges and separate start columns
                        continue

            if is_dup:
                cand.rejection_reason = suppression_reason
                cand.duplicate_group = dup_group
                cand.detection_status = "INVALID_CARD_BOUNDS"
                duplicates.append(cand)
                if debug_info is not None:
                    cls._record_rejection(debug_info, suppression_reason)
            else:
                keep.append(cand)

        if debug_info is not None:
            debug_info.duplicate_detections = duplicates

        return keep


class CardTracker:
    """Tracks detected cards across frames to detect movement vs card changes.

    Ensures that when cards merely change positions on screen without changing
    ranks/suits, the game state does NOT trigger an expensive recalculation.
    """

    def __init__(self, debounce_frames: int = 2) -> None:
        self.debounce_frames = debounce_frames
        self.last_card_signature: Optional[Tuple[str, ...]] = None
        self.last_positions: List[Tuple[int, int, int, int]] = []
        self.stable_count: int = 0

    def evaluate_frame(
        self, detected_cards: List[any]
    ) -> Tuple[str, bool]:
        """Evaluates detected cards.

        Returns (status_label, should_recalculate):
        - "EMPTY": No cards detected
        - "CONTENT_CHANGED": Card composition (ranks/suits) changed -> recalculate
        - "MOVED_NO_RECALCULATE": Same cards, only moved position -> skip solve
        - "STABLE_NO_CHANGE": Exact same cards and positions
        """
        if not detected_cards:
            self.last_card_signature = None
            self.last_positions = []
            return "EMPTY", False

        # Build position-independent card signature (sorted card codes)
        card_codes = sorted([c.card_code for c in detected_cards if hasattr(c, "card_code") and c.card_code != "??"])
        current_sig = tuple(card_codes)
        current_positions = [c.bbox for c in detected_cards]

        if self.last_card_signature is None:
            # First read
            self.last_card_signature = current_sig
            self.last_positions = current_positions
            self.stable_count = 1
            return "CONTENT_CHANGED", True

        if current_sig != self.last_card_signature:
            # Cards themselves changed (e.g. dealt new hand)
            self.last_card_signature = current_sig
            self.last_positions = current_positions
            self.stable_count = 1
            return "CONTENT_CHANGED", True

        # Ranks and suits are identical. Check if positions moved.
        has_moved = False
        if len(current_positions) == len(self.last_positions):
            for (cx, cy, _, _), (lx, ly, _, _) in zip(current_positions, self.last_positions):
                if abs(cx - lx) > 12 or abs(cy - ly) > 12:
                    has_moved = True
                    break
        else:
            has_moved = True

        self.last_positions = current_positions
        if has_moved:
            return "MOVED_NO_RECALCULATE", False

        return "STABLE_NO_CHANGE", False
