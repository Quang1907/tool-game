"""Monte Carlo Simulator for Binh 13 (Mậu Binh / Chinese Poker).

Deals remaining unseen cards to 1-3 opponents, simulates realistic opponent strategies,
and computes detailed head-to-head metrics, EV, variance, and confidence intervals.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
import random
import time
from typing import Sequence

from app.core.card import Card, Deck
from app.core.evaluator import Evaluator, HandEvaluation
from app.core.rules import HeadToHeadResult, RuleConfig, RulesEngine
from app.core.solver import HandArrangement, Solver


@dataclass(frozen=True, slots=True)
class SimulationStats:
    """Comprehensive statistical metrics from a Monte Carlo simulation run."""
    expected_value: float          # Mean total net points per round across all opponents
    win_rate: float                # % of rounds where net score > 0
    tie_rate: float                # % of rounds where net score == 0
    loss_rate: float               # % of rounds where net score < 0
    front_win_rate: float          # % of front hands won against any opponent
    front_tie_rate: float
    front_loss_rate: float
    middle_win_rate: float
    middle_tie_rate: float
    middle_loss_rate: float
    back_win_rate: float
    back_tie_rate: float
    back_loss_rate: float
    scoop_rate: float              # Frequency of winning all 3 hands against an opponent
    scooped_rate: float            # Frequency of losing all 3 hands against an opponent
    variance: float
    std_dev: float
    std_err: float
    ci_95_lower: float
    ci_95_upper: float
    total_rounds: int
    elapsed_seconds: float


class OpponentStrategy(ABC):
    """Abstract interface for opponent arrangement generation."""

    @abstractmethod
    def arrange(self, cards: Sequence[Card]) -> HandArrangement:
        """Arranges 13 cards into a legal HandArrangement."""
        pass


class FastHeuristicOpponent(OpponentStrategy):
    """Blazingly fast opponent that constructs a strong legal arrangement in < 0.2ms."""

    def __init__(self, wheel_rule: str = "LOWEST") -> None:
        self.wheel_rule = wheel_rule
        self._solver = Solver(wheel_rule=self.wheel_rule)

    def arrange(self, cards: Sequence[Card]) -> HandArrangement:
        # Fast path: evaluate 13 sorted cards
        sorted_cards = sorted(cards, reverse=True)

        # 1. Greedy approach:
        # Group cards by suit to check for flushes
        suit_groups: dict[int, list[Card]] = {}
        for c in sorted_cards:
            suit_groups.setdefault(c.suit.value, []).append(c)

        # Check for flush in 13 cards
        flush_cards: list[Card] | None = None
        for s_cards in suit_groups.values():
            if len(s_cards) >= 5:
                flush_cards = s_cards[:5]
                break

        if flush_cards:
            back_cards = tuple(flush_cards)
            rem = [c for c in sorted_cards if c not in back_cards]
            # Try taking best 5 for middle:
            mid_cards = tuple(rem[:5])
            front_cards = tuple(rem[5:8])

            f_eval = Evaluator.evaluate_front(front_cards)
            m_eval = Evaluator.evaluate_five(mid_cards, wheel_rule=self.wheel_rule)
            b_eval = Evaluator.evaluate_five(back_cards, wheel_rule=self.wheel_rule)

            if not Evaluator.is_foul(f_eval, m_eval, b_eval):
                return HandArrangement(
                    front=f_eval.cards, middle=m_eval.cards, back=b_eval.cards,
                    front_eval=f_eval, middle_eval=m_eval, back_eval=b_eval,
                    is_foul=False
                )

        # General path: Top 1 from pre-initialized solver
        arrangements = self._solver.solve(sorted_cards, strategy="BALANCED", max_results=1)
        if arrangements:
            return arrangements[0]

        # Extreme fallback
        f = Evaluator.evaluate_front(sorted_cards[10:13])
        m = Evaluator.evaluate_five(sorted_cards[5:10], wheel_rule=self.wheel_rule)
        b = Evaluator.evaluate_five(sorted_cards[0:5], wheel_rule=self.wheel_rule)
        return HandArrangement(
            front=f.cards, middle=m.cards, back=b.cards,
            front_eval=f, middle_eval=m, back_eval=b,
            is_foul=Evaluator.is_foul(f, m, b)
        )


class MonteCarloSimulator:
    """Monte Carlo engine for simulating games against unseen cards."""

    def __init__(
        self,
        rules_engine: RulesEngine | None = None,
        opponent_strategy: OpponentStrategy | None = None,
    ) -> None:
        self.rules = rules_engine or RulesEngine()
        self.strategy = opponent_strategy or FastHeuristicOpponent()

    def simulate_arrangement(
        self,
        arrangement: HandArrangement,
        player_cards: Sequence[Card],
        num_rounds: int = 1000,
        num_opponents: int = 3,
        seed: int | None = None,
    ) -> SimulationStats:
        """Simulates an arrangement against random opponent deals from unseen cards."""
        start_time = time.perf_counter()

        # Build remaining 39-card deck
        deck = Deck()
        deck.remove(player_cards)
        unseen_cards = deck.cards

        if num_opponents * 13 > len(unseen_cards):
            raise ValueError(
                f"Cannot deal {num_opponents} opponents (requires {num_opponents*13} cards); "
                f"only {len(unseen_cards)} unseen cards remaining"
            )

        rng = random.Random(seed) if seed is not None else random.Random()

        round_scores: list[float] = []
        front_wins = 0
        front_ties = 0
        front_losses = 0
        middle_wins = 0
        middle_ties = 0
        middle_losses = 0
        back_wins = 0
        back_ties = 0
        back_losses = 0
        scoops = 0
        scoopeds = 0
        total_matchups = num_rounds * num_opponents

        for _ in range(num_rounds):
            # Shuffle remaining cards
            rng.shuffle(unseen_cards)

            round_net_score = 0.0

            for opp_idx in range(num_opponents):
                opp_cards = unseen_cards[opp_idx * 13 : (opp_idx + 1) * 13]
                opp_arr = self.strategy.arrange(opp_cards)

                res = self.rules.compare_head_to_head(arrangement, opp_arr)
                round_net_score += res.total_points

                # Track per-hand statistics
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

            round_scores.append(round_net_score)

        elapsed = time.perf_counter() - start_time

        # Compute statistics
        n = len(round_scores)
        mean_ev = sum(round_scores) / n

        wins = sum(1 for s in round_scores if s > 0)
        ties = sum(1 for s in round_scores if s == 0)
        losses = sum(1 for s in round_scores if s < 0)

        # Sample variance & standard error
        if n > 1:
            variance = sum((s - mean_ev) ** 2 for s in round_scores) / (n - 1)
            std_dev = math.sqrt(variance)
            std_err = std_dev / math.sqrt(n)
        else:
            variance = 0.0
            std_dev = 0.0
            std_err = 0.0

        # 95% Confidence Interval (z ~ 1.96)
        ci_lower = mean_ev - 1.96 * std_err
        ci_upper = mean_ev + 1.96 * std_err

        return SimulationStats(
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
            ci_95_lower=ci_lower,
            ci_95_upper=ci_upper,
            total_rounds=n,
            elapsed_seconds=elapsed,
        )
