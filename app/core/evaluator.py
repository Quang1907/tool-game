"""Hand Evaluator module for Binh 13 (Mậu Binh / Chinese Poker).

Evaluates 3-card front hands and 5-card middle/back hands according to standard
poker ranking hierarchy and Chinese Poker rules with full tie-breaking.
"""

from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from enum import IntEnum
from typing import Sequence
from app.core.card import Card, Rank, Suit


class HandCategory(IntEnum):
    """Rank category of a poker hand, ordered from weakest to strongest."""
    HIGH_CARD = 1           # Mậu thầu
    ONE_PAIR = 2            # Một đôi
    TWO_PAIR = 3            # Hai đôi (Thú) - chỉ có ở 5 lá
    THREE_OF_A_KIND = 4     # Sám cô
    STRAIGHT = 5            # Sảnh - chỉ có ở 5 lá
    FLUSH = 6               # Thùng - chỉ có ở 5 lá
    FULL_HOUSE = 7          # Cù lũ - chỉ có ở 5 lá
    FOUR_OF_A_KIND = 8      # Tứ quý - chỉ có ở 5 lá
    STRAIGHT_FLUSH = 9      # Thùng phá sảnh - chỉ có ở 5 lá

    @property
    def vietnamese_name(self) -> str:
        names = {
            HandCategory.HIGH_CARD: "Mậu thầu",
            HandCategory.ONE_PAIR: "Một đôi",
            HandCategory.TWO_PAIR: "Hai đôi (Thú)",
            HandCategory.THREE_OF_A_KIND: "Sám cô",
            HandCategory.STRAIGHT: "Sảnh",
            HandCategory.FLUSH: "Thùng",
            HandCategory.FULL_HOUSE: "Cù lũ",
            HandCategory.FOUR_OF_A_KIND: "Tứ quý",
            HandCategory.STRAIGHT_FLUSH: "Thùng phá sảnh",
        }
        return names[self]


@dataclass(frozen=True, slots=True)
class HandEvaluation:
    """Immutable evaluation result of a 3-card or 5-card hand.

    Attributes:
        category: HandCategory enum value.
        tie_breakers: Tuple of integer values used for lexicographical comparison
                      within the same category.
        cards: The evaluated cards sorted for display.
        description: Human-readable description (e.g. 'Cù lũ Át già', 'Đôi 10').
        is_front_hand: True if this represents a 3-card front hand.
    """
    category: HandCategory
    tie_breakers: tuple[int, ...]
    cards: tuple[Card, ...]
    description: str
    is_front_hand: bool = False

    @property
    def score_tuple(self) -> tuple[int, ...]:
        """Comparable representation for ordering hands within the same size."""
        return (self.category.value,) + self.tie_breakers

    def __lt__(self, other: HandEvaluation) -> bool:
        if not isinstance(other, HandEvaluation):
            return NotImplemented
        return self.score_tuple < other.score_tuple

    def __le__(self, other: HandEvaluation) -> bool:
        if not isinstance(other, HandEvaluation):
            return NotImplemented
        return self.score_tuple <= other.score_tuple

    def __gt__(self, other: HandEvaluation) -> bool:
        if not isinstance(other, HandEvaluation):
            return NotImplemented
        return self.score_tuple > other.score_tuple

    def __ge__(self, other: HandEvaluation) -> bool:
        if not isinstance(other, HandEvaluation):
            return NotImplemented
        return self.score_tuple >= other.score_tuple

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HandEvaluation):
            return False
        return self.score_tuple == other.score_tuple

    def __repr__(self) -> str:
        cards_str = " ".join(c.short_name for c in self.cards)
        return f"<HandEval: {self.description} ({cards_str})>"


class Evaluator:
    """Evaluates 3-card and 5-card poker hands and verifies validity against foul rules."""

    @staticmethod
    def evaluate_front(cards: Sequence[Card]) -> HandEvaluation:
        """Evaluates a 3-card Front Hand (Chi Đầu).

        Possible categories:
        - THREE_OF_A_KIND (Sám cô): e.g. A-A-A
        - ONE_PAIR (Đôi): e.g. K-K-9
        - HIGH_CARD (Mậu thầu): e.g. Q-J-7
        """
        if len(cards) != 3:
            raise ValueError(f"Front hand must contain exactly 3 cards, got {len(cards)}")

        ranks = sorted([c.rank.value for c in cards], reverse=True)
        counts = Counter(ranks).most_common()

        # Sorted cards for consistent display
        sorted_cards = tuple(sorted(cards, reverse=True))

        # Check Three of a Kind
        if counts[0][1] == 3:
            trip_rank = counts[0][0]
            rank_name = Rank(trip_rank).char
            return HandEvaluation(
                category=HandCategory.THREE_OF_A_KIND,
                tie_breakers=(trip_rank,),
                cards=sorted_cards,
                description=f"Sám {rank_name}",
                is_front_hand=True,
            )

        # Check One Pair
        if counts[0][1] == 2:
            pair_rank = counts[0][0]
            kicker = counts[1][0]
            pair_name = Rank(pair_rank).char
            kicker_name = Rank(kicker).char
            return HandEvaluation(
                category=HandCategory.ONE_PAIR,
                tie_breakers=(pair_rank, kicker),
                cards=sorted_cards,
                description=f"Đôi {pair_name} (kicker {kicker_name})",
                is_front_hand=True,
            )

        # High Card
        high_name = Rank(ranks[0]).char
        return HandEvaluation(
            category=HandCategory.HIGH_CARD,
            tie_breakers=tuple(ranks),
            cards=sorted_cards,
            description=f"Mậu thầu {high_name} cao",
            is_front_hand=True,
        )

    @staticmethod
    def evaluate_five(cards: Sequence[Card], wheel_rule: str = "LOWEST") -> HandEvaluation:
        """Evaluates a 5-card hand (Chi Giữa or Chi Cuối).

        wheel_rule options:
        - 'LOWEST': A-2-3-4-5 is 5-high straight (standard).
        - 'SECOND_HIGHEST': A-2-3-4-5 ranks just below A-K-Q-J-10.
        """
        if len(cards) != 5:
            raise ValueError(f"5-card hand must contain exactly 5 cards, got {len(cards)}")

        ranks = sorted([c.rank.value for c in cards], reverse=True)
        suits = [c.suit for c in cards]
        is_flush = len(set(suits)) == 1

        # Check straight
        is_straight = False
        straight_high = 0

        # Standard consecutive ranks check: e.g. [14, 13, 12, 11, 10]
        if len(set(ranks)) == 5:
            if ranks[0] - ranks[4] == 4:
                is_straight = True
                straight_high = ranks[0]
            elif ranks == [14, 5, 4, 3, 2]:
                # Wheel straight (A-2-3-4-5)
                is_straight = True
                straight_high = 5 if wheel_rule == "LOWEST" else 13.5  # Just below King-high (13) or Ace-high

        sorted_cards = tuple(sorted(cards, reverse=True))

        # 1. Straight Flush
        if is_flush and is_straight:
            high_name = "Thượng (A)" if straight_high == 14 else Rank(int(straight_high)).char
            return HandEvaluation(
                category=HandCategory.STRAIGHT_FLUSH,
                tie_breakers=(int(straight_high * 2),),
                cards=sorted_cards,
                description=f"Thùng phá sảnh ({high_name} cao)",
                is_front_hand=False,
            )

        counts = Counter(ranks).most_common()

        # 2. Four of a Kind (Tứ Quý)
        if counts[0][1] == 4:
            quad_rank = counts[0][0]
            kicker = counts[1][0]
            return HandEvaluation(
                category=HandCategory.FOUR_OF_A_KIND,
                tie_breakers=(quad_rank, kicker),
                cards=sorted_cards,
                description=f"Tứ quý {Rank(quad_rank).char}",
                is_front_hand=False,
            )

        # 3. Full House (Cù Lũ)
        if counts[0][1] == 3 and counts[1][1] == 2:
            trip_rank = counts[0][0]
            pair_rank = counts[1][0]
            return HandEvaluation(
                category=HandCategory.FULL_HOUSE,
                tie_breakers=(trip_rank, pair_rank),
                cards=sorted_cards,
                description=f"Cù lũ {Rank(trip_rank).char} và {Rank(pair_rank).char}",
                is_front_hand=False,
            )

        # 4. Flush (Thùng)
        if is_flush:
            high_name = Rank(ranks[0]).char
            return HandEvaluation(
                category=HandCategory.FLUSH,
                tie_breakers=tuple(ranks),
                cards=sorted_cards,
                description=f"Thùng ({high_name} cao)",
                is_front_hand=False,
            )

        # 5. Straight (Sảnh)
        if is_straight:
            high_name = "A" if straight_high == 14 else ("5" if straight_high == 5 else Rank(int(straight_high)).char)
            return HandEvaluation(
                category=HandCategory.STRAIGHT,
                tie_breakers=(int(straight_high * 2),),
                cards=sorted_cards,
                description=f"Sảnh ({high_name} cao)",
                is_front_hand=False,
            )

        # 6. Three of a Kind (Sám Cô)
        if counts[0][1] == 3:
            trip_rank = counts[0][0]
            kickers = sorted([counts[1][0], counts[2][0]], reverse=True)
            return HandEvaluation(
                category=HandCategory.THREE_OF_A_KIND,
                tie_breakers=(trip_rank, kickers[0], kickers[1]),
                cards=sorted_cards,
                description=f"Sám {Rank(trip_rank).char}",
                is_front_hand=False,
            )

        # 7. Two Pair (Hai Đôi / Thú)
        if counts[0][1] == 2 and counts[1][1] == 2:
            pairs = sorted([counts[0][0], counts[1][0]], reverse=True)
            kicker = counts[2][0]
            return HandEvaluation(
                category=HandCategory.TWO_PAIR,
                tie_breakers=(pairs[0], pairs[1], kicker),
                cards=sorted_cards,
                description=f"Hai đôi {Rank(pairs[0]).char} và {Rank(pairs[1]).char}",
                is_front_hand=False,
            )

        # 8. One Pair (Một Đôi)
        if counts[0][1] == 2:
            pair_rank = counts[0][0]
            kickers = sorted([counts[1][0], counts[2][0], counts[3][0]], reverse=True)
            return HandEvaluation(
                category=HandCategory.ONE_PAIR,
                tie_breakers=(pair_rank, kickers[0], kickers[1], kickers[2]),
                cards=sorted_cards,
                description=f"Đôi {Rank(pair_rank).char}",
                is_front_hand=False,
            )

        # 9. High Card (Mậu Thầu)
        high_name = Rank(ranks[0]).char
        return HandEvaluation(
            category=HandCategory.HIGH_CARD,
            tie_breakers=tuple(ranks),
            cards=sorted_cards,
            description=f"Mậu thầu {high_name} cao",
            is_front_hand=False,
        )

    @classmethod
    def evaluate(cls, cards: Sequence[Card], wheel_rule: str = "LOWEST") -> HandEvaluation:
        """Dispatches evaluation based on card count (3 or 5)."""
        if len(cards) == 3:
            return cls.evaluate_front(cards)
        elif len(cards) == 5:
            return cls.evaluate_five(cards, wheel_rule)
        raise ValueError(f"Only 3-card or 5-card hands can be evaluated, received {len(cards)}")

    @classmethod
    def is_front_stronger_than_five(cls, front: HandEvaluation, five: HandEvaluation) -> bool:
        """Determines if a 3-card Front Hand is strictly stronger than a 5-card hand.

        In Binh 13, if Front > Middle or Middle > Back, the hand is Foul (Binh Lủng).
        """
        # If five has Two Pair, Straight, Flush, Full House, Quads, or Straight Flush:
        # It is strictly stronger than any 3-card hand (which can only have at most Three of a Kind).
        if five.category.value > HandCategory.THREE_OF_A_KIND.value:
            return False

        # If front has higher category than five:
        # e.g. Front has Three of a Kind and five has Pair or High Card:
        if front.category.value > five.category.value:
            return True

        # If front has lower category than five:
        # e.g. Front has High Card and five has Three of a Kind or Pair:
        if front.category.value < five.category.value:
            return False

        # If both have the same category (THREE_OF_A_KIND, ONE_PAIR, or HIGH_CARD):
        if front.category == HandCategory.THREE_OF_A_KIND:
            # Compare trip rank: front.tie_breakers[0] vs five.tie_breakers[0]
            return front.tie_breakers[0] > five.tie_breakers[0]

        if front.category == HandCategory.ONE_PAIR:
            # Compare pair rank
            if front.tie_breakers[0] != five.tie_breakers[0]:
                return front.tie_breakers[0] > five.tie_breakers[0]
            # Same pair rank: compare front's single kicker against five's highest kicker
            return front.tie_breakers[1] > five.tie_breakers[1]

        # Both are High Card: compare highest cards
        # Front has 3 kickers, five has 5 kickers. Compare the top cards that both have.
        for r_f, r_5 in zip(front.tie_breakers, five.tie_breakers):
            if r_f != r_5:
                return r_f > r_5
        return False

    @classmethod
    def is_foul(
        cls,
        front_eval: HandEvaluation,
        middle_eval: HandEvaluation,
        back_eval: HandEvaluation,
    ) -> bool:
        """Checks if hand arrangement violates the Binh 13 hierarchy rule:

        Requirement for legal hand:
            Back Hand >= Middle Hand >= Front Hand.
        Returns:
            True if FOUL (Lủng / Binh lủng), False if LEGAL.
        """
        # 1. Back hand must be >= Middle hand
        if back_eval < middle_eval:
            return True

        # 2. Middle hand must be >= Front hand
        if cls.is_front_stronger_than_five(front_eval, middle_eval):
            return True

        return False
