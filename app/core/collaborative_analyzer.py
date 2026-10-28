"""Collaborative Table Analyzer and Counter-Strategy Engine for Binh 13.

In a 4-player Mậu Binh table, given the 3 hands (39 cards) observed across 3 windows,
this engine mathematically deduces the exact 13 cards remaining in the 52-card deck
for the 4th player (the Opponent), calculates the Opponent's most dangerous arrangement,
and devises the optimal counter-strategy for the 3 friendly windows to defeat/scoop them.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from app.core.card import Card
from app.core.rules import HeadToHeadResult, RulesEngine
from app.core.solver import HandArrangement, Solver


@dataclass(frozen=True, slots=True)
class WindowCounterStrategy:
    """Strategy for a specific window against the deduced opponent."""
    window_idx: int
    optimal_arrangement: HandArrangement
    default_arrangement: HandArrangement
    matchup: HeadToHeadResult
    is_counter_adapted: bool
    score_vs_opponent: float

    @property
    def outcome_summary(self) -> str:
        if self.matchup.is_scoop:
            return "🏆 BẮT SẬP 3 CHI (+6 điểm)"
        elif self.matchup.total_points > 0:
            return f"✓ Thắng (+{self.matchup.total_points:.0f} điểm)"
        elif self.matchup.total_points == 0:
            return " Hòa (0 điểm)"
        elif self.matchup.is_scooped:
            return " Bị Sập 3 Chi (-6 điểm)"
        else:
            return f" Thua ({self.matchup.total_points:.0f} điểm)"

    @property
    def chi_breakdown(self) -> str:
        f = "Thắng" if self.matchup.front_outcome > 0 else ("Hòa" if self.matchup.front_outcome == 0 else "Thua")
        m = "Thắng" if self.matchup.middle_outcome > 0 else ("Hòa" if self.matchup.middle_outcome == 0 else "Thua")
        b = "Thắng" if self.matchup.back_outcome > 0 else ("Hòa" if self.matchup.back_outcome == 0 else "Thua")
        return f"Đầu: {f} | Giữa: {m} | Cuối: {b}"


@dataclass
class CollaborativeTableResult:
    """Result of table-wide analysis for 3 player windows and 1 deduced opponent."""
    total_known_cards: int
    remaining_cards: List[Card]
    is_opponent_fully_deduced: bool
    opponent_best_arrangement: Optional[HandArrangement]
    window_strategies: Dict[int, WindowCounterStrategy] = field(default_factory=dict)
    cross_duplicates: List[Card] = field(default_factory=list)
    total_team_score_vs_opponent: float = 0.0

    @property
    def summary_message(self) -> str:
        if self.cross_duplicates:
            dups = " ".join(c.unicode_name for c in self.cross_duplicates)
            return f"⚠️ Phát hiện quân bài trùng giữa các cửa sổ: {dups}! Vui lòng kiểm tra lại góc nhận diện."
        if not self.is_opponent_fully_deduced:
            return f"Đã phát hiện {self.total_known_cards}/39 lá bài. Còn {len(self.remaining_cards)} lá chưa xuất hiện trong bộ 52 cây."
        scoop_count = sum(1 for s in self.window_strategies.values() if s.matchup.is_scoop)
        win_count = sum(1 for s in self.window_strategies.values() if s.matchup.total_points > 0)
        return (
            f"🎯 ĐÃ KHÓA CHẶT 13 LÁ ĐỐI THỦ! "
            f"Tổng điểm 3 nhà vs Đối thủ: {self.total_team_score_vs_opponent:+.0f} điểm "
            f"({win_count}/3 nhà thắng, {scoop_count} nhà bắt sập)"
        )


class CollaborativeTableAnalyzer:
    """Deduces the 4th opponent hand by card elimination and devises counter-strategies."""

    def __init__(
        self,
        rules_engine: Optional[RulesEngine] = None,
        solver: Optional[Solver] = None,
    ) -> None:
        self.rules_engine = rules_engine or RulesEngine()
        self.solver = solver or Solver()

    def analyze_table(self, window_hands: Dict[int, Sequence[Card]]) -> CollaborativeTableResult:
        """Executes full card deduction and counter-strategy optimization."""
        # 1. Collect cards and detect cross-window duplicates
        all_card_counts: Dict[int, int] = {}
        id_to_card: Dict[int, Card] = {}
        for win_idx, cards in window_hands.items():
            for c in cards:
                all_card_counts[c.card_id] = all_card_counts.get(c.card_id, 0) + 1
                id_to_card[c.card_id] = c

        cross_duplicates = [id_to_card[cid] for cid, cnt in all_card_counts.items() if cnt > 1]
        unique_known_ids = set(all_card_counts.keys())
        total_known_cards = len(unique_known_ids)

        # 2. Compute remaining unseen cards in standard 52-card deck
        all_deck_cards = [Card.from_id(i) for i in range(52)]
        remaining_cards = [c for c in all_deck_cards if c.card_id not in unique_known_ids]
        remaining_cards.sort(reverse=True)

        # Check if opponent is fully deduced: exactly 39 cards across 3 windows with 13 cards each
        has_3_windows_with_13 = all(len(window_hands.get(i, [])) == 13 for i in (1, 2, 3))
        is_opponent_fully_deduced = (
            has_3_windows_with_13
            and len(remaining_cards) == 13
            and not cross_duplicates
        )

        opponent_best: Optional[HandArrangement] = None
        if is_opponent_fully_deduced:
            try:
                opp_arrangements = self.solver.solve(remaining_cards, strategy="BALANCED")
                if opp_arrangements:
                    opponent_best = opp_arrangements[0]
            except Exception:
                opponent_best = None

        # 3. Optimize arrangements for each window
        strategies: Dict[int, WindowCounterStrategy] = {}
        total_team_score = 0.0

        for win_idx in (1, 2, 3):
            cards = list(window_hands.get(win_idx, []))
            if len(cards) != 13:
                continue

            try:
                legal_arrangements = self.solver.solve(cards, strategy="BALANCED")
                if not legal_arrangements:
                    continue
                default_arr = legal_arrangements[0]

                if opponent_best is not None:
                    # Counter-optimization against known opponent arrangement
                    best_arr = default_arr
                    best_matchup = self.rules_engine.compare_head_to_head(default_arr, opponent_best)
                    best_score = best_matchup.total_points * 1000.0 + default_arr.heuristic_score

                    for candidate in legal_arrangements:
                        cand_matchup = self.rules_engine.compare_head_to_head(candidate, opponent_best)
                        cand_score = cand_matchup.total_points * 1000.0 + candidate.heuristic_score
                        if cand_score > best_score:
                            best_score = cand_score
                            best_arr = candidate
                            best_matchup = cand_matchup

                    is_adapted = (best_arr != default_arr)
                    total_team_score += best_matchup.total_points
                    strategies[win_idx] = WindowCounterStrategy(
                        window_idx=win_idx,
                        optimal_arrangement=best_arr,
                        default_arrangement=default_arr,
                        matchup=best_matchup,
                        is_counter_adapted=is_adapted,
                        score_vs_opponent=best_matchup.total_points,
                    )
                else:
                    # No opponent known yet: use standard heuristic
                    neutral_matchup = HeadToHeadResult(0, 0, 0, 0.0, 0.0, 0.0, False, False)
                    strategies[win_idx] = WindowCounterStrategy(
                        window_idx=win_idx,
                        optimal_arrangement=default_arr,
                        default_arrangement=default_arr,
                        matchup=neutral_matchup,
                        is_counter_adapted=False,
                        score_vs_opponent=0.0,
                    )
            except Exception:
                continue

        return CollaborativeTableResult(
            total_known_cards=total_known_cards,
            remaining_cards=remaining_cards,
            is_opponent_fully_deduced=is_opponent_fully_deduced,
            opponent_best_arrangement=opponent_best,
            window_strategies=strategies,
            cross_duplicates=cross_duplicates,
            total_team_score_vs_opponent=total_team_score,
        )
