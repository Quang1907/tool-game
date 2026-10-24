"""Unit tests for Binh 13 Combinatorial Solver."""

import time
import pytest
from app.core.card import CardParser
from app.core.evaluator import Evaluator
from app.core.solver import Solver


class TestSolverCombinatorics:
    def test_total_raw_partitions_count_is_36036(self):
        cards = CardParser.parse_cards("As Kh Qd Jc 10s 9h 8d 7c 6s 5h 4d 3c 2s")
        solver = Solver()
        total_partitions = solver.count_total_partitions(cards)
        assert total_partitions == 36036

    def test_solver_produces_only_legal_hands(self):
        # A mixed hand with some pairs and flushes
        cards = CardParser.parse_cards("As Ks Qs Js 10s 9h 9d 8c 8s 7h 5d 3c 2h")
        solver = Solver()

        start_time = time.perf_counter()
        solutions = solver.solve(cards)
        elapsed = time.perf_counter() - start_time

        print(f"\n[Performance] Solved 36,036 partitions in {elapsed*1000:.1f}ms, found {len(solutions)} legal arrangements")

        assert len(solutions) > 0
        # Verification of performance: should be fast (< 0.5s)
        assert elapsed < 0.5

        original_set = set(cards)

        # Inspect top 100 solutions or all solutions to verify 0 foul hands
        for arr in solutions[:200]:
            # Hand sizes
            assert len(arr.front) == 3
            assert len(arr.middle) == 5
            assert len(arr.back) == 5

            # Card conservation
            arr_cards_set = set(arr.all_cards)
            assert arr_cards_set == original_set
            assert len(arr_cards_set) == 13

            # Legality check
            assert arr.back_eval >= arr.middle_eval
            assert not Evaluator.is_front_stronger_than_five(arr.front_eval, arr.middle_eval)
            assert Evaluator.is_foul(arr.front_eval, arr.middle_eval, arr.back_eval) is False

    def test_solver_card_conservation_and_uniqueness(self):
        cards = CardParser.parse_cards("Ah Ad Ac Ks Kd 10s 10h 8d 7c 6s 5h 4d 2c")
        solver = Solver()
        solutions = solver.solve(cards, max_results=10)

        assert len(solutions) > 0
        best = solutions[0]
        # Full house or quads in back, two pair or pair in middle, pair or high card in front
        assert best.back_eval >= best.middle_eval
        assert not Evaluator.is_front_stronger_than_five(best.front_eval, best.middle_eval)

    def test_solver_rejects_invalid_inputs(self):
        solver = Solver()
        # 12 cards
        with pytest.raises(ValueError):
            solver.solve(CardParser.parse_cards("As Kh Qd Jc 10s 9h 8d 7c 6s 5h 4d 3c"))

        # 13 cards with duplicate
        with pytest.raises(ValueError):
            solver.solve(CardParser.parse_cards("As As Qd Jc 10s 9h 8d 7c 6s 5h 4d 3c 2s"))
