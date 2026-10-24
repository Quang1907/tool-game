"""Expected Value (EV) Optimizer for Binh 13 (Mậu Binh / Chinese Poker).

Uses Common Random Numbers (CRN) to evaluate and rank candidate hand arrangements
across identical opponent scenarios, minimizing variance and discovering optimal strategies.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
import random
import time
from typing import Callable, Sequence

from app.core.card import Card, Deck
from app.core.rules import RuleConfig, RulesEngine
from app.core.simulator import FastHeuristicOpponent, OpponentStrategy, SimulationStats
from app.core.solver import HandArrangement, Solver


@dataclass(frozen=True, slots=True)
class OptimizedArrangement:
    """Arrangement paired with its empirical Monte Carlo simulation results."""
    rank: int
    arrangement: HandArrangement
    stats: SimulationStats

    @property
    def ev(self) -> float:
        return self.stats.expected_value


class EVOptimizer:
    """Optimizer evaluating candidate arrangements using Common Random Numbers (CRN)."""

    def __init__(
        self,
        rules_engine: RulesEngine | None = None,
        opponent_strategy: OpponentStrategy | None = None,
    ) -> None:
        self.rules = rules_engine or RulesEngine()
        self.strategy = opponent_strategy or FastHeuristicOpponent()

    def optimize(
        self,
        player_cards: Sequence[Card],
        num_candidates: int = 15,
        num_scenarios: int = 500,
        num_opponents: int = 3,
        seed: int | None = 42,
        progress_callback: Callable[[int, int, str], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> list[OptimizedArrangement]:
        """Finds and ranks candidate arrangements by simulated Expected Value (EV).

        Steps:
        1. Solver generates all legal arrangements, filtered down to top `num_candidates` by heuristic.
        2. Pre-generates `num_scenarios` opponent scenarios using CRN.
        3. Simulates each candidate against identical scenarios.
        4. Ranks candidates by empirical EV.
        """
        start_time = time.perf_counter()

        if progress_callback:
            progress_callback(0, 100, "Sinh các phương án xếp bài hợp lệ...")

        # 1. Generate candidate arrangements
        solver = Solver(wheel_rule=self.rules.config.wheel_straight_rule)
        candidates = solver.solve(player_cards, strategy="BALANCED", max_results=num_candidates)

        if not candidates:
            return []

        if progress_callback:
            progress_callback(10, 100, f"Đang tạo {num_scenarios} kịch bản đối thủ (CRN)...")

        # 2. Build unseen deck and pre-generate opponent scenarios
        deck = Deck()
        deck.remove(player_cards)
        unseen_cards = deck.cards

        rng = random.Random(seed) if seed is not None else random.Random()

        # Each scenario is a list of opponent HandArrangements for this round
        scenarios: list[list[HandArrangement]] = []
        for sc_idx in range(num_scenarios):
            if cancel_check and cancel_check():
                return []

            rng.shuffle(unseen_cards)
            round_opponents: list[HandArrangement] = []
            for opp_idx in range(num_opponents):
                opp_deal = unseen_cards[opp_idx * 13 : (opp_idx + 1) * 13]
                opp_arr = self.strategy.arrange(opp_deal)
                round_opponents.append(opp_arr)
            scenarios.append(round_opponents)

        if progress_callback:
            progress_callback(25, 100, f"Đang mô phỏng {len(candidates)} phương án...")

        # 3. Simulate all candidates against identical scenarios
        results: list[OptimizedArrangement] = []
        total_candidates = len(candidates)

        for c_idx, candidate in enumerate(candidates):
            if cancel_check and cancel_check():
                return []

            cand_start = time.perf_counter()
            round_scores: list[float] = []
            front_wins = front_ties = front_losses = 0
            middle_wins = middle_ties = middle_losses = 0
            back_wins = back_ties = back_losses = 0
            scoops = scoopeds = 0
            total_matchups = num_scenarios * num_opponents

            for round_opponents in scenarios:
                net_round = 0.0
                for opp_arr in round_opponents:
                    res = self.rules.compare_head_to_head(candidate, opp_arr)
                    net_round += res.total_points

                    if res.front_outcome == 1:
                        front_wins += 1
                    elif res.front_outcome == -1:
                        front_losses += 1
                    else:
                        front_ties += 1

                    if res.middle_outcome == 1:
                        middle_wins += 1
                    elif res.middle_outcome == -1:
                        middle_losses += 1
                    else:
                        middle_ties += 1

                    if res.back_outcome == 1:
                        back_wins += 1
                    elif res.back_outcome == -1:
                        back_losses += 1
                    else:
                        back_ties += 1

                    if res.is_scoop:
                        scoops += 1
                    elif res.is_scooped:
                        scoopeds += 1

                round_scores.append(net_round)

            cand_elapsed = time.perf_counter() - cand_start
            n = len(round_scores)
            mean_ev = sum(round_scores) / n

            wins = sum(1 for s in round_scores if s > 0)
            ties = sum(1 for s in round_scores if s == 0)
            losses = sum(1 for s in round_scores if s < 0)

            variance = sum((s - mean_ev) ** 2 for s in round_scores) / (n - 1) if n > 1 else 0.0
            std_dev = math.sqrt(variance)
            std_err = std_dev / math.sqrt(n)

            stats = SimulationStats(
                expected_value=mean_ev,
                win_rate=wins / n,
                tie_rate=ties / n,
                loss_rate=losses / n,
                front_win_rate=front_wins / total_matchups,
                front_tie_rate=front_ties / total_matchups,
                front_loss_rate=front_losses / total_matchups,
                middle_win_rate=middle_wins / total_matchups,
                middle_tie_rate=middle_ties / total_matchups,
                middle_loss_rate=middle_losses / total_matchups,
                back_win_rate=back_wins / total_matchups,
                back_tie_rate=back_ties / total_matchups,
                back_loss_rate=back_losses / total_matchups,
                scoop_rate=scoops / total_matchups,
                scooped_rate=scoopeds / total_matchups,
                variance=variance,
                std_dev=std_dev,
                std_err=std_err,
                ci_95_lower=mean_ev - 1.96 * std_err,
                ci_95_upper=mean_ev + 1.96 * std_err,
                total_rounds=n,
                elapsed_seconds=cand_elapsed,
            )

            # Temporary rank 0; will re-assign after sorting
            results.append(OptimizedArrangement(rank=0, arrangement=candidate, stats=stats))

            if progress_callback:
                progress = int(25 + ((c_idx + 1) / total_candidates) * 75)
                progress_callback(
                    progress,
                    100,
                    f"Đã đánh giá phương án {c_idx + 1}/{total_candidates} (EV: {mean_ev:+.2f})...",
                )

        # 4. Sort strictly descending by Expected Value (EV)
        results.sort(key=lambda item: item.stats.expected_value, reverse=True)

        # Re-assign 1-based ranks
        ranked_results = [
            OptimizedArrangement(rank=idx + 1, arrangement=item.arrangement, stats=item.stats)
            for idx, item in enumerate(results)
        ]

        if progress_callback:
            progress_callback(100, 100, f"Hoàn thành tối ưu {len(ranked_results)} phương án!")

        return ranked_results
