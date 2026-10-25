"""Card State Manager: Position-invariant state tracking with debouncing and change detection."""

from __future__ import annotations
import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from app.vision.card_recognizer import DetectedCard


@dataclass
class WindowCardState:
    """Represents the recognition and solution state for an individual game window."""
    window_id: int
    detected_cards: List[DetectedCard] = field(default_factory=list)
    card_hash: str = ""
    status: str = "IDLE"  # "IDLE", "OCCLUDED", "UNCERTAIN", "CONFIRMED_13", "MOVED_NO_RECALCULATE"
    solution_report: Optional[str] = None
    last_positions: List[Tuple[int, int, int, int]] = field(default_factory=list)
    stable_count: int = 0
    last_update_ts: float = 0.0


class CardStateManager:
    """Manages independent card states across 3 windows with position invariance."""

    def __init__(self, debounce_frames: int = 2) -> None:
        self.debounce_frames = debounce_frames
        self.states: Dict[int, WindowCardState] = {}

    def get_or_create_state(self, window_id: int) -> WindowCardState:
        if window_id not in self.states:
            self.states[window_id] = WindowCardState(window_id=window_id)
        return self.states[window_id]

    @staticmethod
    def compute_position_invariant_hash(detected_cards: List[DetectedCard]) -> str:
        """Computes SHA-256 hash from sorted card codes, invariant to spatial card positions."""
        valid_codes = sorted([
            d.card_code for d in detected_cards
            if d.card is not None and d.card_code != "??"
        ])
        if not valid_codes:
            return ""
        content = ",".join(valid_codes)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def update_window_cards(
        self, window_id: int, detected_cards: List[DetectedCard], is_occluded: bool = False
    ) -> Tuple[WindowCardState, bool]:
        """Updates window state and determines whether Solver recalculation is required.

        Returns (updated_state, should_recalculate_solver).
        """
        state = self.get_or_create_state(window_id)
        state.last_update_ts = time.time()

        if is_occluded:
            state.status = "OCCLUDED"
            return state, False

        new_hash = self.compute_position_invariant_hash(detected_cards)
        current_positions = [d.bbox for d in detected_cards]

        if not new_hash:
            state.detected_cards = detected_cards
            state.card_hash = ""
            state.status = "IDLE"
            state.stable_count = 0
            return state, False

        # Check if cards are identical to previous state
        if new_hash == state.card_hash:
            # Check if positions moved
            has_moved = False
            if len(current_positions) == len(state.last_positions):
                for (cx, cy, _, _), (lx, ly, _, _) in zip(current_positions, state.last_positions):
                    if abs(cx - lx) > 10 or abs(cy - ly) > 10:
                        has_moved = True
                        break
            else:
                has_moved = True

            state.last_positions = current_positions
            state.detected_cards = detected_cards

            if has_moved:
                state.status = "MOVED_NO_RECALCULATE"
            else:
                state.status = "STABLE_CONFIRMED" if len(detected_cards) == 13 else f"FOUND_{len(detected_cards)}"
            return state, False

        # Card content changed! Increment debounce
        if new_hash != state.card_hash:
            state.card_hash = new_hash
            state.last_positions = current_positions
            state.detected_cards = detected_cards
            state.stable_count = 1

            # Only trigger recalculation if we have exactly 13 unique confirmed cards
            if len(detected_cards) == 13 and all(d.card is not None for d in detected_cards):
                # Check uniqueness
                unique_codes = {d.card_code for d in detected_cards}
                if len(unique_codes) == 13:
                    state.status = "CONFIRMED_13"
                    return state, True

            state.status = f"DETECTED_{len(detected_cards)}_CARDS"
            return state, False

        return state, False
