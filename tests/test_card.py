"""Unit tests for Card, Deck, Hand, Parser, and Validator."""

import pytest
from app.core.card import Card, Deck, Hand, Rank, Suit, CardParser, CardValidator


class TestCardModel:
    def test_standard_52_cards_creation(self):
        cards = [Card.from_id(i) for i in range(52)]
        assert len(cards) == 52
        assert len(set(cards)) == 52
        # Check first card: 2 of Spades (id 0)
        assert cards[0].rank == Rank.TWO
        assert cards[0].suit == Suit.SPADES
        assert cards[0].short_name == "2s"
        assert cards[0].unicode_name == "2♠"

        # Check last card: Ace of Hearts (id 51)
        assert cards[51].rank == Rank.ACE
        assert cards[51].suit == Suit.HEARTS
        assert cards[51].short_name == "Ah"
        assert cards[51].unicode_name == "A♥"

    def test_card_immutability(self):
        c = Card(Rank.ACE, Suit.SPADES)
        with pytest.raises(AttributeError):
            c.rank = Rank.KING  # type: ignore

    def test_card_comparison(self):
        c_2s = Card(Rank.TWO, Suit.SPADES)
        c_2h = Card(Rank.TWO, Suit.HEARTS)
        c_as = Card(Rank.ACE, Suit.SPADES)
        c_ah = Card(Rank.ACE, Suit.HEARTS)

        assert c_as > c_2s
        assert c_2s < c_as
        assert c_2s < c_2h  # Same rank, compared by suit (Spades < Hearts)
        assert c_ah > c_as
        assert c_as == Card(Rank.ACE, Suit.SPADES)
        assert c_as != c_ah


class TestCardParser:
    def test_parse_valid_cards(self):
        assert CardParser.parse_card("As") == Card(Rank.ACE, Suit.SPADES)
        assert CardParser.parse_card("10h") == Card(Rank.TEN, Suit.HEARTS)
        assert CardParser.parse_card("Th") == Card(Rank.TEN, Suit.HEARTS)
        assert CardParser.parse_card("Kd") == Card(Rank.KING, Suit.DIAMONDS)
        assert CardParser.parse_card("2c") == Card(Rank.TWO, Suit.CLUBS)
        assert CardParser.parse_card("A♠") == Card(Rank.ACE, Suit.SPADES)
        assert CardParser.parse_card("10♥") == Card(Rank.TEN, Suit.HEARTS)

    def test_parse_invalid_cards(self):
        for invalid in ["", "X", "15s", "100h", "Ak", "2z", "hello"]:
            with pytest.raises(ValueError):
                CardParser.parse_card(invalid)

    def test_parse_card_list(self):
        text = "As Kh Qd Jc 10s 9h 8d 7c 6s 5h 4d 3c 2s"
        cards = CardParser.parse_cards(text)
        assert len(cards) == 13
        assert cards[0] == Card(Rank.ACE, Suit.SPADES)
        assert cards[-1] == Card(Rank.TWO, Suit.SPADES)


class TestCardValidator:
    def test_validate_unique_success(self):
        cards = CardParser.parse_cards("As Kh Qd Jc 10s")
        is_valid, msg = CardValidator.validate_unique(cards)
        assert is_valid is True
        assert msg == ""

    def test_validate_duplicate_failure(self):
        cards = CardParser.parse_cards("As Kh As Jc 10s")
        is_valid, msg = CardValidator.validate_unique(cards)
        assert is_valid is False
        assert "Duplicate" in msg

    def test_validate_13_cards(self):
        cards = CardParser.parse_cards("As Kh Qd Jc 10s 9h 8d 7c 6s 5h 4d 3c 2s")
        is_valid, msg = CardValidator.validate_13_cards(cards)
        assert is_valid is True

        # Too few
        is_valid, msg = CardValidator.validate_13_cards(cards[:12])
        assert is_valid is False
        assert "exactly 13 cards" in msg


class TestDeck:
    def test_deck_initialization_and_deal(self):
        deck = Deck()
        assert deck.remaining == 52
        dealt = deck.deal(13)
        assert len(dealt) == 13
        assert deck.remaining == 39

        with pytest.raises(ValueError):
            deck.deal(40)

    def test_deck_shuffle_seed_reproducibility(self):
        deck1 = Deck()
        deck1.shuffle(seed=42)
        cards1 = deck1.deal(13)

        deck2 = Deck()
        deck2.shuffle(seed=42)
        cards2 = deck2.deal(13)

        assert cards1 == cards2

    def test_deck_card_removal(self):
        deck = Deck()
        player_cards = CardParser.parse_cards("As Kh Qd Jc 10s 9h 8d 7c 6s 5h 4d 3c 2s")
        deck.remove(player_cards)
        assert deck.remaining == 39
        remaining_cards = deck.deal(39)
        # Ensure none of the player cards are in remaining
        for c in player_cards:
            assert c not in remaining_cards


class TestHand:
    def test_hand_sorted_descending(self):
        cards = CardParser.parse_cards("2s As 10h Kd")
        hand = Hand(cards)
        assert [c.short_name for c in hand] == ["As", "Kd", "10h", "2s"]

    def test_hand_rejects_duplicates(self):
        cards = CardParser.parse_cards("As As")
        with pytest.raises(ValueError):
            Hand(cards)
