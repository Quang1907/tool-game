"""Game Rules and Scoring Engine for Binh 13 (Mậu Binh / Chinese Poker).

Supports configurable player count, point multipliers, sweep bonuses (Sập 3 chi, Sập làng),
foul penalties, and special instant-win hands (Mậu Binh Thắng Trắng).
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Sequence

from app.core.card import Card, Rank
from app.core.evaluator import HandEvaluation
from app.core.solver import HandArrangement


@dataclass(frozen=True, slots=True)
class HeadToHeadResult:
    """Outcome of comparing one player's arrangement against one opponent."""
    front_outcome: int       # 1 (win), 0 (tie), -1 (loss)
    middle_outcome: int      # 1 (win), 0 (tie), -1 (loss)
    back_outcome: int        # 1 (win), 0 (tie), -1 (loss)
    base_points: float       # Points from individual hand outcomes
    bonus_points: float      # Sweep bonuses or penalties
    total_points: float      # base_points + bonus_points
    is_scoop: bool           # Player won all 3 hands against this opponent
    is_scooped: bool         # Player lost all 3 hands against this opponent


@dataclass
class RuleConfig:
    """Configurable rule definitions for Binh 13."""
    players: int = 4
    hand_size: int = 13
    front_size: int = 3
    middle_size: int = 5
    back_size: int = 5

    point_win_hand: float = 1.0
    point_loss_hand: float = -1.0
    point_tie_hand: float = 0.0

    # Sweep bonuses: winning all 3 hands against an opponent (Sập 3 chi)
    sweep_single_player_bonus: float = 3.0
    # Sweep all opponents at table (Sập làng)
    sweep_all_players_bonus: float = 6.0
    # Penalty for foul hand (Binh lủng)
    foul_penalty_points: float = -12.0

    # Wheel straight rule: 'LOWEST' (A-2-3-4-5 is 5-high) or 'SECOND_HIGHEST'
    wheel_straight_rule: str = "LOWEST"

    # Special hands (Thắng trắng)
    special_hands_enabled: bool = True
    special_hand_scores: dict[str, float] = field(default_factory=lambda: {
        "DRAGON": 26.0,          # Sảnh rồng (A-K-Q-J-10-9-8-7-6-5-4-3-2)
        "SIX_PAIRS": 12.0,       # Lục phé bôn (6 đôi)
        "THREE_STRAIGHTS": 12.0, # Ba sảnh
        "THREE_FLUSHES": 12.0,   # Ba thùng
    })

    @classmethod
    def load_from_file(cls, path: str | Path) -> RuleConfig:
        """Loads configuration from JSON file."""
        file_path = Path(path)
        if not file_path.exists():
            return cls()
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> dict[str, Any]:
        """Serializes configuration to dictionary."""
        return {
            "players": self.players,
            "hand_size": self.hand_size,
            "front_size": self.front_size,
            "middle_size": self.middle_size,
            "back_size": self.back_size,
            "point_win_hand": self.point_win_hand,
            "point_loss_hand": self.point_loss_hand,
            "point_tie_hand": self.point_tie_hand,
            "sweep_single_player_bonus": self.sweep_single_player_bonus,
            "sweep_all_players_bonus": self.sweep_all_players_bonus,
            "foul_penalty_points": self.foul_penalty_points,
            "wheel_straight_rule": self.wheel_straight_rule,
            "special_hands_enabled": self.special_hands_enabled,
            "special_hand_scores": dict(self.special_hand_scores),
        }

    def save_to_file(self, path: str | Path) -> None:
        """Saves configuration to JSON file."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


class RulesEngine:
    """Engine executing comparison and point calculation based on a RuleConfig."""

    def __init__(self, config: RuleConfig | None = None) -> None:
        self.config = config or RuleConfig()

    @staticmethod
    def compare_evaluations(eval_a: HandEvaluation, eval_b: HandEvaluation) -> int:
        """Compares two evaluations of the same size (3-card vs 3-card, or 5-card vs 5-card).

        Returns:
            1 if eval_a beats eval_b
            -1 if eval_b beats eval_a
            0 if tied
        """
        if eval_a > eval_b:
            return 1
        elif eval_a < eval_b:
            return -1
        return 0

    def compare_head_to_head(
        self,
        player: HandArrangement,
        opponent: HandArrangement,
    ) -> HeadToHeadResult:
        """Calculates head-to-head score between player and an opponent."""
        # Check foul hands
        if player.is_foul and opponent.is_foul:
            return HeadToHeadResult(0, 0, 0, 0.0, 0.0, 0.0, False, False)
        elif player.is_foul:
            penalty = self.config.foul_penalty_points
            return HeadToHeadResult(-1, -1, -1, -3.0, penalty + 3.0, penalty, False, True)
        elif opponent.is_foul:
            penalty = abs(self.config.foul_penalty_points)
            return HeadToHeadResult(1, 1, 1, 3.0, penalty - 3.0, penalty, True, False)

        # 1. Front hand comparison (3 vs 3)
        front_res = self.compare_evaluations(player.front_eval, opponent.front_eval)
        # 2. Middle hand comparison (5 vs 5)
        middle_res = self.compare_evaluations(player.middle_eval, opponent.middle_eval)
        # 3. Back hand comparison (5 vs 5)
        back_res = self.compare_evaluations(player.back_eval, opponent.back_eval)

        # Compute base points
        base_points = 0.0
        for res in (front_res, middle_res, back_res):
            if res == 1:
                base_points += self.config.point_win_hand
            elif res == -1:
                base_points += self.config.point_loss_hand
            else:
                base_points += self.config.point_tie_hand

        # Check scoops (Sập 3 chi)
        bonus_points = 0.0
        is_scoop = (front_res == 1 and middle_res == 1 and back_res == 1)
        is_scooped = (front_res == -1 and middle_res == -1 and back_res == -1)

        if is_scoop:
            bonus_points += self.config.sweep_single_player_bonus
        elif is_scooped:
            bonus_points -= self.config.sweep_single_player_bonus

        total = base_points + bonus_points
        return HeadToHeadResult(
            front_outcome=front_res,
            middle_outcome=middle_res,
            back_outcome=back_res,
            base_points=base_points,
            bonus_points=bonus_points,
            total_points=total,
            is_scoop=is_scoop,
            is_scooped=is_scooped,
        )

    @classmethod
    def check_special_hand(cls, cards: Sequence[Card]) -> tuple[str | None, str]:
        """Detects if 13 cards form a special instant-win hand (Mậu Binh Thắng Trắng).

        Returns:
            (hand_type, description) or (None, "")
        """
        if len(cards) != 13:
            return None, ""

        ranks = sorted([c.rank.value for c in cards], reverse=True)
        suits = [c.suit for c in cards]

        # 1. Dragon (Sảnh Rồng: 13 distinct ranks from 2 to Ace)
        if len(set(ranks)) == 13:
            return "DRAGON", "Sảnh Rồng (Dragon: 2 tới A)"

        # 2. Six Pairs (Lục Phé Bôn: 6 distinct pairs)
        from collections import Counter
        counts = Counter(ranks)
        num_pairs = sum(1 for cnt in counts.values() if cnt >= 2)
        if num_pairs == 6:
            return "SIX_PAIRS", "Lục Phé Bôn (6 đôi)"

        return None, ""
