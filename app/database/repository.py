"""Repository pattern implementation for analysis sessions and simulation data."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from app.core.card import Card
from app.core.simulator import SimulationStats
from app.core.solver import HandArrangement
from app.database.db import DatabaseManager


class AnalysisRepository:
    """Repository handling CRUD operations for analysis sessions and history."""

    def __init__(self, db_manager: DatabaseManager | None = None) -> None:
        self.db = db_manager or DatabaseManager()

    def create_session(
        self,
        cards: list[Card],
        input_method: str = "MANUAL",
        notes: str = "",
    ) -> str:
        """Creates a new analysis session record."""
        session_id = str(uuid.uuid4())
        raw_cards_json = json.dumps([c.short_name for c in cards])

        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO analysis_sessions (id, input_method, raw_input_cards, status, notes)
                VALUES (?, ?, ?, 'INITIALIZED', ?)
                """,
                (session_id, input_method, raw_cards_json, notes),
            )
        return session_id

    def save_arrangements(
        self,
        session_id: str,
        arrangements: list[HandArrangement],
    ) -> list[str]:
        """Saves ranked hand arrangements under a session."""
        ids: list[str] = []
        with self.db.get_connection() as conn:
            for rank, arr in enumerate(arrangements, start=1):
                arr_id = str(uuid.uuid4())
                ids.append(arr_id)
                conn.execute(
                    """
                    INSERT INTO hand_arrangements (
                        id, session_id, rank_order, front_cards, middle_cards, back_cards,
                        front_category, middle_category, back_category, heuristic_score, is_foul
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        arr_id,
                        session_id,
                        rank,
                        json.dumps([c.short_name for c in arr.front]),
                        json.dumps([c.short_name for c in arr.middle]),
                        json.dumps([c.short_name for c in arr.back]),
                        arr.front_eval.category.name,
                        arr.middle_eval.category.name,
                        arr.back_eval.category.name,
                        arr.heuristic_score,
                        1 if arr.is_foul else 0,
                    ),
                )
            conn.execute(
                "UPDATE analysis_sessions SET status = 'SOLVED' WHERE id = ?",
                (session_id,),
            )
        return ids

    def get_top_arrangement_id(self, session_id: str) -> Optional[str]:
        """Returns the ID of the highest ranked arrangement in a session."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM hand_arrangements WHERE session_id = ? ORDER BY rank_order ASC LIMIT 1",
                (session_id,),
            )
            row = cursor.fetchone()
            return row["id"] if row else None

    def record_simulation_result(
        self,
        session_id: str,
        stats: SimulationStats,
        num_opponents: int,
        rules_json: str,
        arrangement_id: Optional[str] = None,
    ) -> str:
        """Records a simulation run and its empirical stats."""
        run_id = str(uuid.uuid4())
        res_id = str(uuid.uuid4())

        # If arrangement_id not specified, resolve top arrangement for session
        if arrangement_id is None:
            arrangement_id = self.get_top_arrangement_id(session_id)

        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO simulation_runs (
                    id, session_id, num_opponents, num_iterations, opponent_model,
                    elapsed_seconds, rules_config_json
                ) VALUES (?, ?, ?, ?, 'FAST_HEURISTIC', ?, ?)
                """,
                (run_id, session_id, num_opponents, stats.total_rounds, stats.elapsed_seconds, rules_json),
            )

            conn.execute(
                """
                INSERT INTO simulation_results (
                    id, simulation_run_id, arrangement_id, expected_value,
                    win_rate, tie_rate, loss_rate, front_win_rate, middle_win_rate,
                    back_win_rate, scoop_rate, scooped_rate, std_dev, std_err,
                    ci_95_lower, ci_95_upper
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    res_id, run_id, arrangement_id, stats.expected_value,
                    stats.win_rate, stats.tie_rate, stats.loss_rate,
                    stats.front_win_rate, stats.middle_win_rate, stats.back_win_rate,
                    stats.scoop_rate, stats.scooped_rate, stats.std_dev, stats.std_err,
                    stats.ci_95_lower, stats.ci_95_upper,
                ),
            )

            # Update arrangement expected value if arrangement_id valid
            if arrangement_id:
                conn.execute(
                    "UPDATE hand_arrangements SET expected_value = ? WHERE id = ?",
                    (stats.expected_value, arrangement_id),
                )
            conn.execute(
                "UPDATE analysis_sessions SET status = 'SIMULATED' WHERE id = ?",
                (session_id,),
            )
        return res_id

    def list_recent_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists recent sessions ordered by creation time descending."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT s.id, s.created_at, s.input_method, s.raw_input_cards, s.status, s.notes,
                       COUNT(a.id) as arrangement_count,
                       MAX(a.expected_value) as top_ev
                FROM analysis_sessions s
                LEFT JOIN hand_arrangements a ON s.id = a.session_id
                GROUP BY s.id
                ORDER BY s.created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session and all cascading arrangements / simulation logs."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM analysis_sessions WHERE id = ?", (session_id,))
            return cursor.rowcount > 0
