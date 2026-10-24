"""Unit tests for Binh 13 Hand Evaluator."""

import pytest
from app.core.card import CardParser
from app.core.evaluator import Evaluator, HandCategory


class TestFrontHandEvaluator:
    def test_three_of_a_kind(self):
        h1 = Evaluator.evaluate_front(CardParser.parse_cards("As Ah Ad"))
        h2 = Evaluator.evaluate_front(CardParser.parse_cards("Ks Kh Kd"))
        assert h1.category == HandCategory.THREE_OF_A_KIND
        assert h2.category == HandCategory.THREE_OF_A_KIND
        assert h1 > h2

    def test_one_pair(self):
        # Higher pair beats lower pair
        h1 = Evaluator.evaluate_front(CardParser.parse_cards("As Ah 2c"))
        h2 = Evaluator.evaluate_front(CardParser.parse_cards("Ks Kh Qd"))
        assert h1.category == HandCategory.ONE_PAIR
        assert h2.category == HandCategory.ONE_PAIR
        assert h1 > h2

        # Same pair, higher kicker wins
        h3 = Evaluator.evaluate_front(CardParser.parse_cards("Ks Kh Jc"))
        assert h2 > h3

        # Identical pair and kicker tie
        h4 = Evaluator.evaluate_front(CardParser.parse_cards("Kc Kd Qs"))
        assert h2 == h4

    def test_high_card(self):
        h1 = Evaluator.evaluate_front(CardParser.parse_cards("As Kd 2c"))
        h2 = Evaluator.evaluate_front(CardParser.parse_cards("As Qd Jc"))
        assert h1.category == HandCategory.HIGH_CARD
        assert h2.category == HandCategory.HIGH_CARD
        assert h1 > h2  # Both have Ace, h1 has King > Queen

        h3 = Evaluator.evaluate_front(CardParser.parse_cards("As Kd 3c"))
        assert h3 > h1  # Both have A and K, h3 has 3 > 2

    def test_category_ordering(self):
        trips = Evaluator.evaluate_front(CardParser.parse_cards("2s 2h 2c"))
        pair = Evaluator.evaluate_front(CardParser.parse_cards("As Ah Kd"))
        high = Evaluator.evaluate_front(CardParser.parse_cards("As Kd Qd"))

        assert trips > pair
        assert pair > high


class TestFiveCardEvaluator:
    def test_category_hierarchy(self):
        sf = Evaluator.evaluate_five(CardParser.parse_cards("9h 8h 7h 6h 5h"))
        quads = Evaluator.evaluate_five(CardParser.parse_cards("Ah As Ac Ad 2s"))
        full_house = Evaluator.evaluate_five(CardParser.parse_cards("Kh Ks Kd 2c 2h"))
        flush = Evaluator.evaluate_five(CardParser.parse_cards("As Qs 10s 7s 2s"))
        straight = Evaluator.evaluate_five(CardParser.parse_cards("9s 8h 7d 6c 5s"))
        trips = Evaluator.evaluate_five(CardParser.parse_cards("Jh Jd Jc As Kd"))
        two_pair = Evaluator.evaluate_five(CardParser.parse_cards("10s 10h 8d 8c As"))
        pair = Evaluator.evaluate_five(CardParser.parse_cards("9s 9h As Kd Qd"))
        high = Evaluator.evaluate_five(CardParser.parse_cards("As Kd Jc 8s 2d"))

        assert sf.category == HandCategory.STRAIGHT_FLUSH
        assert quads.category == HandCategory.FOUR_OF_A_KIND
        assert full_house.category == HandCategory.FULL_HOUSE
        assert flush.category == HandCategory.FLUSH
        assert straight.category == HandCategory.STRAIGHT
        assert trips.category == HandCategory.THREE_OF_A_KIND
        assert two_pair.category == HandCategory.TWO_PAIR
        assert pair.category == HandCategory.ONE_PAIR
        assert high.category == HandCategory.HIGH_CARD

        # Strict hierarchy order
        assert sf > quads > full_house > flush > straight > trips > two_pair > pair > high

    def test_straight_variations(self):
        broadway = Evaluator.evaluate_five(CardParser.parse_cards("As Kh Qd Jc 10s"))
        nine_high = Evaluator.evaluate_five(CardParser.parse_cards("9s 8h 7d 6c 5s"))
        six_high = Evaluator.evaluate_five(CardParser.parse_cards("6s 5h 4d 3c 2s"))
        wheel = Evaluator.evaluate_five(CardParser.parse_cards("As 5h 4d 3c 2s"), wheel_rule="LOWEST")

        assert broadway > nine_high > six_high > wheel

    def test_full_house_tie_breakers(self):
        # Compare trips first
        h1 = Evaluator.evaluate_five(CardParser.parse_cards("7s 7h 7d 2c 2s"))
        h2 = Evaluator.evaluate_five(CardParser.parse_cards("6s 6h 6d As Ah"))
        assert h1 > h2

        # Same trips, compare pair
        h3 = Evaluator.evaluate_five(CardParser.parse_cards("7s 7h 7d 3c 3s"))
        assert h3 > h1

    def test_flush_tie_breakers(self):
        h1 = Evaluator.evaluate_five(CardParser.parse_cards("As Ks Qs Js 9s"))
        h2 = Evaluator.evaluate_five(CardParser.parse_cards("Ah Kh Qh Jh 8h"))
        assert h1 > h2

    def test_two_pair_tie_breakers(self):
        h1 = Evaluator.evaluate_five(CardParser.parse_cards("As Ah 2d 2c Kd"))
        h2 = Evaluator.evaluate_five(CardParser.parse_cards("Ks Kh Qd Qc As"))
        assert h1 > h2  # A-A beats K-K

        h3 = Evaluator.evaluate_five(CardParser.parse_cards("As Ah 2s 2h Qd"))
        assert h1 > h3  # K kicker beats Q kicker


class TestFoulDetection:
    def test_legal_hand(self):
        front = Evaluator.evaluate_front(CardParser.parse_cards("8s 8h 2c"))          # Pair 8
        middle = Evaluator.evaluate_five(CardParser.parse_cards("9s 8c 7d 6h 5s"))      # Straight 9-high
        back = Evaluator.evaluate_five(CardParser.parse_cards("Ks Kh Kd 2d 2s"))        # Full House K over 2

        assert Evaluator.is_foul(front, middle, back) is False

    def test_foul_middle_weaker_than_front(self):
        front = Evaluator.evaluate_front(CardParser.parse_cards("As Ah 2c"))          # Pair A
        middle = Evaluator.evaluate_five(CardParser.parse_cards("Ks Kh 9d 8c 2s"))      # Pair K
        back = Evaluator.evaluate_five(CardParser.parse_cards("Ks Kh Kd 2d 2s"))        # Full House K over 2

        # Middle Pair K < Front Pair A -> FOUL!
        assert Evaluator.is_foul(front, middle, back) is True

    def test_foul_back_weaker_than_middle(self):
        front = Evaluator.evaluate_front(CardParser.parse_cards("8s 8h 2c"))          # Pair 8
        middle = Evaluator.evaluate_five(CardParser.parse_cards("Ks Kh Kd 2d 2s"))      # Full House
        back = Evaluator.evaluate_five(CardParser.parse_cards("9s 8c 7d 6h 5s"))        # Straight

        # Back (Straight) < Middle (Full House) -> FOUL!
        assert Evaluator.is_foul(front, middle, back) is True

    def test_foul_front_trips_middle_pair(self):
        front = Evaluator.evaluate_front(CardParser.parse_cards("2s 2h 2c"))          # Trips 2
        middle = Evaluator.evaluate_five(CardParser.parse_cards("As Ah Kd Qc Jd"))      # Pair A
        back = Evaluator.evaluate_five(CardParser.parse_cards("Ks Kh Kd 3d 3s"))        # Full House

        # Front Trips > Middle Pair -> FOUL!
        assert Evaluator.is_foul(front, middle, back) is True
