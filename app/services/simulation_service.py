"""Background worker thread for running Monte Carlo simulations and EV optimization."""

from __future__ import annotations
from typing import Sequence
from PySide6.QtCore import QObject, QThread, Signal

from app.core.card import Card
from app.core.ev_optimizer import OptimizedArrangement
from app.services.analysis_service import AnalysisService


class SimulationWorker(QObject):
    """Worker object executing EV optimization on a separate QThread."""

    progress = Signal(int, int, str)               # current, total, status_text
    finished = Signal(list)                        # list[OptimizedArrangement]
    error = Signal(str)                            # error message

    def __init__(
        self,
        analysis_service: AnalysisService,
        cards: Sequence[Card],
        num_candidates: int = 10,
        num_scenarios: int = 300,
        num_opponents: int = 3,
        seed: int | None = 42,
    ) -> None:
        super().__init__()
        self.service = analysis_service
        self.cards = list(cards)
        self.num_candidates = num_candidates
        self.num_scenarios = num_scenarios
        self.num_opponents = num_opponents
        self.seed = seed
        self._is_cancelled = False

    def cancel(self) -> None:
        """Flags the worker to stop processing early."""
        self._is_cancelled = True

    def run(self) -> None:
        """Executes optimization in background."""
        try:
            results = self.service.optimize_ev(
                cards=self.cards,
                num_candidates=self.num_candidates,
                num_scenarios=self.num_scenarios,
                num_opponents=self.num_opponents,
                seed=self.seed,
                progress_callback=self._on_progress,
                cancel_check=lambda: self._is_cancelled,
            )
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, current: int, total: int, message: str) -> None:
        self.progress.emit(current, total, message)
