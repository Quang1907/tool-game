"""Comprehensive End-to-End Integration Test for Binh 13 Analyzer."""

import tempfile
from pathlib import Path
import pytest
from app.core.card import CardParser
from app.database.db import DatabaseManager
from app.database.repository import AnalysisRepository
from app.services.analysis_service import AnalysisService


class TestEndToEndPipeline:
    def test_complete_analysis_pipeline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "integration.db"
            db_mgr = DatabaseManager(db_path=db_path)
            repo = AnalysisRepository(db_manager=db_mgr)
            service = AnalysisService(repository=repo)

            # 1. Parse player cards
            cards = CardParser.parse_cards("As Ks Qs Js 10s 9h 9d 8c 8s 7h 5d 3c 2h")
            assert len(cards) == 13

            # 2. Solve cards
            session_id, arrangements = service.solve_cards(
                cards=cards,
                strategy="BALANCED",
                max_results=10,
                input_method="MANUAL",
            )

            assert len(arrangements) == 10
            best_arr = arrangements[0]

            # Verify non-foul guarantee
            assert best_arr.back_eval >= best_arr.middle_eval
            assert not best_arr.is_foul

            # 3. Optimize EV via Monte Carlo simulation
            optimized = service.optimize_ev(
                cards=cards,
                session_id=session_id,
                num_candidates=3,
                num_scenarios=20,
                num_opponents=3,
                seed=42,
            )

            assert len(optimized) == 3
            top_opt = optimized[0]

            # 4. Save results to repository
            repo.record_simulation_result(
                session_id=session_id,
                stats=top_opt.stats,
                num_opponents=3,
                rules_json="{}",
            )

            # 5. Query repository to verify end-to-end persistence
            sessions = repo.list_recent_sessions()
            assert len(sessions) == 1
            assert sessions[0]["id"] == session_id
            assert sessions[0]["status"] == "SIMULATED"
            assert sessions[0]["top_ev"] == top_opt.stats.expected_value
