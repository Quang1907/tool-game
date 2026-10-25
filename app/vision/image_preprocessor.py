"""Image preprocessing utilities with dynamic resolution scaling."""

from __future__ import annotations
from typing import List, Tuple
import cv2
import numpy as np


class ImagePreprocessor:
    """Preprocesses table screenshots and extracts individual card candidate patches."""

    CARD_TARGET_WIDTH = 120
    CARD_TARGET_HEIGHT = 168  # 1.4 aspect ratio

    @staticmethod
    def to_gray(image: np.ndarray) -> np.ndarray:
        """Converts BGR or RGB image to Grayscale."""
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def enhance_contrast(gray: np.ndarray) -> np.ndarray:
        """Applies Contrast Limited Adaptive Histogram Equalization (CLAHE)."""
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        return clahe.apply(gray)

    @classmethod
    def find_card_bounding_boxes(
        cls,
        image: np.ndarray,
        min_area_ratio: float = 0.002,   # Minimum 0.2% of total image area
        max_area_ratio: float = 0.35,    # Maximum 35% of total image area
    ) -> List[Tuple[int, int, int, int]]:
        """Finds candidate card bounding boxes (x, y, w, h) dynamically scaled to image size.

        Filters by aspect ratio (standard playing card aspect ratio is ~ 1.2 to 1.8).
        """
        img_h, img_w = image.shape[:2]
        total_pixels = img_h * img_w
        min_area = int(total_pixels * min_area_ratio)
        max_area = int(total_pixels * max_area_ratio)

        gray = cls.to_gray(image)
        enhanced = cls.enhance_contrast(gray)
        blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)

        # Multi-scale edge detection
        edges = cv2.Canny(blurred, 30, 120)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(edges, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates: List[Tuple[int, int, int, int]] = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            aspect = h / float(w) if w > 0 else 0

            # Card aspect ratio usually ranges from 1.15 to 1.85
            if 1.1 <= aspect <= 1.95:
                candidates.append((x, y, w, h))

        # Sort candidate cards top-to-bottom, left-to-right
        candidates.sort(key=lambda b: (b[1] // max(1, img_h // 10), b[0]))
        return candidates

    @classmethod
    def remove_green_border(cls, card_crop: np.ndarray) -> np.ndarray:
        """Trims game selection green glowing borders from card edges if detected."""
        if card_crop is None or card_crop.size == 0 or len(card_crop.shape) < 3:
            return card_crop
        ch, cw = card_crop.shape[:2]
        if ch < 30 or cw < 30:
            return card_crop

        hsv = cv2.cvtColor(card_crop, cv2.COLOR_BGR2HSV)
        is_green = (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] > 50) & (hsv[:, :, 2] > 50)

        t = min(6, ch // 12, cw // 12)
        if t <= 0:
            return card_crop

        border_mask = np.zeros((ch, cw), dtype=bool)
        border_mask[:t, :] = True
        border_mask[-t:, :] = True
        border_mask[:, :t] = True
        border_mask[:, -t:] = True

        if int(np.count_nonzero(is_green & border_mask)) > 80:
            return card_crop[t : ch - t, t : cw - t]
        return card_crop

    @classmethod
    def refine_card_boundary(
        cls,
        image: np.ndarray,
        bbox: Tuple[int, int, int, int],
        pad: int = 6,
    ) -> Tuple[int, int, int, int]:
        """Refines a candidate bounding box to snugly fit the physical white card body.

        Trims away green selection glows, table felt, gold UI frames, and drop shadows
        by finding the actual boundary of the white card face within the local search patch.
        """
        img_h, img_w = image.shape[:2]
        x, y, w, h = bbox

        # Expand slightly to ensure card edges are not pre-clipped
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(img_w, x + w + pad)
        y2 = min(img_h, y + h + pad)

        patch = image[y1:y2, x1:x2]
        if patch.size == 0 or patch.shape[0] < 15 or patch.shape[1] < 15:
            return bbox

        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)

        # White paper: low saturation, adequate brightness
        is_white = (hsv[:, :, 1] <= 110) & (hsv[:, :, 2] >= 115) & (gray >= 115)

        # Exclude strong green selection halos explicitly
        is_green_glow = (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] > 55)
        is_white = is_white & (~is_green_glow)

        white_mask = is_white.astype(np.uint8) * 255

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        cleaned = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return bbox

        patch_h, patch_w = patch.shape[:2]
        center_x, center_y = patch_w / 2.0, patch_h / 2.0
        min_card_area = max(100, int(w * h * 0.40))

        best_cnt = None
        best_dist = 999999.0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_card_area:
                continue
            bx, by, bw, bh = cv2.boundingRect(cnt)
            c_dist = abs((bx + bw / 2.0) - center_x) + abs((by + bh / 2.0) - center_y)
            if c_dist < best_dist:
                best_dist = c_dist
                best_cnt = cnt

        if best_cnt is not None:
            bx, by, bw, bh = cv2.boundingRect(best_cnt)
            aspect = bh / float(bw) if bw > 0 else 0
            if 0.5 <= aspect <= 2.2 and bw >= 16 and bh >= 24:
                return (x1 + bx, y1 + by, bw, bh)

        return bbox

    @classmethod
    def order_quadrilateral_points(cls, pts: np.ndarray | List[Tuple[int, int]]) -> np.ndarray:
        """Orders 4 coordinates clockwise: top-left, top-right, bottom-right, bottom-left."""
        pts_arr = np.array(pts, dtype=np.float32).reshape(4, 2)
        rect = np.zeros((4, 2), dtype=np.float32)

        # Top-left has smallest sum, bottom-right has largest sum
        s = pts_arr.sum(axis=1)
        rect[0] = pts_arr[np.argmin(s)]
        rect[2] = pts_arr[np.argmax(s)]

        # Top-right has smallest difference, bottom-left has largest difference
        diff = np.diff(pts_arr, axis=1)
        rect[1] = pts_arr[np.argmin(diff)]
        rect[3] = pts_arr[np.argmax(diff)]

        return rect

    @classmethod
    def warp_perspective_polygon(
        cls,
        image: np.ndarray,
        polygon: List[Tuple[int, int]] | np.ndarray,
        target_w: int = CARD_TARGET_WIDTH,
        target_h: int = CARD_TARGET_HEIGHT,
    ) -> np.ndarray:
        """Applies 4-point perspective warp to extract and rectify a rotated card patch."""
        pts = np.array(polygon, dtype=np.float32)
        if len(pts) != 4:
            x, y, w, h = cv2.boundingRect(pts.astype(np.int32))
            crop = image[max(0, y):y+h, max(0, x):x+w]
            return cls.rectify_card(crop)

        ordered = cls.order_quadrilateral_points(pts)
        dst = np.float32([
            [0, 0],
            [target_w - 1, 0],
            [target_w - 1, target_h - 1],
            [0, target_h - 1],
        ])

        M = cv2.getPerspectiveTransform(ordered, dst)
        warped = cv2.warpPerspective(image, M, (target_w, target_h), flags=cv2.INTER_LINEAR)
        cleaned = cls.remove_green_border(warped)
        return cv2.resize(cleaned, (target_w, target_h))

    @classmethod
    def rectify_card(cls, card_crop: np.ndarray) -> np.ndarray:
        """Resizes a card patch to normalized target dimensions (120x168) with green border removal."""
        cleaned = cls.remove_green_border(card_crop)
        return cv2.resize(cleaned, (cls.CARD_TARGET_WIDTH, cls.CARD_TARGET_HEIGHT))


