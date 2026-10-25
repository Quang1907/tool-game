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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "card_code": self.card_code,
            "rank": self.rank,
            "suit": self.suit,
            "image_path": self.image_path,
            "source": self.source,
            "confirmed": self.confirmed,
            "created_at": self.created_at,
            "image_hash": self.image_hash,
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
        """Determines if the card image is primarily red or black."""
        if len(img.shape) < 3:
            return False
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask_r1 = cv2.inRange(hsv, np.array([0, 45, 45]), np.array([12, 255, 255]))
        mask_r2 = cv2.inRange(hsv, np.array([165, 45, 45]), np.array([180, 255, 255]))
        mask_red = mask_r1 | mask_r2
        return int(cv2.countNonZero(mask_red)) > 15

    @classmethod
    def extract_primary_glyph(
        cls, patch_bgr: np.ndarray, target_size: Tuple[int, int] = (24, 36)
    ) -> np.ndarray:
        """Extracts the primary foreground glyph (rank character or suit symbol),
        effectively stripping green selection borders, shadows, and background noise.
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

        # 3. Connected components analysis to isolate the main glyph
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh)
        if num_labels <= 1:
            return np.zeros(target_size[::-1], dtype=np.uint8)

        best_idx = -1
        best_area = 0
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area > best_area and area > 12:
                best_area = area
                best_idx = i

        if best_idx == -1:
            pts = cv2.findNonZero(thresh)
            if pts is None:
                return np.zeros(target_size[::-1], dtype=np.uint8)
            bx, by, bw, bh = cv2.boundingRect(pts)
            glyph = thresh[by : by + bh, bx : bx + bw]
        else:
            bx = stats[best_idx, cv2.CC_STAT_LEFT]
            by = stats[best_idx, cv2.CC_STAT_TOP]
            bw = stats[best_idx, cv2.CC_STAT_WIDTH]
            bh = stats[best_idx, cv2.CC_STAT_HEIGHT]
            glyph = (labels[by : by + bh, bx : bx + bw] == best_idx).astype(np.uint8) * 255

        if glyph.size == 0 or glyph.shape[0] < 2 or glyph.shape[1] < 2:
            return np.zeros(target_size[::-1], dtype=np.uint8)

        return cv2.resize(glyph, target_size, interpolation=cv2.INTER_AREA)

    def match_rank_glyph(
        self, query_glyph: np.ndarray
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

        return best_rank, max(0.0, best_score), best_ref_id

    def match_suit_glyph(
        self, query_glyph: np.ndarray, is_red: bool
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
        cv2.imwrite(str(file_path), image)

        now_str = datetime.datetime.now().isoformat()
        metadata_json = json.dumps(metadata_dict)

        # 3. Insert record into database
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

    def get_reference_by_id(self, ref_id: str) -> Optional[CardReference]:
        """Retrieves a single reference by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM card_references WHERE id = ?", (ref_id,))
            row = cursor.fetchone()
            return self._row_to_reference(row) if row else None

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
        rank_crop = norm_card[8:48, 8:44]
        suit_crop = norm_card[46:82, 8:44]
        rank_glyph = self.extract_primary_glyph(rank_crop, (24, 36))
        suit_glyph = self.extract_primary_glyph(suit_crop, (28, 28))

        dhash_hex = ref.image_hash or self.compute_dhash(img)
        dhash_int = int(dhash_hex, 16) if dhash_hex else 0
        is_red = self.is_red_suit(suit)

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

        if rank_crop is None or rank_crop.size == 0:
            rank_crop = q_norm[8:48, 8:44]
        if suit_crop is None or suit_crop.size == 0:
            suit_crop = q_norm[46:82, 8:44]

        q_rank_glyph = self.extract_primary_glyph(rank_crop, (24, 36))
        q_suit_glyph = self.extract_primary_glyph(suit_crop, (28, 28))

        q_corner_norm = cv2.resize(qc, self.NORM_CORNER_SIZE, interpolation=cv2.INTER_AREA)
        q_full_norm = cv2.resize(crop_image, self.NORM_FULL_SIZE, interpolation=cv2.INTER_AREA)

        q_corner_gray = cv2.cvtColor(q_corner_norm, cv2.COLOR_BGR2GRAY)
        q_full_gray = cv2.cvtColor(q_full_norm, cv2.COLOR_BGR2GRAY)

        query_is_red = self.check_image_is_red(suit_crop) or self.check_image_is_red(qc)

        has_rank_glyph = cv2.countNonZero(q_rank_glyph) >= 10
        has_suit_glyph = cv2.countNonZero(q_suit_glyph) >= 10

        # 2. Score candidates against all cached samples
        card_best_scores: Dict[str, Tuple[float, Card, str, float, float]] = {}  # card_code -> (score, Card, ref_id, r_score, s_score)

        for ref in self._cache:
            color_penalty = 1.0 if query_is_red == ref.is_red else 0.50

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

            # Normalized Cross Correlation on corner (focuses on rank & suit glyphs)
            res_corner = cv2.matchTemplate(q_corner_gray, ref.corner_gray, cv2.TM_CCOEFF_NORMED)
            score_corner = max(0.0, float(res_corner[0][0]))

            # Normalized Cross Correlation on full card patch
            res_full = cv2.matchTemplate(q_full_gray, ref.full_gray, cv2.TM_CCOEFF_NORMED)
            score_full = max(0.0, float(res_full[0][0]))

            # Weighted combination (40% rank, 35% suit, 15% corner, 10% full)
            raw_score = (score_rank * 0.40 + score_suit * 0.35 + score_corner * 0.15 + score_full * 0.10) * color_penalty
            final_score = min(0.99, max(0.0, raw_score))

            if ref.card_code not in card_best_scores or final_score > card_best_scores[ref.card_code][0]:
                card_best_scores[ref.card_code] = (final_score, ref.card, ref.ref_id, score_rank, score_suit)

        if not card_best_scores:
            return None

        # 3. Rank candidates
        sorted_candidates = sorted(
            [(code, data[0], data[1], data[2], data[3], data[4]) for code, data in card_best_scores.items()],
            key=lambda x: x[1],
            reverse=True,
        )

        top_code, top_score, top_card, top_ref_id, top_rank_score, top_suit_score = sorted_candidates[0]

        if top_score < min_confidence:
            return None

        # Confidence criteria: score >= 0.80 and clear margin over runner-up
        second_score = sorted_candidates[1][1] if len(sorted_candidates) > 1 else 0.0
        is_confident = (top_score >= 0.80) and ((top_score - second_score) >= 0.05)

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
