"""Unit tests for CollaborativeTableAnalyzer and 4th Hand Deduction Engine."""

import pytest
from app.core.card import Card, CardParser, Deck
from app.core.collaborative_analyzer import CollaborativeTableAnalyzer


class TestCollaborativeTableAnalyzer:
    def test_deduce_exact_13_opponent_cards(self):
        """Simulate dealing a full standard 52-card deck into 4 hands of 13 cards.
        Give Hands 1, 2, 3 to the analyzer and verify Hand 4 is deduced with 100% precision.
        """
        deck = Deck()
        deck.shuffle(seed=42)

        hand_1 = deck.deal(13)
        hand_2 = deck.deal(13)
        hand_3 = deck.deal(13)
        hand_4_actual = sorted(deck.deal(13), reverse=True)

        analyzer = CollaborativeTableAnalyzer()
        result = analyzer.analyze_table({1: hand_1, 2: hand_2, 3: hand_3})

        assert result.total_known_cards == 39
        assert len(result.remaining_cards) == 13
        assert result.is_opponent_fully_deduced is True
        assert result.cross_duplicates == []

        # Deduce cards must match hand_4_actual card by card
        deduced_ids = [c.card_id for c in result.remaining_cards]
        actual_ids = [c.card_id for c in hand_4_actual]
        assert deduced_ids == actual_ids

        # Opponent best arrangement must be legally solved
        assert result.opponent_best_arrangement is not None
        assert result.opponent_best_arrangement.is_foul is False

        # Strategies for all 3 windows must be computed against opponent
        assert len(result.window_strategies) == 3
        for win_idx in (1, 2, 3):
            strat = result.window_strategies[win_idx]
            assert strat.window_idx == win_idx
            assert strat.optimal_arrangement.is_foul is False
            # Matchup against opponent must have total_points
            assert strat.matchup is not None

    def test_counter_strategy_maximizes_score_against_opponent(self):
        """Verifies that the counter-strategy selects arrangements that beat or scoop the opponent."""
        analyzer = CollaborativeTableAnalyzer()

        # Hand 1: Strong cards
        h1 = CardParser.parse_cards("As Ks Qs Js 10s 9h 8h 7h 6h 5h 4c 3c 2c")
        # Hand 2: Strong cards
        h2 = CardParser.parse_cards("Ah Kh Qh Jh 10h 9d 8d 7d 6d 5d 4s 3s 2s")
        # Hand 3: Mid cards
        h3 = CardParser.parse_cards("Ad Kd Qd Jd 10d 9s 8s 7s 6s 5s 4d 3d 2d")

        result = analyzer.analyze_table({1: h1, 2: h2, 3: h3})

        assert result.is_opponent_fully_deduced is True
        assert len(result.remaining_cards) == 13

        # For Window 1, optimal arrangement must score >= default arrangement against opponent
        strat_1 = result.window_strategies[1]
        rules = analyzer.rules_engine
        opp = result.opponent_best_arrangement

        score_optimal = rules.compare_head_to_head(strat_1.optimal_arrangement, opp).total_points
        score_default = rules.compare_head_to_head(strat_1.default_arrangement, opp).total_points
        assert score_optimal >= score_default

    def test_cross_duplicates_detection(self):
        """Verifies that duplicate cards across windows are detected and flagged."""
        # Intentionally duplicate As in Window 1 and Window 2
        h1 = CardParser.parse_cards("As Ks Qs Js 10s 9h 8h 7h 6h 5h 4c 3c 2c")
        h2 = CardParser.parse_cards("As Kh Qh Jh 10h 9d 8d 7d 6d 5d 4s 3s 2s")

        analyzer = CollaborativeTableAnalyzer()
        result = analyzer.analyze_table({1: h1, 2: h2})

        assert len(result.cross_duplicates) == 1
        assert result.cross_duplicates[0].short_name == "As"
        assert result.is_opponent_fully_deduced is False
        assert "trùng" in result.summary_message

    def test_partial_windows_tracking(self):
        """Verifies graceful behavior when only 1 or 2 windows are active."""
        h1 = CardParser.parse_cards("As Ks Qs Js 10s 9h 8h 7h 6h 5h 4c 3c 2c")

        analyzer = CollaborativeTableAnalyzer()
        result = analyzer.analyze_table({1: h1})

        assert result.total_known_cards == 13
        assert len(result.remaining_cards) == 39
        assert result.is_opponent_fully_deduced is False
        assert result.opponent_best_arrangement is None
        assert 1 in result.window_strategies
