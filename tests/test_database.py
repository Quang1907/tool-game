"""Unit tests for SQLite DatabaseManager and AnalysisRepository."""

import tempfile
from pathlib import Path
import pytest
from app.core.card import CardParser
from app.core.simulator import SimulationStats
from app.core.solver import Solver
from app.database.db import DatabaseManager
from app.database.repository import AnalysisRepository


class TestDatabaseRepository:
    def test_session_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db_mgr = DatabaseManager(db_path=db_path)
            repo = AnalysisRepository(db_manager=db_mgr)

            cards = CardParser.parse_cards("As Kh Qd Jc 10s 9h 8d 7c 6s 5h 4d 3c 2s")

            # 1. Create Session
            session_id = repo.create_session(cards, input_method="MANUAL", notes="Test session")
            assert session_id is not None

            # 2. Save Arrangements
            solver = Solver()
            arrangements = solver.solve(cards, max_results=3)
            arr_ids = repo.save_arrangements(session_id, arrangements)
            assert len(arr_ids) == 3

            # 3. Record Simulation Result
            stats = SimulationStats(
                expected_value=2.45,
                win_rate=0.62,
                tie_rate=0.08,
                loss_rate=0.30,
                front_win_rate=0.55,
                front_tie_rate=0.05,
                front_loss_rate=0.40,
                middle_win_rate=0.60,
                middle_tie_rate=0.05,
                middle_loss_rate=0.35,
                back_win_rate=0.70,
                back_tie_rate=0.05,
                back_loss_rate=0.25,
                scoop_rate=0.15,
                scooped_rate=0.05,
                variance=4.2,
                std_dev=2.05,
                std_err=0.20,
                ci_95_lower=2.05,
                ci_95_upper=2.85,
                total_rounds=100,
                elapsed_seconds=0.12,
            )
            res_id = repo.record_simulation_result(
                session_id=session_id,
                stats=stats,
                num_opponents=3,
                rules_json="{}",
                arrangement_id=arr_ids[0],
            )
            assert res_id is not None

            # 4. List Sessions
            sessions = repo.list_recent_sessions()
            assert len(sessions) == 1
            assert sessions[0]["id"] == session_id
            assert sessions[0]["status"] == "SIMULATED"
            assert sessions[0]["top_ev"] == 2.45

            # 5. Delete Session (Cascading)
            deleted = repo.delete_session(session_id)
            assert deleted is True
            assert len(repo.list_recent_sessions()) == 0
