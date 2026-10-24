"""Unit tests for RulesEngine and RuleConfig."""

import tempfile
from pathlib import Path
import pytest
from app.core.card import CardParser
from app.core.evaluator import Evaluator
from app.core.rules import RuleConfig, RulesEngine
from app.core.solver import HandArrangement


class TestRulesEngine:
    def test_default_config_and_serialization(self):
        config = RuleConfig()
        assert config.players == 4
        assert config.sweep_single_player_bonus == 3.0

        d = config.to_dict()
        assert d["players"] == 4

        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "rules.json"
            config.save_to_file(json_file)
            loaded = RuleConfig.load_from_file(json_file)
            assert loaded.players == 4
            assert loaded.sweep_single_player_bonus == 3.0

    def test_head_to_head_standard_win(self):
        # Player wins back & middle, loses front
        p_front = Evaluator.evaluate_front(CardParser.parse_cards("2s 3h 4d"))       # High 4
        p_mid = Evaluator.evaluate_five(CardParser.parse_cards("Ks Kh 9d 8c 7s"))    # Pair K
        p_back = Evaluator.evaluate_five(CardParser.parse_cards("As Ah Ad 2c 3s"))    # Trips A

        opp_front = Evaluator.evaluate_front(CardParser.parse_cards("As Kh Qd"))     # High A (wins front)
        opp_mid = Evaluator.evaluate_five(CardParser.parse_cards("Qs Qh 9c 8d 7h"))   # Pair Q (loses mid)
        opp_back = Evaluator.evaluate_five(CardParser.parse_cards("Ks Kd Kc 2h 3d"))  # Trips K (loses back)

        p_arr = HandArrangement(p_front.cards, p_mid.cards, p_back.cards, p_front, p_mid, p_back)
        opp_arr = HandArrangement(opp_front.cards, opp_mid.cards, opp_back.cards, opp_front, opp_mid, opp_back)

        engine = RulesEngine()
        res = engine.compare_head_to_head(p_arr, opp_arr)

        assert res.front_outcome == -1
        assert res.middle_outcome == 1
        assert res.back_outcome == 1
        assert res.base_points == 1.0  # -1 + 1 + 1 = +1
        assert res.bonus_points == 0.0
        assert res.total_points == 1.0
        assert res.is_scoop is False
        assert res.is_scooped is False

    def test_head_to_head_scoop(self):
        # Player wins all 3 hands
        p_front = Evaluator.evaluate_front(CardParser.parse_cards("As Ah 4d"))
        p_mid = Evaluator.evaluate_five(CardParser.parse_cards("Ks Kh Kd 8c 7s"))
        p_back = Evaluator.evaluate_five(CardParser.parse_cards("As Ac Ad Ah 2s"))

        opp_front = Evaluator.evaluate_front(CardParser.parse_cards("2s 3h 4c"))
        opp_mid = Evaluator.evaluate_five(CardParser.parse_cards("Qs Qh 9c 8d 7h"))
        opp_back = Evaluator.evaluate_five(CardParser.parse_cards("Ks Kd Kc 2h 3d"))

        p_arr = HandArrangement(p_front.cards, p_mid.cards, p_back.cards, p_front, p_mid, p_back)
        opp_arr = HandArrangement(opp_front.cards, opp_mid.cards, opp_back.cards, opp_front, opp_mid, opp_back)

        engine = RulesEngine()
        res = engine.compare_head_to_head(p_arr, opp_arr)

        assert res.front_outcome == 1
        assert res.middle_outcome == 1
        assert res.back_outcome == 1
        assert res.base_points == 3.0
        assert res.bonus_points == 3.0  # Sweep bonus
        assert res.total_points == 6.0
        assert res.is_scoop is True
        assert res.is_scooped is False

    def test_special_hand_dragon(self):
        dragon_cards = CardParser.parse_cards("As Kh Qd Jc 10s 9h 8d 7c 6s 5h 4d 3c 2s")
        h_type, desc = RulesEngine.check_special_hand(dragon_cards)
        assert h_type == "DRAGON"
        assert "Dragon" in desc

    def test_special_hand_six_pairs(self):
        six_pairs = CardParser.parse_cards("As Ah Ks Kh Qs Qh Js Jh 10s 10h 9s 9h 2c")
        h_type, desc = RulesEngine.check_special_hand(six_pairs)
        assert h_type == "SIX_PAIRS"
