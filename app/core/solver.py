"""Combinatorial Solver for Binh 13 (Mậu Binh / Chinese Poker).

Exhaustively partitions 13 cards into 3 (front), 5 (middle), 5 (back) hands,
filters out all foul hands, and ranks valid arrangements by heuristic strategy.
"""

from __future__ import annotations
from dataclasses import dataclass
import itertools
from typing import Sequence

from app.core.card import Card, CardValidator
from app.core.evaluator import Evaluator, HandCategory, HandEvaluation


@dataclass(frozen=True, slots=True)
class HandArrangement:
    """Represents a specific 13-card arrangement into 3 hands: front, middle, back.

    Attributes:
        front: 3-card front hand.
        middle: 5-card middle hand.
        back: 5-card back hand.
        front_eval: HandEvaluation for front hand.
        middle_eval: HandEvaluation for middle hand.
        back_eval: HandEvaluation for back hand.
        heuristic_score: Initial heuristic rank score.
        is_foul: True if foul, False if strictly legal.
    """
    front: tuple[Card, ...]
    middle: tuple[Card, ...]
    back: tuple[Card, ...]
    front_eval: HandEvaluation
    middle_eval: HandEvaluation
    back_eval: HandEvaluation
    heuristic_score: float = 0.0
    is_foul: bool = False

    @property
    def all_cards(self) -> tuple[Card, ...]:
        return self.front + self.middle + self.back

    def summary_str(self) -> str:
        return (
            f"[Front: {self.front_eval.description}] "
            f"[Mid: {self.middle_eval.description}] "
            f"[Back: {self.back_eval.description}] "
            f"Heuristic: {self.heuristic_score:.1f}"
        )


class Solver:
    """High-performance combinatorial solver for partitioning 13 cards into 3-5-5."""

    TOTAL_RAW_PARTITIONS: int = 36036  # C(13, 3) * C(10, 5) / 2 = 286 * 126

    def __init__(self, wheel_rule: str = "LOWEST") -> None:
        self.wheel_rule = wheel_rule
        # Precompute the 126 complementary partitions of 10 indices (0..9)
        self._ten_index_partitions = self._generate_ten_partitions()

    @staticmethod
    def _generate_ten_partitions() -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
        """Generates the 126 unordered pairs of 5-element subsets from indices 0..9."""
        all_indices = set(range(10))
        pairs = []
        seen_pairs = set()

        for group_a in itertools.combinations(range(10), 5):
            group_b = tuple(sorted(all_indices - set(group_a)))
            pair_key = (min(group_a, group_b), max(group_a, group_b))
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                pairs.append((group_a, group_b))

        return pairs

    def _compute_heuristic_score(
        self,
        front_eval: HandEvaluation,
        middle_eval: HandEvaluation,
        back_eval: HandEvaluation,
        strategy: str = "BALANCED",
    ) -> float:
        """Calculates a heuristic score to rank arrangements prior to Monte Carlo simulation.

        Strategies:
        - 'BALANCED': Standard weighted distribution (Back=1.0, Mid=1.3, Front=1.8).
        - 'FRONT_HEAVY': Prioritizes high front hand to steal front points.
        - 'BACK_HEAVY': Maximizes back hand security.
        - 'MIDDLE_HEAVY': Bolsters the middle hand.
        """
        # Convert evaluation into a normalized float score [0..100]
        def eval_to_val(eval_res: HandEvaluation) -> float:
            base = eval_res.category.value * 10.0
            tie_bonus = 0.0
            if eval_res.tie_breakers:
                # Add fractional bonus from top tie-breakers
                tie_bonus = eval_res.tie_breakers[0] * 0.5
                if len(eval_res.tie_breakers) > 1:
                    tie_bonus += eval_res.tie_breakers[1] * 0.03
            return base + tie_bonus

        f_val = eval_to_val(front_eval)
        m_val = eval_to_val(middle_eval)
        b_val = eval_to_val(back_eval)

        # In Front hand, Three of a Kind is category 4, Pair is category 2.
        # Normalize front hand to be competitively weighted
        if front_eval.category == HandCategory.THREE_OF_A_KIND:
            f_norm = 65.0 + front_eval.tie_breakers[0]
        elif front_eval.category == HandCategory.ONE_PAIR:
            f_norm = 25.0 + front_eval.tie_breakers[0] * 2.0 + front_eval.tie_breakers[1] * 0.1
        else:
            f_norm = front_eval.tie_breakers[0]

        if strategy == "FRONT_HEAVY":
            return b_val * 0.8 + m_val * 1.1 + f_norm * 2.2
        elif strategy == "BACK_HEAVY":
            return b_val * 1.6 + m_val * 1.1 + f_norm * 1.0
        elif strategy == "MIDDLE_HEAVY":
            return b_val * 0.9 + m_val * 1.7 + f_norm * 1.1
        else:  # BALANCED
            return b_val * 1.0 + m_val * 1.3 + f_norm * 1.7

    def solve(
        self,
        cards: Sequence[Card],
        strategy: str = "BALANCED",
        max_results: int | None = None,
    ) -> list[HandArrangement]:
        """Finds and returns all legal (non-foul) hand arrangements, ranked by heuristic score.

        Uses pre-evaluation caching across the 13 cards:
        - Evaluates all C(13, 3) = 286 front subsets.
        - Evaluates all C(13, 5) = 1,287 five-card subsets.
        - Combines them in 36,036 partitions to filter legal hands in milliseconds.
        """
        is_valid, err = CardValidator.validate_13_cards(cards)
        if not is_valid:
            raise ValueError(err)

        card_list = list(cards)

        # 1. Precompute all 286 3-card evaluations indexed by frozenset of card indices
        front_cache: dict[tuple[int, ...], HandEvaluation] = {}
        for indices in itertools.combinations(range(13), 3):
            sub_cards = [card_list[i] for i in indices]
            front_cache[indices] = Evaluator.evaluate_front(sub_cards)

        # 2. Precompute all 1,287 5-card evaluations indexed by tuple of card indices
        five_cache: dict[tuple[int, ...], HandEvaluation] = {}
        for indices in itertools.combinations(range(13), 5):
            sub_cards = [card_list[i] for i in indices]
            five_cache[indices] = Evaluator.evaluate_five(sub_cards, wheel_rule=self.wheel_rule)

        legal_arrangements: list[HandArrangement] = []
        all_13_indices = set(range(13))

        # 3. Iterate over all 286 front choices
        for front_idx_tuple in itertools.combinations(range(13), 3):
            front_eval = front_cache[front_idx_tuple]
            rem_indices = sorted(all_13_indices - set(front_idx_tuple))

            # rem_indices has 10 elements. Use precomputed 126 partitions:
            for part_a_local, part_b_local in self._ten_index_partitions:
                idx_group_a = tuple(sorted(rem_indices[i] for i in part_a_local))
                idx_group_b = tuple(sorted(rem_indices[i] for i in part_b_local))

                eval_a = five_cache[idx_group_a]
                eval_b = five_cache[idx_group_b]

                # Canonically assign Back = max(eval_a, eval_b), Middle = min(eval_a, eval_b)
                if eval_a >= eval_b:
                    back_eval = eval_a
                    back_indices = idx_group_a
                    middle_eval = eval_b
                    middle_indices = idx_group_b
                else:
                    back_eval = eval_b
                    back_indices = idx_group_b
                    middle_eval = eval_a
                    middle_indices = idx_group_a

                # Check foul condition: Middle >= Front
                if not Evaluator.is_front_stronger_than_five(front_eval, middle_eval):
                    # Valid legal arrangement!
                    score = self._compute_heuristic_score(
                        front_eval, middle_eval, back_eval, strategy=strategy
                    )
                    arr = HandArrangement(
                        front=front_eval.cards,
                        middle=middle_eval.cards,
                        back=back_eval.cards,
                        front_eval=front_eval,
                        middle_eval=middle_eval,
                        back_eval=back_eval,
                        heuristic_score=score,
                        is_foul=False,
                    )
                    legal_arrangements.append(arr)

        # Sort descending by heuristic score
        legal_arrangements.sort(key=lambda a: a.heuristic_score, reverse=True)

        if max_results is not None:
            return legal_arrangements[:max_results]
        return legal_arrangements

    def solve_heuristic(
        self,
        cards: Sequence[Card],
        strategy: str = "BALANCED",
        max_results: int | None = None,
    ) -> list[HandArrangement]:
        """Heuristic solver alias returning legal arrangements ranked by strategic weight."""
        return self.solve(cards, strategy=strategy, max_results=max_results)

    def count_total_partitions(self, cards: Sequence[Card]) -> int:
        """Utility method verifying that exactly 36,036 partitions are explored."""
        is_valid, err = CardValidator.validate_13_cards(cards)
        if not is_valid:
            raise ValueError(err)

        count = 0
        all_13_indices = set(range(13))
        for front_idx_tuple in itertools.combinations(range(13), 3):
            rem_indices = sorted(all_13_indices - set(front_idx_tuple))
            for _ in self._ten_index_partitions:
                count += 1
        return count
