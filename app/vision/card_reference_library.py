"""Card Reference Library for persisting and matching user-confirmed card samples."""

from __future__ import annotations
from dataclasses import dataclass, field
import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid
import cv2
import numpy as np

from app.core.card import Card, Rank, Suit
from app.database.db import DatabaseManager


@dataclass
class CardReference:
    """Represents a persistent user-confirmed reference image of a playing card."""
    id: str
    card_code: str
    rank: str
    suit: str
    image_path: str
    source: str = "user_confirmed"
    confirmed: bool = True
    created_at: str = ""
    image_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def reference_id(self) -> str:
        return self.id

    @property
    def active(self) -> bool:
        return self.confirmed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference_id": self.id,
            "id": self.id,
            "card_code": self.card_code,
            "rank": self.rank,
            "suit": self.suit,
            "image_path": self.image_path,
            "image_hash": self.image_hash,
            "source": self.source,
            "created_at": self.created_at,
            "normalization_version": self.metadata.get("normalization_version", "v2"),
            "active": self.confirmed,
            "confirmed": self.confirmed,
            "metadata": self.metadata,
        }


@dataclass
class CardReferenceMatch:
    """Result of matching a crop image against the reference library."""
    card: Optional[Card]
    card_code: str
    score: float
    reference_id: str
    alternative_candidates: List[Tuple[str, float]] = field(default_factory=list)
    is_confident: bool = False
    rank_score: float = 0.0
    suit_score: float = 0.0
    matched_image_path: str = ""


@dataclass
class _CachedReference:
    """In-memory pre-processed reference data for ultra-fast matching."""
    ref_id: str
    card_code: str
    card: Card
    full_gray: np.ndarray        # Normalized to (80, 112)
    corner_gray: np.ndarray      # Normalized to (36, 48)
    rank_glyph: np.ndarray       # Normalized to (24, 36)
    suit_glyph: np.ndarray       # Normalized to (28, 28)
    rank_char: str
    suit_char: str
    is_red: bool
    dhash_int: int
    image_path: str = ""


class CardReferenceLibrary:
    """Manages confirmed card sample images, persistence in SQLite/disk, and image matching."""

    DEFAULT_REFERENCES_DIR = Path.home() / ".binh13_analyzer" / "references"

    # Standard normalization resolutions for template matching
    NORM_FULL_SIZE = (80, 112)    # (width, height)
    NORM_CORNER_SIZE = (36, 48)   # (width, height)

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        storage_dir: Optional[str | Path] = None,
    ) -> None:
        self.db = db_manager or DatabaseManager()
        self.storage_dir = Path(storage_dir) if storage_dir else self.DEFAULT_REFERENCES_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._cache: List[_CachedReference] = []
        self.reload_cache()

    @staticmethod
    def compute_dhash(img: np.ndarray, hash_size: int = 8) -> str:
        """Computes 64-bit difference hash (dHash) for deduplication.

        Resizes to (hash_size + 1, hash_size), converts to grayscale,
        and compares adjacent horizontal pixels.
        """
        if img is None or img.size == 0:
            return ""

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
        diff = resized[:, 1:] > resized[:, :-1]

        decimal_val = 0
        for bit in diff.flatten():
            decimal_val = (decimal_val << 1) | int(bit)
        return f"{decimal_val:016x}"

    @staticmethod
    def is_red_suit(suit: Suit) -> bool:
        return suit in (Suit.HEARTS, Suit.DIAMONDS)

    @classmethod
    def check_image_is_red(cls, img: np.ndarray) -> bool:
        """Determines if the card image is primarily red or black using robust color metrics.
        If a full card image is provided, automatically focuses on the top-left index area
        to avoid face-card court illustrations (e.g. red robes on Jack/King of Clubs).
        """
        if img is None or img.size == 0 or len(img.shape) < 3:
            return False

        h, w = img.shape[:2]
        if h >= 80 and w >= 60:
            roi = img[0 : int(h * 0.45), 0 : int(w * 0.45)]
        else:
            roi = img

        # 1. Clean green selection borders if present
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        is_green = (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] > 50)
        cleaned = roi.copy()
        cleaned[is_green] = [245, 245, 245]

        b, g, r = cv2.split(cleaned.astype(float))
        # Vibrant red pixels: High R and distinctly higher than G and B, with sufficient saturation
        red_diff = r - np.maximum(g, b)
        is_red_px = (r > 90) & (red_diff > 25) & (hsv[:, :, 1] > 50)
        red_count = int(np.count_nonzero(is_red_px))

        # Dark/black foreground pixels (low luminance and neutral hue)
        gray = cv2.cvtColor(cleaned, cv2.COLOR_BGR2GRAY)
        is_black_px = (gray < 110) & (red_diff <= 20)
        black_count = int(np.count_nonzero(is_black_px))

        # Must have significant red pixels and not be dominated by black foreground
        return red_count >= 25 and (red_count > black_count * 0.35)

    @classmethod
    def extract_primary_glyph(
        cls, patch_bgr: np.ndarray, target_size: Tuple[int, int] = (24, 36)
    ) -> np.ndarray:
        """Extracts the primary foreground glyph (rank character or suit symbol),
        effectively stripping green selection borders, shadows, and background noise.
        Supports multi-digit characters like '10' by combining major adjacent components.
        """
        if patch_bgr is None or patch_bgr.size == 0:
            return np.zeros(target_size[::-1], dtype=np.uint8)

        # 1. Clean green selection borders
        if len(patch_bgr.shape) == 3:
            hsv = cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2HSV)
            is_green = (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] > 50) & (hsv[:, :, 2] > 50)
            cleaned = patch_bgr.copy()
            cleaned[is_green] = [245, 245, 245]
            gray = cv2.cvtColor(cleaned, cv2.COLOR_BGR2GRAY)
        else:
            gray = patch_bgr

        # 2. Otsu thresholding for card foreground
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

        # 3. Connected components analysis to isolate glyphs
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(thresh)
        if num_labels <= 1:
            return np.zeros(target_size[::-1], dtype=np.uint8)

        # Primary component is the one with the largest area
        best_idx = max(range(1, num_labels), key=lambda i: stats[i, cv2.CC_STAT_AREA])
        bx1, by1, bw1, bh1, ba1 = stats[best_idx]
        if ba1 < 12:
            return np.zeros(target_size[::-1], dtype=np.uint8)

        valid_indices = [best_idx]

        # Selectively merge companion digit for multi-digit '10' (only for rank glyphs)
        # Companion digit must have similar height, aligned top, and be horizontally adjacent
        if target_size == (24, 36) and num_labels > 2:
            for i in range(1, num_labels):
                if i == best_idx:
                    continue
                bx, by, bw, bh, ba = stats[i]
                gap = max(0, max(bx1 - (bx + bw), bx - (bx1 + bw1)))
                if (
                    ba >= ba1 * 0.30
                    and bh >= bh1 * 0.65
                    and abs(by - by1) <= 12
                    and gap <= 8
                ):
                    valid_indices.append(i)
                    break

        mask = np.isin(labels, valid_indices).astype(np.uint8) * 255
        pts = cv2.findNonZero(mask)
        if pts is None:
            return np.zeros(target_size[::-1], dtype=np.uint8)

        bx, by, bw, bh = cv2.boundingRect(pts)
        glyph = mask[by : by + bh, bx : bx + bw]
        if glyph.size == 0 or glyph.shape[0] < 2 or glyph.shape[1] < 2:
            return np.zeros(target_size[::-1], dtype=np.uint8)

        return cv2.resize(glyph, target_size, interpolation=cv2.INTER_AREA)

    @classmethod
    def extract_dynamic_corner_patches(
        cls, card_bgr: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Extracts Rank patch and Suit patch dynamically using connected components
        in the top-left index area of a normalized (120, 168) card.
        Properly handles multi-digit '10' by clustering upper components as Rank
        and lower components as Suit, preventing rank/suit bleed.
        """
        if card_bgr is None or card_bgr.size == 0:
            return np.zeros((40, 36, 3), dtype=np.uint8), np.zeros((36, 36, 3), dtype=np.uint8)

        h, w = card_bgr.shape[:2]
        if (w, h) != (120, 168):
            norm = cv2.resize(card_bgr, (120, 168), interpolation=cv2.INTER_AREA)
        else:
            norm = card_bgr

        # Top-left index search area
        corner = norm[0:105, 0:50]
        gray = cv2.cvtColor(corner, cv2.COLOR_BGR2GRAY)

        # Clean green selection borders
        hsv = cv2.cvtColor(corner, cv2.COLOR_BGR2HSV)
        is_green = (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] > 50)
        gray[is_green] = 245

        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(thresh)

        rank_comps = []
        suit_candidates = []
        for i in range(1, num_labels):
            x, y, cw, ch, area = stats[i]
            # Ignore thin border artifacts touching edge
            if (x == 0 and cw <= 6) or (y == 0 and ch <= 6):
                continue
            if area > 35 and cw < 45 and ch < 80:
                center_y = y + ch / 2.0
                if center_y < 52:
                    rank_comps.append((x, y, cw, ch, area))
                elif center_y >= 45 and y < 98 and x < 38:
                    suit_candidates.append((x, y, cw, ch, area))

        # Rank patch: combine all valid components in upper region (e.g. '1' and '0' for 10)
        if rank_comps:
            rx1 = max(0, min(c[0] for c in rank_comps) - 2)
            rx2 = min(50, max(c[0] + c[2] for c in rank_comps) + 2)
            ry1 = max(0, min(c[1] for c in rank_comps) - 2)
            ry2 = min(105, max(c[1] + c[3] for c in rank_comps) + 2)
            rank_patch = corner[ry1:ry2, rx1:rx2]
            rank_cx = (rx1 + rx2) / 2.0
            rank_bottom = ry2
        else:
            rank_patch = norm[8:55, 4:48]
            rank_cx = 18.0
            rank_bottom = 50.0

        # Suit patch: isolate the corner suit pip located directly beneath the rank glyph
        # On court cards (J, Q, K), portrait clothing starts right at x >= 25, y >= 45.
        # The true corner suit pip is strictly aligned beneath the rank glyph horizontally.
        if suit_candidates:
            def suit_score(c: Tuple[int, int, int, int, int]) -> float:
                sx, sy, scw, sch, sarea = c
                scx = sx + scw / 2.0
                horiz_dist = abs(scx - rank_cx)
                vert_dist = max(0.0, float(sy - rank_bottom))
                penalty = horiz_dist * 2.5 + vert_dist * 1.0
                # Penalize portrait fragments with excessive dimensions or area
                if scw > 30 or sch > 35:
                    penalty += 100.0
                if sarea > 550:
                    penalty += 100.0
                return penalty

            suit_candidates.sort(key=suit_score)
            main_suit = suit_candidates[0]
            sx1 = max(0, main_suit[0] - 2)
            sx2 = min(50, main_suit[0] + main_suit[2] + 2)
            sy1 = max(0, main_suit[1] - 2)
            sy2 = min(105, main_suit[1] + main_suit[3] + 2)
            suit_patch = corner[sy1:sy2, sx1:sx2]
        else:
            suit_patch = norm[52:95, 6:46]

        return rank_patch, suit_patch

    def match_rank_glyph(
        self, query_glyph: np.ndarray, min_score: float = 0.65
    ) -> Tuple[Optional[Rank], float, Optional[str]]:
        """Matches a query rank glyph (24x36) against all cached reference rank glyphs."""
        if not self._cache or query_glyph is None or query_glyph.size == 0 or cv2.countNonZero(query_glyph) < 10:
            return None, 0.0, None

        best_score = -1.0
        best_rank: Optional[Rank] = None
        best_ref_id: Optional[str] = None

        for ref in self._cache:
            if ref.rank_glyph is None or ref.rank_glyph.size == 0 or cv2.countNonZero(ref.rank_glyph) < 10:
                continue
            res = cv2.matchTemplate(query_glyph, ref.rank_glyph, cv2.TM_CCOEFF_NORMED)
            score = float(res[0][0])
            if score > best_score:
                best_score = score
                best_rank = ref.card.rank
                best_ref_id = ref.ref_id

        if best_score < min_score:
            return None, max(0.0, best_score), None

        return best_rank, max(0.0, best_score), best_ref_id

    def match_suit_glyph(
        self, query_glyph: np.ndarray, is_red: bool, min_score: float = 0.65
    ) -> Tuple[Optional[Suit], float, Optional[str]]:
        """Matches a query suit glyph (28x28) against all cached reference suit glyphs with matching color."""
        if not self._cache or query_glyph is None or query_glyph.size == 0 or cv2.countNonZero(query_glyph) < 10:
            return None, 0.0, None

        best_score = -1.0
        best_suit: Optional[Suit] = None
        best_ref_id: Optional[str] = None

        for ref in self._cache:
            if ref.is_red != is_red:
                continue
            if ref.suit_glyph is None or ref.suit_glyph.size == 0 or cv2.countNonZero(ref.suit_glyph) < 10:
                continue
            res = cv2.matchTemplate(query_glyph, ref.suit_glyph, cv2.TM_CCOEFF_NORMED)
            score = float(res[0][0])
            if score > best_score:
                best_score = score
                best_suit = ref.card.suit
                best_ref_id = ref.ref_id

        if best_score < min_score:
            return None, max(0.0, best_score), None

        return best_suit, max(0.0, best_score), best_ref_id

    def add_reference(
        self,
        image: np.ndarray,
        card: Card,
        source: str = "user_confirmed",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CardReference:
        """Saves a confirmed card sample to disk and SQLite, preventing duplicates."""
        if image is None or image.size == 0:
            raise ValueError("Reference image cannot be empty")

        card_code = f"{card.rank.char}{card.suit.char.upper()}"
        image_hash = self.compute_dhash(image)
        metadata_dict = metadata or {}
        metadata_dict.setdefault("normalization_version", "v2")
        metadata_dict.setdefault("active", True)

        # 1. Deduplication check: Do not re-save if exact image hash exists for this card
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM card_references WHERE image_hash = ? AND card_code = ?",
                (image_hash, card_code),
            )
            existing = cursor.fetchone()
            if existing:
                return self._row_to_reference(existing)

        # 2. Save image file to storage directory
        ref_id = str(uuid.uuid4())
        filename = f"{card_code}_{image_hash[:8]}_{ref_id[:6]}.png"
        file_path = self.storage_dir / filename
        success = cv2.imwrite(str(file_path), image)
        if not success:
            raise IOError(f"Failed to write reference image to {file_path}")

        now_str = datetime.datetime.now().isoformat()
        metadata_json = json.dumps(metadata_dict)

        # 3. Insert record into database
        try:
            with self.db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO card_references (
                        id, card_code, rank, suit, image_path, source,
                        confirmed, created_at, image_hash, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                    """,
                    (
                        ref_id,
                        card_code,
                        card.rank.char,
                        card.suit.char.upper(),
                        str(file_path),
                        source,
                        now_str,
                        image_hash,
                        metadata_json,
                    ),
                )
        except Exception:
            if file_path.exists():
                file_path.unlink()
            raise

        ref = CardReference(
            id=ref_id,
            card_code=card_code,
            rank=card.rank.char,
            suit=card.suit.char.upper(),
            image_path=str(file_path),
            source=source,
            confirmed=True,
            created_at=now_str,
            image_hash=image_hash,
            metadata=metadata_dict,
        )

        # 4. Update in-memory cache
        self._add_to_cache(ref, image)
        return ref

    def delete_reference(self, ref_id: str) -> bool:
        """Deletes a reference sample from SQLite and deletes the image file from disk."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT image_path FROM card_references WHERE id = ?", (ref_id,))
            row = cursor.fetchone()
            if not row:
                return False

            file_path = Path(row["image_path"])
            conn.execute("DELETE FROM card_references WHERE id = ?", (ref_id,))

        # Remove file from disk
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"[CardReferenceLibrary] Warning: Failed to delete file {file_path}: {e}")

        # Remove from in-memory cache
        self._cache = [c for c in self._cache if c.ref_id != ref_id]
        return True

    def delete_references_for_card(self, card_code: str) -> int:
        """Deletes all reference samples for a given card code (e.g. 'AS')."""
        refs = self.get_references_for_card(card_code)
        count = 0
        for r in refs:
            if self.delete_reference(r.id):
                count += 1
        return count

    def get_references_for_card(self, card_code: str) -> List[CardReference]:
        """Retrieves all confirmed samples for a specific card code."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM card_references WHERE card_code = ? ORDER BY created_at DESC",
                (card_code,),
            )
            return [self._row_to_reference(row) for row in cursor.fetchall()]

    def get_all_references(self) -> List[CardReference]:
        """Retrieves all reference samples across all 52 cards."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM card_references ORDER BY card_code ASC, created_at DESC")
            return [self._row_to_reference(row) for row in cursor.fetchall()]

    list_all_references = get_all_references

    def get_reference_by_id(self, ref_id: str) -> Optional[CardReference]:
        """Retrieves a single reference by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM card_references WHERE id = ?", (ref_id,))
            row = cursor.fetchone()
            return self._row_to_reference(row) if row else None

    def get_reference_image(self, ref_id: str) -> Optional[np.ndarray]:
        """Loads and returns the BGR reference image for a given reference ID."""
        ref = self.get_reference_by_id(ref_id)
        if not ref or not ref.image_path:
            return None
        p = Path(ref.image_path)
        if p.exists():
            return cv2.imread(str(p))
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Returns statistical summary of reference samples in library."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT card_code, COUNT(*) as count FROM card_references GROUP BY card_code"
            )
            counts = {row["card_code"]: row["count"] for row in cursor.fetchall()}

        total_samples = sum(counts.values())
        unique_cards = len(counts)
        return {
            "counts": counts,
            "total_samples": total_samples,
            "unique_cards_covered": unique_cards,
            "coverage_pct": round((unique_cards / 52.0) * 100, 1),
        }

    def clear_all(self) -> None:
        """Clears all reference samples from DB and deletes files (for testing/reset)."""
        refs = self.get_all_references()
        for r in refs:
            self.delete_reference(r.id)
        self._cache.clear()

    def reload_cache(self) -> None:
        """Reloads all reference samples from DB into in-memory pre-processed cache."""
        self._cache.clear()
        refs = self.get_all_references()
        for ref in refs:
            p = Path(ref.image_path)
            if not p.exists():
                continue
            img = cv2.imread(str(p))
            if img is not None and img.size > 0:
                self._add_to_cache(ref, img)

    def _add_to_cache(self, ref: CardReference, img: np.ndarray) -> None:
        """Pre-processes image and adds it to the in-memory matching cache."""
        try:
            rank = Rank.from_str(ref.rank)
            suit = Suit.from_str(ref.suit)
            card = Card(rank, suit)
        except Exception:
            return

        h, w = img.shape[:2]
        if h < 10 or w < 10:
            return

        # Normalize card dimensions to standard (120, 168)
        if (w, h) != (120, 168):
            norm_card = cv2.resize(img, (120, 168), interpolation=cv2.INTER_AREA)
        else:
            norm_card = img

        # Extract top-left corner (rank + suit indicator)
        corner_h = max(8, int(h * 0.42))
        corner_w = max(8, int(w * 0.45))
        corner = img[0:corner_h, 0:corner_w]

        # Normalize resolutions
        full_norm = cv2.resize(img, self.NORM_FULL_SIZE, interpolation=cv2.INTER_AREA)
        corner_norm = cv2.resize(corner, self.NORM_CORNER_SIZE, interpolation=cv2.INTER_AREA)

        full_gray = cv2.cvtColor(full_norm, cv2.COLOR_BGR2GRAY)
        corner_gray = cv2.cvtColor(corner_norm, cv2.COLOR_BGR2GRAY)

        # Dedicated rank & suit crops and isolated glyphs
        d_rank, d_suit = self.extract_dynamic_corner_patches(norm_card)
        rank_crop = d_rank if (d_rank is not None and d_rank.size > 0) else norm_card[8:55, 6:46]
        suit_crop = d_suit if (d_suit is not None and d_suit.size > 0) else norm_card[52:95, 6:46]
        rank_glyph = self.extract_primary_glyph(rank_crop, (24, 36))
        suit_glyph = self.extract_primary_glyph(suit_crop, (28, 28))

        dhash_hex = ref.image_hash or self.compute_dhash(img)
        dhash_int = int(dhash_hex, 16) if dhash_hex else 0
        is_red = self.is_red_suit(card.suit)

        cached = _CachedReference(
            ref_id=ref.id,
            card_code=ref.card_code,
            card=card,
            full_gray=full_gray,
            corner_gray=corner_gray,
            rank_glyph=rank_glyph,
            suit_glyph=suit_glyph,
            rank_char=card.rank.char,
            suit_char=card.suit.char.upper(),
            is_red=is_red,
            dhash_int=dhash_int,
            image_path=ref.image_path,
        )
        self._cache.append(cached)

    def match_crop(
        self,
        crop_image: np.ndarray,
        corner_crop: Optional[np.ndarray] = None,
        rank_crop: Optional[np.ndarray] = None,
        suit_crop: Optional[np.ndarray] = None,
        min_confidence: float = 0.65,
    ) -> Optional[CardReferenceMatch]:
        """Matches a query card crop against the library using multi-scale normalized cross-correlation
        across isolated rank glyph, suit glyph, corner index, and full layout.
        Strictly enforces that Rank and Suit must both match independently.
        """
        if not self._cache or crop_image is None or crop_image.size == 0:
            return None

        qh, qw = crop_image.shape[:2]
        if qh < 10 or qw < 10:
            return None

        # 1. Normalize query card to standard (120, 168)
        if (qw, qh) != (120, 168):
            q_norm = cv2.resize(crop_image, (120, 168), interpolation=cv2.INTER_AREA)
        else:
            q_norm = crop_image

        if corner_crop is not None and corner_crop.size > 0:
            qc = corner_crop
        else:
            ch = max(8, int(qh * 0.42))
            cw = max(8, int(qw * 0.45))
            qc = crop_image[0:ch, 0:cw]

        if rank_crop is None or rank_crop.size == 0 or suit_crop is None or suit_crop.size == 0:
            d_rank, d_suit = self.extract_dynamic_corner_patches(q_norm)
            if rank_crop is None or rank_crop.size == 0:
                rank_crop = d_rank
            if suit_crop is None or suit_crop.size == 0:
                suit_crop = d_suit

        q_rank_glyph = self.extract_primary_glyph(rank_crop, (24, 36))
        q_suit_glyph = self.extract_primary_glyph(suit_crop, (28, 28))

        q_corner_norm = cv2.resize(qc, self.NORM_CORNER_SIZE, interpolation=cv2.INTER_AREA)
        q_full_norm = cv2.resize(crop_image, self.NORM_FULL_SIZE, interpolation=cv2.INTER_AREA)

        q_corner_gray = cv2.cvtColor(q_corner_norm, cv2.COLOR_BGR2GRAY)
        q_full_gray = cv2.cvtColor(q_full_norm, cv2.COLOR_BGR2GRAY)

        is_red_s = self.check_image_is_red(suit_crop)
        is_red_r = self.check_image_is_red(rank_crop)
        if is_red_s == is_red_r:
            query_is_red = is_red_s
        elif not is_red_r and is_red_s:
            # On court cards (J, Q, K), portrait graphics may have red pigment, but the corner rank letter is pure black.
            # A standard card with a black rank letter can NEVER be a red suit (Hearts or Diamonds).
            query_is_red = False
        elif is_red_r and not is_red_s:
            query_is_red = True
        else:
            query_is_red = is_red_s

        has_rank_glyph = cv2.countNonZero(q_rank_glyph) >= 10
        has_suit_glyph = cv2.countNonZero(q_suit_glyph) >= 10

        # 2. Score candidates against all cached samples
        card_best_scores: Dict[str, Tuple[float, Card, str, float, float, str]] = {}  # card_code -> (score, Card, ref_id, r_score, s_score, image_path)

        for ref in self._cache:
            color_penalty = 1.0 if query_is_red == ref.is_red else 0.10

            # Rank glyph NCC
            if has_rank_glyph and cv2.countNonZero(ref.rank_glyph) >= 10:
                res_r = cv2.matchTemplate(q_rank_glyph, ref.rank_glyph, cv2.TM_CCOEFF_NORMED)
                score_rank = max(0.0, float(res_r[0][0]))
            else:
                score_rank = 0.50

            # Suit glyph NCC
            if has_suit_glyph and cv2.countNonZero(ref.suit_glyph) >= 10:
                res_s = cv2.matchTemplate(q_suit_glyph, ref.suit_glyph, cv2.TM_CCOEFF_NORMED)
                score_suit = max(0.0, float(res_s[0][0]))
            else:
                score_suit = 0.50

            # Multi-scale Normalized Cross Correlation on corner (focuses on rank & suit glyphs)
            score_corner = max(0.0, float(cv2.matchTemplate(q_corner_gray, ref.corner_gray, cv2.TM_CCOEFF_NORMED)[0][0]))
            for sc in (0.92, 1.08):
                cw_s = max(8, int(ref.corner_gray.shape[1] * sc))
                ch_s = max(8, int(ref.corner_gray.shape[0] * sc))
                if q_corner_gray.shape[0] >= ch_s and q_corner_gray.shape[1] >= cw_s:
                    ref_sc = cv2.resize(ref.corner_gray, (cw_s, ch_s))
                    sc_res = cv2.matchTemplate(q_corner_gray, ref_sc, cv2.TM_CCOEFF_NORMED)
                    score_corner = max(score_corner, float(np.max(sc_res)))

            # Normalized Cross Correlation on full card patch
            res_full = cv2.matchTemplate(q_full_gray, ref.full_gray, cv2.TM_CCOEFF_NORMED)
            score_full = max(0.0, float(res_full[0][0]))

            # Base score with 45% rank, 40% suit, 10% corner, 5% full
            raw_score = (score_rank * 0.45 + score_suit * 0.40 + score_corner * 0.10 + score_full * 0.05) * color_penalty

            # Strict Gating: If rank glyph does NOT match this reference (< 0.68), penalize heavily!
            # Two cards with different ranks CANNOT match!
            if has_rank_glyph and score_rank < 0.68:
                raw_score *= max(0.05, (score_rank / 0.68) ** 3)

            # Strict Gating: If suit glyph does NOT match this reference (< 0.68), penalize heavily!
            if has_suit_glyph and score_suit < 0.68:
                raw_score *= max(0.05, (score_suit / 0.68) ** 3)

            final_score = min(0.99, max(0.0, raw_score))

            if ref.card_code not in card_best_scores or final_score > card_best_scores[ref.card_code][0]:
                card_best_scores[ref.card_code] = (final_score, ref.card, ref.ref_id, score_rank, score_suit, ref.image_path)

        if not card_best_scores:
            return None

        # 3. Rank candidates
        sorted_candidates = sorted(
            [(code, data[0], data[1], data[2], data[3], data[4], data[5]) for code, data in card_best_scores.items()],
            key=lambda x: x[1],
            reverse=True,
        )

        top_code, top_score, top_card, top_ref_id, top_rank_score, top_suit_score, top_img_path = sorted_candidates[0]

        if top_score < min_confidence:
            return None

        # Confidence criteria: overall score >= 0.75, both rank and suit scores >= 0.70, and solid margin
        second_score = sorted_candidates[1][1] if len(sorted_candidates) > 1 else 0.0
        is_confident = (
            (top_score >= 0.75)
            and (top_rank_score >= 0.70)
            and (top_suit_score >= 0.70)
            and ((top_score - second_score) >= 0.03 or top_score >= 0.82)
        )

        alternatives = [(c[0], round(c[1], 3)) for c in sorted_candidates[1:4]]

        return CardReferenceMatch(
            card=top_card,
            card_code=top_code,
            score=round(top_score, 4),
            reference_id=top_ref_id,
            alternative_candidates=alternatives,
            is_confident=is_confident,
            rank_score=round(top_rank_score, 4),
            suit_score=round(top_suit_score, 4),
            matched_image_path=top_img_path,
        )

    def _row_to_reference(self, row: Any) -> CardReference:
        metadata_dict = {}
        if row["metadata_json"]:
            try:
                metadata_dict = json.loads(row["metadata_json"])
            except Exception:
                pass

        return CardReference(
            id=row["id"],
            card_code=row["card_code"],
            rank=row["rank"],
            suit=row["suit"],
            image_path=row["image_path"],
            source=row["source"],
            confirmed=bool(row["confirmed"]),
            created_at=row["created_at"],
            image_hash=row["image_hash"],
            metadata=metadata_dict,
        )
