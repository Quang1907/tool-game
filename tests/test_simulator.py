"""Unit tests for MonteCarloSimulator and EVOptimizer."""

import pytest
from app.core.card import CardParser
from app.core.ev_optimizer import EVOptimizer
from app.core.simulator import FastHeuristicOpponent, MonteCarloSimulator
from app.core.solver import Solver


class TestMonteCarloSimulator:
    def test_simulation_runs_and_seed_reproducibility(self):
        cards = CardParser.parse_cards("As Ks Qs Js 10s 9h 8c 7d 6s 5h 4d 3c 2s")
        solver = Solver()
        arrangements = solver.solve(cards, max_results=1)
        assert len(arrangements) == 1
        arr = arrangements[0]

        simulator = MonteCarloSimulator()

        # Run 1 with seed=123
        stats1 = simulator.simulate_arrangement(
            arr, cards, num_rounds=50, num_opponents=3, seed=123
        )

        # Run 2 with same seed=123
        stats2 = simulator.simulate_arrangement(
            arr, cards, num_rounds=50, num_opponents=3, seed=123
        )

        assert stats1.expected_value == stats2.expected_value
        assert stats1.win_rate == stats2.win_rate
        assert stats1.total_rounds == 50
        assert stats1.ci_95_lower <= stats1.expected_value <= stats1.ci_95_upper

    def test_opponent_deals_contain_no_player_cards(self):
        player_cards = CardParser.parse_cards("As Kh Qd Jc 10s 9h 8d 7c 6s 5h 4d 3c 2s")
        player_set = set(player_cards)

        strategy = FastHeuristicOpponent()
        # Verify deck removal logic
        from app.core.card import Deck
        deck = Deck()
        deck.remove(player_cards)
        unseen = deck.cards
        assert len(unseen) == 39

        for i in range(3):
            opp_deal = unseen[i * 13 : (i + 1) * 13]
            opp_set = set(opp_deal)
            # No overlap with player
            assert len(player_set.intersection(opp_set)) == 0
            # Legal arrangement produced
            opp_arr = strategy.arrange(opp_deal)
            assert opp_arr.is_foul is False


class TestEVOptimizer:
    def test_ev_optimization_and_ranking(self):
        cards = CardParser.parse_cards("As Ah Ad Ks Kd 10s 10h 8d 7c 6s 5h 4d 2c")
        optimizer = EVOptimizer()

        progress_calls = []

        def on_progress(cur, total, msg):
            progress_calls.append((cur, total, msg))

        results = optimizer.optimize(
            player_cards=cards,
            num_candidates=5,
            num_scenarios=30,
            num_opponents=3,
            seed=42,
            progress_callback=on_progress,
        )

        assert len(results) > 0
        assert len(progress_calls) > 0

        # Verify sorted by EV descending
        for i in range(len(results) - 1):
            assert results[i].ev >= results[i + 1].ev
            assert results[i].rank == i + 1

    def test_ev_optimization_cancellation(self):
        cards = CardParser.parse_cards("As Ah Ad Ks Kd 10s 10h 8d 7c 6s 5h 4d 2c")
        optimizer = EVOptimizer()

        # Cancellation check that aborts immediately
        results = optimizer.optimize(
            player_cards=cards,
            num_candidates=5,
            num_scenarios=50,
            cancel_check=lambda: True,
        )

        assert results == []
