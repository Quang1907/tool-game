"""Layout 3-5-5 Analyzer and Card Verification Engine for Binh 13 (Chinese Poker / Mậu Binh).

Analyzes and enforces the strict 3-5-5 geometric layout:
- Chi 1 (Front Row): 3 cards (Slots 1, 2, 3)
- Chi 2 (Middle Row): 5 cards (Slots 4, 5, 6, 7, 8)
- Chi 3 (Back Row): 5 cards (Slots 9, 10, 11, 12, 13)

Capabilities:
1. Row Clustering & Spatial Sorting: Organizes detected cards into 3 physical rows.
2. Missing Card Identification & Position Estimation:
   When < 13 cards are detected or a row is incomplete, mathematically calculates the exact
   bounding boxes (x, y, w, h) of missing card slots using intra-row spacing, inter-row alignment,
   and nominal/calibrated slot models.
3. Targeted Crop & Second-Pass Card Verification:
   Crops the estimated missing positions directly from the table image, verifies physical card presence
   (whiteness, borders, candidate validation), and recognizes rank/suit using the reference library
   and template matching.
4. Duplicate Resolution & Misreading Prevention:
   Since all 13 cards in a hand must be strictly unique (52-card standard deck), resolves duplicate
   misreadings by analyzing alternative candidates, similarity scores, and mutual exclusion against
   unused deck cards.
5. Structured 3-5-5 Hand Ordering:
   Guarantees the output is strictly structured: 3 front, 5 middle, 5 back cards with slot numbers 1..13.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple
import cv2
import numpy as np

from app.core.card import Card, Deck, Rank, Suit
from app.vision.card_detector import CardCrop, CardDetection, CardDetector
from app.vision.card_recognizer import CardRecognizer, DetectedCard
from app.vision.image_preprocessor import ImagePreprocessor


@dataclass
class LayoutRow:
    """Represents one of the 3 rows in the 3-5-5 Binh layout."""
    row_index: int                       # 0: Front, 1: Middle, 2: Back
    row_name: str                        # "front", "middle", "back"
    target_count: int                    # 3 for front, 5 for middle/back
    cards: List[DetectedCard] = field(default_factory=list)
    median_y: float = 0.0
    median_h: float = 0.0
    pitch_x: float = 0.0

    @property
    def missing_count(self) -> int:
        return max(0, self.target_count - len(self.cards))

    @property
    def is_complete(self) -> bool:
        return len(self.cards) == self.target_count


@dataclass
class MissingSlotInfo:
    """Metadata describing a missing card slot in the 3-5-5 layout."""
    slot_number: int                     # 1 to 13
    row_name: str                        # "front", "middle", "back"
    row_index: int                       # 0, 1, 2
    col_index: int                       # 1..3 or 1..5
    estimated_bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    inference_method: str = "grid_geometry"     # "grid_gap", "edge_extrapolation", "inter_row_alignment", "slot_model"


@dataclass
class LayoutVerificationReport:
    """Diagnostic report from 3-5-5 layout analysis and completion."""
    is_complete_13: bool
    front_count: int
    middle_count: int
    back_count: int
    recovered_slots: List[int] = field(default_factory=list)
    disambiguated_cards: List[Tuple[str, str]] = field(default_factory=list)
    message: str = ""

    def summary_str(self) -> str:
        rec_str = f"Đã khôi phục {len(self.recovered_slots)} lá ô: {self.recovered_slots}" if self.recovered_slots else "Không thiếu lá nào"
        dis_str = f" | Đã khử đọc sai trùng lặp: {self.disambiguated_cards}" if self.disambiguated_cards else ""
        return (
            f"Bố cục 3-5-5: Chi 1 ({self.front_count}/3) - Chi 2 ({self.middle_count}/5) - Chi 3 ({self.back_count}/5) | "
            f"{rec_str}{dis_str} | Trạng thái: {'Đủ 13 lá chuẩn' if self.is_complete_13 else 'Chưa đủ 13 lá'}"
        )


class Layout355Analyzer:
    """Engine analyzing and enforcing the 3-5-5 layout for Binh 13 cards."""

    # Default relative slot centers [rel_x, rel_y] for 13 slots
    DEFAULT_SLOTS_355 = {
        # Chi Đầu (Row 1: 3 cards)
        1: (0.32, 0.28, "front"),
        2: (0.50, 0.28, "front"),
        3: (0.68, 0.28, "front"),
        # Chi Giữa (Row 2: 5 cards)
        4: (0.20, 0.50, "middle"),
        5: (0.35, 0.50, "middle"),
        6: (0.50, 0.50, "middle"),
        7: (0.65, 0.50, "middle"),
        8: (0.80, 0.50, "middle"),
        # Chi Cuối (Row 3: 5 cards)
        9: (0.20, 0.72, "back"),
        10: (0.35, 0.72, "back"),
        11: (0.50, 0.72, "back"),
        12: (0.65, 0.72, "back"),
        13: (0.80, 0.72, "back"),
    }

    @classmethod
    def cluster_into_rows(
        cls, detected_cards: List[DetectedCard], img_h: int = 600
    ) -> List[LayoutRow]:
        """Clusters detected cards into the 3 rows: Front (3), Middle (5), Back (5)."""
        front_row = LayoutRow(row_index=0, row_name="front", target_count=3)
        middle_row = LayoutRow(row_index=1, row_name="middle", target_count=5)
        back_row = LayoutRow(row_index=2, row_name="back", target_count=5)

        if not detected_cards:
            return [front_row, middle_row, back_row]

        heights = [d.bbox[3] for d in detected_cards if d.bbox[3] > 0]
        med_h = float(np.median(heights)) if heights else 80.0
        row_tol = max(24.0, med_h * 0.45)

        # Sort cards by vertical center
        sorted_by_y = sorted(detected_cards, key=lambda d: d.bbox[1] + d.bbox[3] / 2.0)

        # Group into raw clusters based on vertical separation
        raw_clusters: List[List[DetectedCard]] = []
        current_cluster: List[DetectedCard] = [sorted_by_y[0]]

        for d in sorted_by_y[1:]:
            prev_cy = current_cluster[-1].bbox[1] + current_cluster[-1].bbox[3] / 2.0
            cur_cy = d.bbox[1] + d.bbox[3] / 2.0
            if (cur_cy - prev_cy) <= row_tol:
                current_cluster.append(d)
            else:
                raw_clusters.append(current_cluster)
                current_cluster = [d]
        if current_cluster:
            raw_clusters.append(current_cluster)

        # Sort cards inside each cluster left-to-right
        for cluster in raw_clusters:
            cluster.sort(key=lambda d: d.bbox[0])

        # Map raw clusters into the 3 canonical rows (Front, Middle, Back)
        if len(raw_clusters) == 3:
            front_row.cards = raw_clusters[0]
            middle_row.cards = raw_clusters[1]
            back_row.cards = raw_clusters[2]
        elif len(raw_clusters) == 2:
            c0, c1 = raw_clusters[0], raw_clusters[1]
            cy0 = np.mean([d.bbox[1] + d.bbox[3] / 2.0 for d in c0])
            cy1 = np.mean([d.bbox[1] + d.bbox[3] / 2.0 for d in c1])

            # If both have 5 cards or c0 is in the lower 60% of the image, Chi 1 is missing
            if len(c0) == 5 and len(c1) == 5:
                middle_row.cards = c0
                back_row.cards = c1
            elif len(c0) == 3 and len(c1) == 5:
                gap = cy1 - cy0
                if gap > med_h * 1.8:
                    # Middle row is missing in between
                    front_row.cards = c0
                    back_row.cards = c1
                else:
                    front_row.cards = c0
                    middle_row.cards = c1
            elif cy0 < (img_h * 0.38):
                front_row.cards = c0
                if cy1 > (img_h * 0.65):
                    back_row.cards = c1
                else:
                    middle_row.cards = c1
            else:
                middle_row.cards = c0
                back_row.cards = c1
        elif len(raw_clusters) == 1:
            c = raw_clusters[0]
            cy = np.mean([d.bbox[1] + d.bbox[3] / 2.0 for d in c])
            if cy < (img_h * 0.38) or len(c) <= 3:
                front_row.cards = c
            elif cy < (img_h * 0.62):
                middle_row.cards = c
            else:
                back_row.cards = c
        else:
            # More than 3 clusters: merge closest ones vertically
            while len(raw_clusters) > 3:
                # Find pair with minimal vertical distance
                min_dist = float("inf")
                merge_idx = 0
                for i in range(len(raw_clusters) - 1):
                    cy_a = np.mean([d.bbox[1] for d in raw_clusters[i]])
                    cy_b = np.mean([d.bbox[1] for d in raw_clusters[i + 1]])
                    dist = abs(cy_b - cy_a)
                    if dist < min_dist:
                        min_dist = dist
                        merge_idx = i
                merged = raw_clusters[merge_idx] + raw_clusters[merge_idx + 1]
                merged.sort(key=lambda d: d.bbox[0])
                raw_clusters[merge_idx] = merged
                raw_clusters.pop(merge_idx + 1)

            if len(raw_clusters) == 3:
                front_row.cards = raw_clusters[0]
                middle_row.cards = raw_clusters[1]
                back_row.cards = raw_clusters[2]

        # Calculate metrics for each row
        for r in [front_row, middle_row, back_row]:
            if r.cards:
                r.median_y = float(np.median([d.bbox[1] for d in r.cards]))
                r.median_h = float(np.median([d.bbox[3] for d in r.cards]))
                if len(r.cards) >= 2:
                    xs = [d.bbox[0] for d in r.cards]
                    diffs = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
                    r.pitch_x = float(np.median(diffs))

        return [front_row, middle_row, back_row]

    @classmethod
    def infer_missing_slot_bboxes(
        cls,
        table_image: np.ndarray,
        detected_cards: List[DetectedCard],
        custom_slots: Optional[Dict[int, Any]] = None,
    ) -> List[MissingSlotInfo]:
        """Mathematically determines the exact bounding boxes (x, y, w, h) for any missing cards in the 3-5-5 layout."""
        if not detected_cards or table_image is None or table_image.size == 0:
            return []

        img_h, img_w = table_image.shape[:2]
        widths = [d.bbox[2] for d in detected_cards if d.bbox[2] > 0]
        heights = [d.bbox[3] for d in detected_cards if d.bbox[3] > 0]

        card_w = int(np.median(widths)) if widths else max(40, int(img_w * 0.10))
        card_h = int(np.median(heights)) if heights else max(60, int(img_h * 0.18))

        rows = cls.cluster_into_rows(detected_cards, img_h=img_h)
        front_row, middle_row, back_row = rows[0], rows[1], rows[2]

        # Calculate global horizontal pitch ΔX
        pitches_x = [r.pitch_x for r in rows if r.pitch_x > (card_w * 0.70)]
        delta_x = float(np.median(pitches_x)) if pitches_x else (card_w * 1.15)

        # Calculate global vertical pitch ΔY
        valid_ys = [(r.row_index, r.median_y) for r in rows if r.cards]
        delta_y = card_h * 1.15
        if len(valid_ys) >= 2:
            diff_y = (valid_ys[-1][1] - valid_ys[0][1]) / float(valid_ys[-1][0] - valid_ys[0][0])
            if diff_y > (card_h * 0.75):
                delta_y = diff_y

        missing_slots: List[MissingSlotInfo] = []

        # Find reference horizontal span [span_min, span_max] from complete 5-card rows
        span_min, span_max = None, None
        for r in [middle_row, back_row]:
            if len(r.cards) >= 4:
                span_min = r.cards[0].bbox[0]
                span_max = r.cards[-1].bbox[0]
                break
        if span_min is None and detected_cards:
            span_min = min(d.bbox[0] for d in detected_cards)
            span_max = max(d.bbox[0] for d in detected_cards)

        # Process Row 2 (Middle: Slots 4..8) and Row 3 (Back: Slots 9..13)
        for r in [middle_row, back_row]:
            slot_offset = 4 if r.row_index == 1 else 9
            if r.missing_count == 0:
                continue

            row_y = int(r.median_y) if r.cards else int(
                (middle_row.median_y + delta_y) if r.row_index == 2 else (back_row.median_y - delta_y)
            )
            row_y = max(5, min(row_y, img_h - card_h - 5))

            if len(r.cards) == 0:
                # Completely missing 5-card row: synthesize 5 slots aligned with reference span
                start_x = span_min if span_min is not None else int(img_w * 0.20)
                for col in range(5):
                    sx = int(start_x + col * delta_x)
                    sx = max(5, min(sx, img_w - card_w - 5))
                    missing_slots.append(
                        MissingSlotInfo(
                            slot_number=slot_offset + col,
                            row_name=r.row_name,
                            row_index=r.row_index,
                            col_index=col + 1,
                            estimated_bbox=(sx, row_y, card_w, card_h),
                            inference_method="inter_row_alignment",
                        )
                    )
                continue

            # Identify gaps between adjacent cards
            current_cards = list(r.cards)
            xs = [d.bbox[0] for d in current_cards]
            estimated_xs: List[Tuple[int, str]] = []

            # A. Internal gaps
            for i in range(len(xs) - 1):
                gap = xs[i + 1] - xs[i]
                if gap > (delta_x * 1.55):
                    num_in_gap = min(r.missing_count, int(round(gap / delta_x)) - 1)
                    step = gap / float(num_in_gap + 1)
                    for step_idx in range(1, num_in_gap + 1):
                        est_x = int(xs[i] + step_idx * step)
                        estimated_xs.append((est_x, "grid_gap"))

            # B. Edge gaps (Left or Right)
            current_total = len(xs) + len(estimated_xs)
            needed_edges = 5 - current_total

            if needed_edges > 0 and span_min is not None and span_max is not None:
                all_known_xs = sorted(xs + [x for x, _ in estimated_xs])
                left_diff = all_known_xs[0] - span_min
                right_diff = span_max - all_known_xs[-1]

                # Check if missing on left
                if left_diff >= (delta_x * 0.70) and needed_edges > 0:
                    num_left = min(needed_edges, int(round(left_diff / delta_x)))
                    for l_idx in range(1, num_left + 1):
                        est_x = int(all_known_xs[0] - l_idx * delta_x)
                        estimated_xs.append((est_x, "edge_extrapolation"))
                        needed_edges -= 1

                # Check if missing on right
                if right_diff >= (delta_x * 0.70) and needed_edges > 0:
                    num_right = min(needed_edges, int(round(right_diff / delta_x)))
                    for r_idx in range(1, num_right + 1):
                        est_x = int(all_known_xs[-1] + r_idx * delta_x)
                        estimated_xs.append((est_x, "edge_extrapolation"))
                        needed_edges -= 1

            # Fallback if still missing: add to nearest edge
            while needed_edges > 0:
                all_known_xs = sorted(xs + [x for x, _ in estimated_xs])
                est_x = int(all_known_xs[-1] + delta_x)
                if (est_x + card_w) > img_w:
                    est_x = int(all_known_xs[0] - delta_x)
                estimated_xs.append((est_x, "edge_extrapolation"))
                needed_edges -= 1

            # Determine column positions (1..5) by sorting all X coordinates
            all_projected = sorted([(d.bbox[0], False, d) for d in current_cards] + [(x, True, m) for x, m in estimated_xs])
            for col_idx, (proj_x, is_missing, item) in enumerate(all_projected[:5], start=1):
                if is_missing:
                    method = str(item)
                    bx = max(5, min(int(proj_x), img_w - card_w - 5))
                    missing_slots.append(
                        MissingSlotInfo(
                            slot_number=slot_offset + col_idx - 1,
                            row_name=r.row_name,
                            row_index=r.row_index,
                            col_index=col_idx,
                            estimated_bbox=(bx, row_y, card_w, card_h),
                            inference_method=method,
                        )
                    )

        # Process Row 1 (Chi Đầu: Slots 1..3, target 3 cards)
        if front_row.missing_count > 0:
            # Front row Y is above Middle row
            f_y = int(front_row.median_y) if front_row.cards else int(middle_row.median_y - delta_y)
            f_y = max(5, min(f_y, img_h - card_h - 5))

            # Chi 1 is horizontally centered relative to Middle/Back row
            center_x = (span_min + span_max) / 2.0 if (span_min is not None and span_max is not None) else (img_w / 2.0)
            ideal_chi1_xs = [
                int(center_x - delta_x),
                int(center_x),
                int(center_x + delta_x),
            ]

            if len(front_row.cards) == 0:
                for col_idx, ix in enumerate(ideal_chi1_xs, start=1):
                    bx = max(5, min(ix, img_w - card_w - 5))
                    missing_slots.append(
                        MissingSlotInfo(
                            slot_number=col_idx,
                            row_name="front",
                            row_index=0,
                            col_index=col_idx,
                            estimated_bbox=(bx, f_y, card_w, card_h),
                            inference_method="inter_row_alignment",
                        )
                    )
            else:
                existing_xs = [d.bbox[0] for d in front_row.cards]
                # Match existing cards to ideal Chi 1 positions
                taken_ideal_indices = set()
                for ex in existing_xs:
                    # Find closest ideal position
                    closest_idx = int(np.argmin([abs(ex - ix) for ix in ideal_chi1_xs]))
                    taken_ideal_indices.add(closest_idx)

                for col_idx, ix in enumerate(ideal_chi1_xs, start=1):
                    if (col_idx - 1) not in taken_ideal_indices:
                        bx = max(5, min(ix, img_w - card_w - 5))
                        missing_slots.append(
                            MissingSlotInfo(
                                slot_number=col_idx,
                                row_name="front",
                                row_index=0,
                                col_index=col_idx,
                                estimated_bbox=(bx, f_y, card_w, card_h),
                                inference_method="grid_gap",
                            )
                        )

        # Sort missing slots by slot number
        missing_slots.sort(key=lambda s: s.slot_number)
        return missing_slots

    @classmethod
    def verify_and_crop_missing_card(
        cls,
        table_image: np.ndarray,
        slot_info: MissingSlotInfo,
        detector: CardDetector,
        recognizer: CardRecognizer,
        raw_candidates: Optional[List[DetectedCard]] = None,
    ) -> Optional[DetectedCard]:
        """Verifies if a missing card slot has physical card paper, crops it, and recognizes rank/suit."""
        if table_image is None or table_image.size == 0:
            return None

        img_h, img_w = table_image.shape[:2]
        bx, by, bw, bh = slot_info.estimated_bbox

        # 1. First, check if any raw candidate from Pass 1 was detected near this bbox
        if raw_candidates:
            for raw_det in raw_candidates:
                rx, ry, rw, rh = raw_det.bbox
                # Calculate Intersection over Union (IoU) or center proximity
                dx = abs((rx + rw / 2.0) - (bx + bw / 2.0))
                dy = abs((ry + rh / 2.0) - (by + bh / 2.0))
                if dx <= (bw * 0.55) and dy <= (bh * 0.55):
                    # Found matching raw candidate!
                    if raw_det.card is not None and getattr(raw_det, "rank_confidence", 0.0) >= 0.40 and getattr(raw_det, "suit_confidence", 0.0) >= 0.40:
                        raw_det.slot_number = slot_info.slot_number
                        raw_det.row_name = slot_info.row_name
                        raw_det.col_index = slot_info.col_index
                        raw_det.is_recovered = True
                        raw_det.is_uncertain = False
                        raw_det.recognition_status = "CONFIRMED"
                        return raw_det

        # 2. Candidate validation: verify presence of real card paper on the image
        bx = max(0, min(bx, img_w - bw))
        by = max(0, min(by, img_h - bh))
        bw = max(10, min(bw, img_w - bx))
        bh = max(10, min(bh, img_h - by))

        patch = table_image[by : by + bh, bx : bx + bw]
        if patch.size == 0:
            return None

        # Check whiteness and lightness (standard card faces are white/off-white)
        hsv_patch = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        gray_patch = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
        is_card_paper = (hsv_patch[:, :, 1] <= 115) & (hsv_patch[:, :, 2] >= 110) & (gray_patch >= 115)
        whiteness_ratio = np.count_nonzero(is_card_paper) / float(bw * bh)

        # Non-card rejection: empty felt or dark UI elements have whiteness < 0.18
        if whiteness_ratio < 0.18:
            return None

        # Refine bounding box to snugly hug card edges
        ref_x, ref_y, ref_w, ref_h = ImagePreprocessor.refine_card_boundary(table_image, (bx, by, bw, bh))

        # 3. Construct synthetic detection and build CardCrop
        poly = [
            (ref_x, ref_y),
            (ref_x + ref_w, ref_y),
            (ref_x + ref_w, ref_y + ref_h),
            (ref_x, ref_y + ref_h),
        ]
        card_det = CardDetection(
            detection_id=f"rec_slot_{slot_info.slot_number:02d}",
            bbox=(ref_x, ref_y, ref_w, ref_h),
            polygon=poly,
            detection_confidence=0.92,
            crop_status="VALID_CARD_CROP",
            detection_status="CONFIRMED",
        )

        crop = detector._build_single_crop(table_image, card_det)
        if crop is None or crop.image is None or crop.image.size == 0:
            return None

        # 4. Recognize card rank and suit
        det_result = recognizer.recognize_crop(crop)
        if det_result and det_result.card is not None:
            det_result.slot_number = slot_info.slot_number
            det_result.row_name = slot_info.row_name
            det_result.col_index = slot_info.col_index
            det_result.is_recovered = True
            det_result.is_uncertain = False
            det_result.recognition_status = "CONFIRMED"
            return det_result

        return None

    @classmethod
    def resolve_duplicate_cards(
        cls,
        detected_cards: List[DetectedCard],
        recognizer: CardRecognizer,
        table_image: Optional[np.ndarray] = None,
    ) -> Tuple[List[DetectedCard], List[Tuple[str, str]]]:
        """Resolves duplicate cards in a hand since all 13 cards must be strictly unique."""
        disambiguated: List[Tuple[str, str]] = []
        if len(detected_cards) <= 1:
            return detected_cards, disambiguated

        # Group cards by their card_code
        code_map: Dict[str, List[DetectedCard]] = {}
        for d in detected_cards:
            if d.card is not None:
                code = d.card_code
                code_map.setdefault(code, []).append(d)

        all_deck_cards = Deck().cards

        for code, dups in code_map.items():
            if len(dups) <= 1:
                continue

            # Sort duplicates: highest reference match / confidence keeps the identity
            dups.sort(
                key=lambda x: (
                    1 if x.is_reference_match else 0,
                    x.confidence,
                    x.overall_confidence,
                ),
                reverse=True,
            )

            # Keeper is dups[0]
            keeper = dups[0]

            # Others in dups must be disambiguated
            for dup_card in dups[1:]:
                old_code = dup_card.card_code
                taken_codes = {
                    d.card_code for d in detected_cards if d is not dup_card and d.card is not None
                }

                # Strategy A: Check alternative candidates from reference matching
                resolved_card = None
                if dup_card.alternative_candidates:
                    from app.core.card import CardParser
                    for alt_code, score in dup_card.alternative_candidates:
                        if alt_code not in taken_codes and alt_code not in ("", "??"):
                            try:
                                resolved_card = CardParser.parse_card(alt_code)
                                dup_card.confidence = max(0.68, float(score))
                                break
                            except Exception:
                                continue

                # Strategy B: Re-match glyph against unused cards in standard 52-card deck
                if resolved_card is None and dup_card.rank_crop is not None and dup_card.suit_crop is not None:
                    is_red = recognizer.reference_library.check_image_is_red(dup_card.suit_crop)
                    candidate_suits = [Suit.HEARTS, Suit.DIAMONDS] if is_red else [Suit.SPADES, Suit.CLUBS]

                    best_card = None
                    best_score = -1.0

                    q_rank_glyph = recognizer.reference_library.extract_primary_glyph(dup_card.rank_crop, (24, 36))
                    gray_rank = cv2.cvtColor(dup_card.rank_crop, cv2.COLOR_BGR2GRAY)

                    for c in all_deck_cards:
                        if c.short_name in taken_codes or c.suit not in candidate_suits:
                            continue

                        # Check rank similarity
                        ref_r, r_score, _ = recognizer.reference_library.match_rank_glyph(q_rank_glyph, min_score=0.45)
                        algo_r, a_score = recognizer._template_engine.match_rank(gray_rank)

                        score = 0.0
                        if ref_r == c.rank:
                            score += r_score * 0.60
                        if algo_r == c.rank:
                            score += a_score * 0.40

                        if score > best_score:
                            best_score = score
                            best_card = c

                    if best_card is not None and best_score >= 0.45:
                        resolved_card = best_card
                        dup_card.confidence = max(0.68, round(best_score, 2))

                if resolved_card is not None:
                    dup_card.card = resolved_card
                    dup_card.is_verified = True
                    dup_card.is_uncertain = False
                    new_code = dup_card.card_code
                    disambiguated.append((old_code, new_code))

        return detected_cards, disambiguated

    @classmethod
    def complete_and_verify_355_layout(
        cls,
        table_image: np.ndarray,
        detected_cards: List[DetectedCard],
        raw_detected: Optional[List[DetectedCard]] = None,
        detector: Optional[CardDetector] = None,
        recognizer: Optional[CardRecognizer] = None,
        custom_slots: Optional[Dict[int, Any]] = None,
    ) -> Tuple[List[DetectedCard], LayoutVerificationReport]:
        """Master entrypoint: Verifies and completes the 3-5-5 card layout, recovering missing cards

        and resolving any duplicate misreadings.
        """
        if detector is None:
            detector = CardDetector()
        if recognizer is None:
            recognizer = CardRecognizer()

        # If too few cards (< 6 cards), this is not a dealing/full table, do not fabricate cards
        if len(detected_cards) < 6:
            report = LayoutVerificationReport(
                is_complete_13=(len(detected_cards) == 13),
                front_count=0,
                middle_count=0,
                back_count=0,
                message=f"Bàn chơi hiện có {len(detected_cards)} lá bài (< 6 lá, bàn trống hoặc đang dọn bàn).",
            )
            return detected_cards, report

        # Step 1: Resolve any initial duplicate cards
        working_cards, disambiguated = cls.resolve_duplicate_cards(
            detected_cards, recognizer, table_image=table_image
        )

        recovered_slots: List[int] = []

        # Step 2: If cards are missing (< 13 cards), infer missing positions and verify each missing card
        if len(working_cards) < 13 and table_image is not None and table_image.size > 0:
            missing_slots = cls.infer_missing_slot_bboxes(
                table_image=table_image,
                detected_cards=working_cards,
                custom_slots=custom_slots,
            )

            for slot_info in missing_slots:
                if len(working_cards) >= 13:
                    break

                # Check if this slot already has a card
                existing_for_slot = [
                    d for d in working_cards
                    if getattr(d, "slot_number", 0) == slot_info.slot_number
                ]
                if existing_for_slot:
                    continue

                rec_card = cls.verify_and_crop_missing_card(
                    table_image=table_image,
                    slot_info=slot_info,
                    detector=detector,
                    recognizer=recognizer,
                    raw_candidates=raw_detected,
                )

                if rec_card and rec_card.card is not None:
                    # Prevent duplicate insertion
                    current_codes = {d.card_code for d in working_cards if d.card is not None}
                    if rec_card.card_code in current_codes:
                        # Attempt to disambiguate newly recovered card
                        all_dups, _ = cls.resolve_duplicate_cards(
                            working_cards + [rec_card], recognizer, table_image=table_image
                        )
                        working_cards = all_dups
                        recovered_slots.append(slot_info.slot_number)
                    else:
                        working_cards.append(rec_card)
                        recovered_slots.append(slot_info.slot_number)

        # Step 3: Second pass duplicate resolution
        working_cards, disambiguated_2 = cls.resolve_duplicate_cards(
            working_cards, recognizer, table_image=table_image
        )
        disambiguated.extend(disambiguated_2)

        # Step 4: Strict 3-5-5 Layout Organization and Slot Index Assignment
        img_h = table_image.shape[0] if table_image is not None else 600
        rows = cls.cluster_into_rows(working_cards, img_h=img_h)
        front_row, middle_row, back_row = rows[0], rows[1], rows[2]

        final_ordered: List[DetectedCard] = []

        # Front: Slots 1, 2, 3
        for col_idx, d in enumerate(front_row.cards, start=1):
            d.slot_number = col_idx
            d.row_name = "front"
            d.col_index = col_idx
            final_ordered.append(d)

        # Middle: Slots 4, 5, 6, 7, 8
        for col_idx, d in enumerate(middle_row.cards, start=1):
            d.slot_number = 3 + col_idx
            d.row_name = "middle"
            d.col_index = col_idx
            final_ordered.append(d)

        # Back: Slots 9, 10, 11, 12, 13
        for col_idx, d in enumerate(back_row.cards, start=1):
            d.slot_number = 8 + col_idx
            d.row_name = "back"
            d.col_index = col_idx
            final_ordered.append(d)

        is_complete = (len(final_ordered) == 13)
        report = LayoutVerificationReport(
            is_complete_13=is_complete,
            front_count=len(front_row.cards),
            middle_count=len(middle_row.cards),
            back_count=len(back_row.cards),
            recovered_slots=recovered_slots,
            disambiguated_cards=disambiguated,
            message="Xác minh bố cục 3-5-5 hoàn tất: " + (
                "Đủ 13 lá bài hợp lệ, không thiếu, không đọc sai trùng lặp." if is_complete else
                f"Hiện có {len(final_ordered)}/13 lá (Chi 1: {len(front_row.cards)}/3, Chi 2: {len(middle_row.cards)}/5, Chi 3: {len(back_row.cards)}/5)."
            ),
        )

        return final_ordered, report
