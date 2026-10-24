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

        for r_char, tmpls in self._rank_templates.items():
            for tmpl in tmpls:
                # Resize template to patch height maintaining aspect ratio
                th, tw = tmpl.shape[:2]
                if th == 0 or tw == 0:
                    continue

                scaled_w = max(1, int(tw * (patch_h / float(th))))
                resized_tmpl = cv2.resize(tmpl, (scaled_w, patch_h))

                # Normalize sizes for correlation
                target_w = max(patch_w, scaled_w)
                p_pad = np.zeros((patch_h, target_w), dtype=np.uint8)
                t_pad = np.zeros((patch_h, target_w), dtype=np.uint8)

                p_pad[:, :patch_w] = patch_bin
                t_pad[:, :scaled_w] = resized_tmpl

                res = cv2.matchTemplate(p_pad, t_pad, cv2.TM_CCOEFF_NORMED)
                score = float(res[0][0]) if res is not None else -1.0

                if score > best_score:
                    best_score = score
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
