"""High-level analysis service coordinating core domain logic and database persistence."""

from __future__ import annotations
from typing import Callable, Sequence

from app.core.card import Card, CardParser, CardValidator
from app.core.ev_optimizer import EVOptimizer, OptimizedArrangement
from app.core.rules import RuleConfig, RulesEngine
from app.core.simulator import MonteCarloSimulator, SimulationStats
from app.core.solver import HandArrangement, Solver
from app.database.repository import AnalysisRepository


class AnalysisService:
    """Orchestrates end-to-end card analysis, solving, simulation, and history persistence."""

    def __init__(
        self,
        rules_config: RuleConfig | None = None,
        repository: AnalysisRepository | None = None,
    ) -> None:
        self.rules_config = rules_config or RuleConfig()
        self.rules_engine = RulesEngine(self.rules_config)
        self.solver = Solver(wheel_rule=self.rules_config.wheel_straight_rule)
        self.simulator = MonteCarloSimulator(rules_engine=self.rules_engine)
        self.optimizer = EVOptimizer(rules_engine=self.rules_engine)
        self.repository = repository or AnalysisRepository()

    def solve_cards(
        self,
        cards: Sequence[Card],
        strategy: str = "BALANCED",
        max_results: int = 50,
        input_method: str = "MANUAL",
    ) -> tuple[str, list[HandArrangement]]:
        """Solves 13 cards, persists the session, and returns top legal arrangements."""
        is_valid, err = CardValidator.validate_13_cards(cards)
        if not is_valid:
            raise ValueError(err)

        card_list = list(cards)
        arrangements = self.solver.solve(card_list, strategy=strategy, max_results=max_results)

        # Persist session and arrangements
        session_id = self.repository.create_session(card_list, input_method=input_method)
        if arrangements:
            self.repository.save_arrangements(session_id, arrangements)

        return session_id, arrangements

    def optimize_ev(
        self,
        cards: Sequence[Card],
        session_id: str | None = None,
        num_candidates: int = 10,
        num_scenarios: int = 300,
        num_opponents: int = 3,
        seed: int | None = 42,
        progress_callback: Callable[[int, int, str], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> list[OptimizedArrangement]:
        """Runs Monte Carlo EV optimization across candidate arrangements."""
        results = self.optimizer.optimize(
            player_cards=cards,
            num_candidates=num_candidates,
            num_scenarios=num_scenarios,
            num_opponents=num_opponents,
            seed=seed,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
        )

        return results
