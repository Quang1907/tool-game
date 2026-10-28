"""Reference template engine for card rank and suit pattern matching."""

from __future__ import annotations
from typing import Dict, List, Tuple
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.core.card import Rank, Suit


class CardTemplateEngine:
    """Generates and caches multi-scale reference templates for card ranks and suits."""

    RANK_CHARS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    SUIT_CHARS = {
        Suit.SPADES: "♠",
        Suit.CLUBS: "♣",
        Suit.DIAMONDS: "♦",
        Suit.HEARTS: "♥",
    }

    _FONT_CANDIDATES = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]

    def __init__(self) -> None:
        self._rank_templates: Dict[str, List[np.ndarray]] = {}
        self._suit_templates: Dict[Suit, List[np.ndarray]] = {}
        self._font_path = self._find_usable_font()
        self._unicode_font_path = self._find_unicode_font()
        self._build_templates()

    def _find_usable_font(self) -> str | None:
        for p in self._FONT_CANDIDATES:
            try:
                ImageFont.truetype(p, 24)
                return p
            except Exception:
                continue
        return None

    def _find_unicode_font(self) -> str | None:
        unicode_candidates = [
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Apple Color Emoji.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        for p in unicode_candidates:
            try:
                ImageFont.truetype(p, 24)
                return p
            except Exception:
                continue
        return self._font_path

    def _render_char_bitmap(self, char: str, size: int, font_path: str | None) -> np.ndarray:
        """Renders a single character to a tight binary numpy bitmap."""
        try:
            font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        # Canvas with padding
        canvas_w = size * 2
        canvas_h = size * 2
        img = Image.new("L", (canvas_w, canvas_h), 0)
        draw = ImageDraw.Draw(img)

        # Draw centered
        draw.text((canvas_w // 4, canvas_h // 4), char, fill=255, font=font)
        arr = np.array(img, dtype=np.uint8)

        # Crop to bounding box
        coords = cv2.findNonZero(arr)
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            arr = arr[y : y + h, x : x + w]

        return arr

    def _draw_geometric_suit(self, suit: Suit, size: int) -> np.ndarray:
        """Draws exact geometric vector shape for card suits when font glyphs are unavailable."""
        img = np.zeros((size, size), dtype=np.uint8)
        cx, cy = size // 2, size // 2

        if suit == Suit.DIAMONDS:
            # Rotated square / diamond
            pts = np.array([
                [cx, int(size * 0.1)],
                [int(size * 0.9), cy],
                [cx, int(size * 0.9)],
                [int(size * 0.1), cy],
            ], dtype=np.int32)
            cv2.fillConvexPoly(img, pts, 255)

        elif suit == Suit.HEARTS:
            # Two circles + bottom triangle
            r = int(size * 0.22)
            c1 = (int(cx - r * 0.9), int(cy - r * 0.4))
            c2 = (int(cx + r * 0.9), int(cy - r * 0.4))
            cv2.circle(img, c1, r, 255, -1)
            cv2.circle(img, c2, r, 255, -1)
            pts = np.array([
                [int(cx - r * 1.9), int(cy - r * 0.3)],
                [int(cx + r * 1.9), int(cy - r * 0.3)],
                [cx, int(size * 0.92)],
            ], dtype=np.int32)
            cv2.fillConvexPoly(img, pts, 255)

        elif suit == Suit.SPADES:
            # Inverted heart + stem
            r = int(size * 0.20)
            c1 = (int(cx - r * 0.9), int(cy + r * 0.2))
            c2 = (int(cx + r * 0.9), int(cy + r * 0.2))
            cv2.circle(img, c1, r, 255, -1)
            cv2.circle(img, c2, r, 255, -1)
            pts = np.array([
                [int(cx - r * 1.8), int(cy + r * 0.1)],
                [int(cx + r * 1.8), int(cy + r * 0.1)],
                [cx, int(size * 0.08)],
            ], dtype=np.int32)
            cv2.fillConvexPoly(img, pts, 255)
            # Stem at bottom
            stem = np.array([
                [cx, cy],
                [int(cx - size * 0.18), int(size * 0.92)],
                [int(cx + size * 0.18), int(size * 0.92)],
            ], dtype=np.int32)
            cv2.fillConvexPoly(img, stem, 255)

        elif suit == Suit.CLUBS:
            # Three circles + stem
            r = int(size * 0.18)
            cv2.circle(img, (cx, int(cy - r * 1.1)), r, 255, -1)
            cv2.circle(img, (int(cx - r * 1.0), int(cy + r * 0.3)), r, 255, -1)
            cv2.circle(img, (int(cx + r * 1.0), int(cy + r * 0.3)), r, 255, -1)
            stem = np.array([
                [cx, cy],
                [int(cx - size * 0.16), int(size * 0.92)],
                [int(cx + size * 0.16), int(size * 0.92)],
            ], dtype=np.int32)
            cv2.fillConvexPoly(img, stem, 255)

        return img

    def _build_templates(self) -> None:
        """Constructs multi-scale templates for all 13 ranks and 4 suits."""
        scales = [24, 32, 40, 48]

        for r_char in self.RANK_CHARS:
            self._rank_templates[r_char] = []
            for sz in scales:
                bm = self._render_char_bitmap(r_char, sz, self._font_path)
                if bm.size > 0:
                    self._rank_templates[r_char].append(bm)
                if r_char == "10":
                    bm1 = self._render_char_bitmap("1", sz, self._font_path)
                    bm0 = self._render_char_bitmap("0", sz, self._font_path)
                    if bm1.size > 0 and bm0.size > 0:
                        h_max = max(bm1.shape[0], bm0.shape[0])
                        b1 = cv2.resize(bm1, (max(1, int(bm1.shape[1] * h_max / bm1.shape[0])), h_max))
                        b0 = cv2.resize(bm0, (max(1, int(bm0.shape[1] * h_max / bm0.shape[0])), h_max))
                        tight_10 = np.zeros((h_max, b1.shape[1] + b0.shape[1] + 2), dtype=np.uint8)
                        tight_10[:, 0 : b1.shape[1]] = b1
                        tight_10[:, b1.shape[1] + 2 : b1.shape[1] + 2 + b0.shape[1]] = b0
                        self._rank_templates["10"].append(tight_10)

        for suit, s_char in self.SUIT_CHARS.items():
            self._suit_templates[suit] = []
            for sz in scales:
                # First try font rendering
                bm = self._render_char_bitmap(s_char, sz, self._unicode_font_path)
                if bm.size > 0 and cv2.countNonZero(bm) > 15:
                    self._suit_templates[suit].append(bm)
                # Also include geometric template for robust fallback
                geom_bm = self._draw_geometric_suit(suit, sz)
                self._suit_templates[suit].append(geom_bm)

    def match_rank(self, patch_gray: np.ndarray) -> Tuple[Rank, float]:
        """Matches a grayscale rank patch against the template library using normalized cross-correlation."""
        best_score = -1.0
        best_rank_char = "A"

        # Binarize patch
        _, patch_bin = cv2.threshold(patch_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # Invert if dark text on light background (standard playing card is black/red on white)
        if np.mean(patch_bin) > 127:
            patch_bin = 255 - patch_bin

        # Crop patch to non-zero content
        pts = cv2.findNonZero(patch_bin)
        if pts is not None:
            x, y, w, h = cv2.boundingRect(pts)
            if w >= 4 and h >= 8:
                patch_bin = patch_bin[y : y + h, x : x + w]

        patch_h, patch_w = patch_bin.shape[:2]
        if patch_h < 4 or patch_w < 3:
            return Rank.ACE, 0.30

        # Check for multi-digit '10': two distinct tall components side by side
        top_contours, _ = cv2.findContours(patch_bin.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        tall_comps = [
            cnt for cnt in top_contours
            if cv2.boundingRect(cnt)[3] >= patch_h * 0.70 and cv2.contourArea(cnt) > 40
        ]
        is_multi_digit_10 = (
            len(tall_comps) >= 2
            and (patch_w / float(patch_h) >= 0.70)
            and abs(cv2.boundingRect(tall_comps[0])[0] - cv2.boundingRect(tall_comps[1])[0]) >= 10
        )

        # Topological feature extraction: detect closed loops (holes) and their vertical positions
        contours, hierarchy = cv2.findContours(patch_bin.copy(), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        holes = []
        if hierarchy is not None and len(hierarchy[0]) > 1:
            for i, h_info in enumerate(hierarchy[0]):
                if h_info[3] != -1:  # Child contour = hole
                    hole_area = cv2.contourArea(contours[i])
                    if hole_area >= 6:
                        M = cv2.moments(contours[i])
                        if M["m00"] > 0:
                            cy = M["m01"] / M["m00"]
                            rel_y = cy / float(patch_h)
                            holes.append((hole_area, rel_y))

        top_holes = [h for h in holes if h[1] <= 0.46]
        bot_holes = [h for h in holes if h[1] >= 0.54]
        has_two_balanced_holes = False
        if top_holes and bot_holes:
            max_top = max(h[0] for h in top_holes)
            max_bot = max(h[0] for h in bot_holes)
            if min(max_top, max_bot) / max(max_top, max_bot) >= 0.35:
                has_two_balanced_holes = True

        has_bottom_hole = len(bot_holes) > 0 and not has_two_balanced_holes and (not top_holes or max(h[0] for h in bot_holes) > max(h[0] for h in top_holes) * 3)
        has_top_hole = len(top_holes) > 0 and not has_two_balanced_holes and (not bot_holes or max(h[0] for h in top_holes) > max(h[0] for h in bot_holes) * 3)

        for r_char, tmpls in self._rank_templates.items():
            char_best = -1.0
            for tmpl in tmpls:
                # Resize template to patch height maintaining aspect ratio
                th, tw = tmpl.shape[:2]
                if th == 0 or tw == 0:
                    continue

                scaled_w = max(1, int(tw * (patch_h / float(th))))
                resized_tmpl = cv2.resize(tmpl, (scaled_w, patch_h))

                # Normalize sizes for correlation (centered alignment)
                target_w = max(patch_w, scaled_w)
                p_pad = np.zeros((patch_h, target_w), dtype=np.uint8)
                t_pad = np.zeros((patch_h, target_w), dtype=np.uint8)

                pad_p = (target_w - patch_w) // 2
                pad_t = (target_w - scaled_w) // 2
                p_pad[:, pad_p : pad_p + patch_w] = patch_bin
                t_pad[:, pad_t : pad_t + scaled_w] = resized_tmpl

                res = cv2.matchTemplate(p_pad, t_pad, cv2.TM_CCOEFF_NORMED)
                score = float(res[0][0]) if res is not None else -1.0
                if score > char_best:
                    char_best = score

            # Apply multi-digit consistency for 10
            if is_multi_digit_10:
                if r_char == "10":
                    char_best = max(0.92, char_best * 1.5)
                else:
                    char_best *= 0.10
            else:
                if r_char == "10":
                    char_best *= 0.15

            # Apply topological consistency to prevent 6 vs 5, 9 vs 6, or 8 vs Q misclassifications
            if not is_multi_digit_10:
                if has_two_balanced_holes:
                    if r_char == "8":
                        char_best = min(0.99, char_best * 1.35)
                    elif r_char in ("2", "3", "4", "5", "6", "7", "9", "J", "K", "Q"):
                        char_best *= 0.15
                elif has_bottom_hole and not has_top_hole:
                    # Distinct closed loop at bottom -> only 6 matches this topology
                    if r_char in ("2", "3", "4", "5", "7", "J", "K", "8"):
                        char_best *= 0.15
                    elif r_char == "6":
                        char_best = min(0.99, char_best * 1.35)
                elif has_top_hole and not has_bottom_hole:
                    # Distinct closed loop at top -> only 9 matches this topology
                    if r_char in ("2", "3", "4", "5", "6", "7", "J", "K", "8"):
                        char_best *= 0.15
                    elif r_char == "9":
                        char_best = min(0.99, char_best * 1.35)
                elif not holes:
                    # Digits with no holes (2, 3, 5, 7, etc.) cannot be digits with closed loops
                    if r_char in ("6", "8", "9", "Q"):
                        char_best *= 0.20

            if char_best > best_score:
                best_score = char_best
                best_rank_char = r_char

        # Calibrate NCC score: noise is <0.25, legitimate characters score 0.35-0.95
        calibrated = min(0.98, max(0.20, best_score * 1.6)) if best_score > 0 else 0.20
        return Rank.from_str(best_rank_char), calibrated

    def match_suit(self, patch_gray: np.ndarray, is_red: bool) -> Tuple[Suit, float]:
        """Matches a suit patch against templates, constrained by color detection (Red vs Black)."""
        candidate_suits = [Suit.HEARTS, Suit.DIAMONDS] if is_red else [Suit.SPADES, Suit.CLUBS]

        _, patch_bin = cv2.threshold(patch_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        if np.mean(patch_bin) > 127:
            patch_bin = 255 - patch_bin

        pts = cv2.findNonZero(patch_bin)
        if pts is not None:
            x, y, w, h = cv2.boundingRect(pts)
            if w >= 4 and h >= 4:
                patch_bin = patch_bin[y : y + h, x : x + w]

        patch_h, patch_w = patch_bin.shape[:2]
        if patch_h < 4 or patch_w < 4:
            return candidate_suits[0], 0.40

        best_score = -1.0
        best_suit = candidate_suits[0]

        for s in candidate_suits:
            for tmpl in self._suit_templates[s]:
                th, tw = tmpl.shape[:2]
                if th == 0 or tw == 0:
                    continue
                resized_tmpl = cv2.resize(tmpl, (patch_w, patch_h))
                res = cv2.matchTemplate(patch_bin, resized_tmpl, cv2.TM_CCOEFF_NORMED)
                score = float(res[0][0]) if res is not None else -1.0

                if score > best_score:
                    best_score = score
                    best_suit = s

        calibrated = min(0.98, max(0.20, best_score * 1.6)) if best_score > 0 else 0.30
        return best_suit, calibrated
