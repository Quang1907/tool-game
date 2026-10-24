"""Card, Deck, Suit, Rank, Parser and Validator domain models for Binh 13 (Mậu Binh)."""

from __future__ import annotations
from enum import IntEnum
import random
import re
from typing import Iterable, Sequence


class Suit(IntEnum):
    """Card suit enumeration."""
    SPADES = 1      # Bích (s, ♠)
    CLUBS = 2       # Chuồn (c, ♣)
    DIAMONDS = 3    # Rô (d, ♦)
    HEARTS = 4      # Cơ (h, ♥)

    @property
    def symbol(self) -> str:
        symbols = {
            Suit.SPADES: "♠",
            Suit.CLUBS: "♣",
            Suit.DIAMONDS: "♦",
            Suit.HEARTS: "♥",
        }
        return symbols[self]

    @property
    def char(self) -> str:
        chars = {
            Suit.SPADES: "s",
            Suit.CLUBS: "c",
            Suit.DIAMONDS: "d",
            Suit.HEARTS: "h",
        }
        return chars[self]

    @property
    def vietnamese_name(self) -> str:
        names = {
            Suit.SPADES: "Bích",
            Suit.CLUBS: "Chuồn",
            Suit.DIAMONDS: "Rô",
            Suit.HEARTS: "Cơ",
        }
        return names[self]

    @classmethod
    def from_str(cls, val: str) -> Suit:
        val = val.strip().lower()
        mapping = {
            "s": cls.SPADES, "♠": cls.SPADES, "bich": cls.SPADES, "bích": cls.SPADES, "spade": cls.SPADES, "spades": cls.SPADES,
            "c": cls.CLUBS, "♣": cls.CLUBS, "chuon": cls.CLUBS, "chuồn": cls.CLUBS, "tep": cls.CLUBS, "tép": cls.CLUBS, "club": cls.CLUBS, "clubs": cls.CLUBS,
            "d": cls.DIAMONDS, "♦": cls.DIAMONDS, "ro": cls.DIAMONDS, "rô": cls.DIAMONDS, "diamond": cls.DIAMONDS, "diamonds": cls.DIAMONDS,
            "h": cls.HEARTS, "♥": cls.HEARTS, "co": cls.HEARTS, "cơ": cls.HEARTS, "heart": cls.HEARTS, "hearts": cls.HEARTS,
        }
        if val in mapping:
            return mapping[val]
        raise ValueError(f"Unknown suit: '{val}'")


class Rank(IntEnum):
    """Card rank enumeration, valued 2 to 14 (Ace high)."""
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    @property
    def char(self) -> str:
        if self.value <= 9:
            return str(self.value)
        chars = {
            Rank.TEN: "10",
            Rank.JACK: "J",
            Rank.QUEEN: "Q",
            Rank.KING: "K",
            Rank.ACE: "A",
        }
        return chars[self]

    @property
    def vietnamese_name(self) -> str:
        names = {
            Rank.TWO: "2",
            Rank.THREE: "3",
            Rank.FOUR: "4",
            Rank.FIVE: "5",
            Rank.SIX: "6",
            Rank.SEVEN: "7",
            Rank.EIGHT: "8",
            Rank.NINE: "9",
            Rank.TEN: "10",
            Rank.JACK: "Bồi (J)",
            Rank.QUEEN: "Đầm (Q)",
            Rank.KING: "Già (K)",
            Rank.ACE: "Xì (A)",
        }
        return names[self]

    @classmethod
    def from_str(cls, val: str) -> Rank:
        val = val.strip().upper()
        mapping = {
            "2": cls.TWO,
            "3": cls.THREE,
            "4": cls.FOUR,
            "5": cls.FIVE,
            "6": cls.SIX,
            "7": cls.SEVEN,
            "8": cls.EIGHT,
            "9": cls.NINE,
            "10": cls.TEN,
            "T": cls.TEN,
            "J": cls.JACK,
            "Q": cls.QUEEN,
            "K": cls.KING,
            "A": cls.ACE,
            "1": cls.ACE,  # Common alias for Ace
        }
        if val in mapping:
            return mapping[val]
        raise ValueError(f"Unknown rank: '{val}'")


class Card:
    """Immutable representation of a playing card in the standard 52-card deck."""

    __slots__ = ("_rank", "_suit", "_id")

    def __init__(self, rank: Rank, suit: Suit) -> None:
        if not isinstance(rank, Rank):
            raise TypeError(f"rank must be Rank instance, got {type(rank)}")
        if not isinstance(suit, Suit):
            raise TypeError(f"suit must be Suit instance, got {type(suit)}")
        object.__setattr__(self, "_rank", rank)
        object.__setattr__(self, "_suit", suit)
        # Unique integer ID from 0 to 51:
        card_id = (rank.value - 2) * 4 + (suit.value - 1)
        object.__setattr__(self, "_id", card_id)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Card is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Card is immutable")

    @property
    def rank(self) -> Rank:
        return self._rank

    @property
    def suit(self) -> Suit:
        return self._suit

    @property
    def card_id(self) -> int:
        return self._id

    @property
    def short_name(self) -> str:
        """Compact string representation: e.g. 'As', '10h', '2c'."""
        return f"{self._rank.char}{self._suit.char}"

    @property
    def unicode_name(self) -> str:
        """Unicode representation: e.g. 'A♠', '10♥'."""
        return f"{self._rank.char}{self._suit.symbol}"

    @classmethod
    def from_id(cls, card_id: int) -> Card:
        """Create Card from 0..51 integer ID."""
        if not 0 <= card_id <= 51:
            raise ValueError(f"card_id must be in 0..51, got {card_id}")
        rank_val = (card_id // 4) + 2
        suit_val = (card_id % 4) + 1
        return cls(Rank(rank_val), Suit(suit_val))

    def __repr__(self) -> str:
        return f"Card({self.short_name})"

    def __str__(self) -> str:
        return self.unicode_name

    def __hash__(self) -> int:
        return self._id

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Card):
            return self._id == other._id
        return False

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        if self._rank != other._rank:
            return self._rank < other._rank
        return self._suit < other._suit

    def __le__(self, other: object) -> bool:
        return self == other or self < other

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return not (self <= other)

    def __ge__(self, other: object) -> bool:
        return not (self < other)


class CardParser:
    """Parser utility converting string representations into Card instances."""

    _CARD_PATTERN = re.compile(r"^(10|[2-9TJQKA])([sScCdDhH♠♣♦♥]|bich|chuon|tep|ro|co)$", re.IGNORECASE)

    @classmethod
    def parse_card(cls, card_str: str) -> Card:
        """Parses a single card string into a Card.

        Examples: 'As', '10h', 'Th', '2c', 'Kd', 'A♠', '10♥'
        """
        s = card_str.strip()
        if not s:
            raise ValueError("Card string cannot be empty")

        match = cls._CARD_PATTERN.match(s)
        if match:
            rank_part, suit_part = match.groups()
            rank = Rank.from_str(rank_part)
            suit = Suit.from_str(suit_part)
            return Card(rank, suit)

        # Fallback for custom unicode symbols or variations
        if len(s) >= 2:
            rank_part = s[:-1]
            suit_part = s[-1]
            if rank_part.upper() in ("10", "T") or (len(rank_part) == 1 and rank_part.upper() in "23456789JQKA"):
                try:
                    rank = Rank.from_str(rank_part)
                    suit = Suit.from_str(suit_part)
                    return Card(rank, suit)
                except ValueError:
                    pass

        raise ValueError(f"Invalid card format: '{card_str}'")

    @classmethod
    def parse_cards(cls, text: str) -> list[Card]:
        """Parses a string of multiple cards separated by spaces, commas, or delimiters.

        Example: 'As Kh Qd Jc 10s 9h 8d 7c 6s 5h 4d 3c 2s'
        """
        tokens = re.split(r"[\s,;]+", text.strip())
        tokens = [t for t in tokens if t]
        return [cls.parse_card(t) for t in tokens]


class CardValidator:
    """Validation utility for card groups and player hands."""

    @staticmethod
    def validate_unique(cards: Sequence[Card]) -> tuple[bool, str]:
        """Validates that all cards in sequence are unique."""
        seen: set[int] = set()
        for c in cards:
            if c.card_id in seen:
                return False, f"Duplicate card found: {c.unicode_name}"
            seen.add(c.card_id)
        return True, ""

    @staticmethod
    def validate_13_cards(cards: Sequence[Card]) -> tuple[bool, str]:
        """Validates that a hand contains exactly 13 unique cards."""
        if len(cards) != 13:
            return False, f"Hand must contain exactly 13 cards, received {len(cards)}"
        return CardValidator.validate_unique(cards)


class Hand:
    """Immutable collection of cards representing a full hand or a specific chi."""

    def __init__(self, cards: Iterable[Card]) -> None:
        card_list = list(cards)
        is_unique, err = CardValidator.validate_unique(card_list)
        if not is_unique:
            raise ValueError(err)
        # Store sorted descending by rank then suit
        self._cards = tuple(sorted(card_list, reverse=True))

    @property
    def cards(self) -> tuple[Card, ...]:
        return self._cards

    def __len__(self) -> int:
        return len(self._cards)

    def __getitem__(self, idx: int) -> Card:
        return self._cards[idx]

    def __iter__(self):
        return iter(self._cards)

    def __contains__(self, card: Card) -> bool:
        return card in self._cards

    def __repr__(self) -> str:
        cards_str = " ".join(c.short_name for c in self._cards)
        return f"Hand({cards_str})"

    def __str__(self) -> str:
        return " ".join(c.unicode_name for c in self._cards)


class Deck:
    """Standard 52-card deck supporting dealing, shuffling with seed, and card exclusion."""

    def __init__(self) -> None:
        self._cards: list[Card] = [Card.from_id(i) for i in range(52)]
        self._drawn_count: int = 0

    @property
    def cards(self) -> list[Card]:
        return list(self._cards)

    @property
    def remaining(self) -> int:
        return len(self._cards) - self._drawn_count

    def shuffle(self, seed: int | None = None) -> None:
        """Shuffles remaining cards. Optional seed for reproducibility."""
        if seed is not None:
            rng = random.Random(seed)
            # Fisher-Yates shuffle on remaining cards
            rem_cards = self._cards[self._drawn_count:]
            rng.shuffle(rem_cards)
            self._cards[self._drawn_count:] = rem_cards
        else:
            rem_cards = self._cards[self._drawn_count:]
            random.shuffle(rem_cards)
            self._cards[self._drawn_count:] = rem_cards

    def deal(self, count: int = 1) -> list[Card]:
        """Deals count cards from deck."""
        if count > self.remaining:
            raise ValueError(f"Cannot deal {count} cards; only {self.remaining} remaining")
        dealt = self._cards[self._drawn_count : self._drawn_count + count]
        self._drawn_count += count
        return dealt

    def remove(self, cards_to_remove: Iterable[Card]) -> None:
        """Removes specific cards from the deck (e.g. player's 13 known cards).

        This is used to prepare the remaining 39 unseen cards for Monte Carlo simulation.
        """
        remove_ids = {c.card_id for c in cards_to_remove}
        self._cards = [c for c in self._cards if c.card_id not in remove_ids]
        self._drawn_count = 0

    def reset(self) -> None:
        """Resets deck to standard 52 cards."""
        self._cards = [Card.from_id(i) for i in range(52)]
        self._drawn_count = 0
