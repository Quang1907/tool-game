"""Repository pattern implementation for analysis sessions and simulation data."""

from __future__ import annotations
import datetime
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

    # =========================================================================
    # CARD SLOTS (TAB 7)
    # =========================================================================

    def get_all_card_slots(self) -> List[Any]:
        """Returns all 13 card slots ordered by slot_number (1 to 13)."""
        from app.automation.gesture_models import CardSlot
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM card_slots ORDER BY slot_number ASC")
            rows = cursor.fetchall()
            if not rows:
                return self.init_default_card_slots()
            return [
                CardSlot(
                    slot_number=r["slot_number"],
                    name=r["name"],
                    rel_x=r["rel_x"],
                    rel_y=r["rel_y"],
                    group_name=r["group_name"],
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]

    def save_card_slot(self, slot: Any) -> None:
        """Inserts or updates a card slot position."""
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO card_slots (slot_number, name, rel_x, rel_y, group_name, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(slot_number) DO UPDATE SET
                    name = excluded.name,
                    rel_x = excluded.rel_x,
                    rel_y = excluded.rel_y,
                    group_name = excluded.group_name,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (slot.slot_number, slot.name, slot.rel_x, slot.rel_y, slot.group_name),
            )

    def init_default_card_slots(self) -> List[Any]:
        """Initializes standard 13 card slot positions on game table layout."""
        from app.automation.gesture_models import CardSlot
        default_slots: List[CardSlot] = []

        # Chi Đầu (3 cards): Top row, centered
        # x: 0.35, 0.50, 0.65; y: 0.28
        for i, rx in enumerate([0.35, 0.50, 0.65], start=1):
            default_slots.append(CardSlot(slot_number=i, name=f"Chi Đầu {i}", rel_x=rx, rel_y=0.28, group_name="front"))

        # Chi Giữa (5 cards): Middle row
        # x: 0.22, 0.36, 0.50, 0.64, 0.78; y: 0.50
        for i, rx in enumerate([0.22, 0.36, 0.50, 0.64, 0.78], start=4):
            default_slots.append(CardSlot(slot_number=i, name=f"Chi Giữa {i-3}", rel_x=rx, rel_y=0.50, group_name="middle"))

        # Chi Cuối (5 cards): Bottom row
        # x: 0.22, 0.36, 0.50, 0.64, 0.78; y: 0.72
        for i, rx in enumerate([0.22, 0.36, 0.50, 0.64, 0.78], start=9):
            default_slots.append(CardSlot(slot_number=i, name=f"Chi Cuối {i-8}", rel_x=rx, rel_y=0.72, group_name="back"))

        for s in default_slots:
            self.save_card_slot(s)
        return default_slots

    # =========================================================================
    # GESTURE SAMPLES (156 PAIRS)
    # =========================================================================

    def get_gesture_samples(
        self, source_slot: Optional[int] = None, target_slot: Optional[int] = None
    ) -> List[Any]:
        """Retrieves gesture samples filtered by source and/or target slot."""
        from app.automation.gesture_models import GestureSample, GesturePoint
        query = "SELECT * FROM gesture_samples WHERE 1=1"
        params: List[Any] = []
        if source_slot is not None:
            query += " AND source_slot = ?"
            params.append(source_slot)
        if target_slot is not None:
            query += " AND target_slot = ?"
            params.append(target_slot)
        query += " ORDER BY created_at DESC"

        with self.db.get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            samples: List[GestureSample] = []
            for r in rows:
                raw_pts = json.loads(r["points_json"]) if r["points_json"] else []
                pts = [GesturePoint.from_dict(p) for p in raw_pts]
                meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                samples.append(
                    GestureSample(
                        id=r["id"],
                        source_slot=r["source_slot"],
                        target_slot=r["target_slot"],
                        name=r["name"],
                        points=pts,
                        mouse_down_delay_ms=r["mouse_down_delay_ms"],
                        mouse_up_delay_ms=r["mouse_up_delay_ms"],
                        total_duration_ms=r["total_duration_ms"],
                        is_verified=bool(r["is_verified"]),
                        weight=float(r["weight"]),
                        created_at=r["created_at"],
                        metadata=meta,
                    )
                )
            return samples

    def save_gesture_sample(self, sample: Any) -> None:
        """Saves or updates a gesture sample."""
        points_json = json.dumps([p.to_dict() for p in sample.points])
        meta_json = json.dumps(sample.metadata or {})
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO gesture_samples (
                    id, source_slot, target_slot, name, points_json,
                    mouse_down_delay_ms, mouse_up_delay_ms, total_duration_ms,
                    is_verified, weight, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    points_json = excluded.points_json,
                    mouse_down_delay_ms = excluded.mouse_down_delay_ms,
                    mouse_up_delay_ms = excluded.mouse_up_delay_ms,
                    total_duration_ms = excluded.total_duration_ms,
                    is_verified = excluded.is_verified,
                    weight = excluded.weight,
                    metadata_json = excluded.metadata_json
                """,
                (
                    sample.id,
                    sample.source_slot,
                    sample.target_slot,
                    sample.name,
                    points_json,
                    sample.mouse_down_delay_ms,
                    sample.mouse_up_delay_ms,
                    sample.total_duration_ms,
                    1 if sample.is_verified else 0,
                    sample.weight,
                    sample.created_at,
                    meta_json,
                ),
            )

    def delete_gesture_sample(self, sample_id: str) -> bool:
        """Deletes a gesture sample by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM gesture_samples WHERE id = ?", (sample_id,))
            return cursor.rowcount > 0

    def export_gestures_json(self) -> str:
        """Exports all slots and gesture samples into a portable JSON string."""
        slots = [s.to_dict() for s in self.get_all_card_slots()]
        samples = [s.to_dict() for s in self.get_gesture_samples()]
        export_data = {
            "version": "1.0",
            "exported_at": str(datetime.datetime.now().isoformat()) if "datetime" in globals() else "",
            "slots": slots,
            "samples": samples,
        }
        return json.dumps(export_data, indent=2, ensure_ascii=False)

    def import_gestures_json(self, json_str: str) -> int:
        """Imports slots and gesture samples from JSON, returning number of imported samples."""
        from app.automation.gesture_models import CardSlot, GestureSample
        data = json.loads(json_str)
        imported_count = 0
        if "slots" in data:
            for s_data in data["slots"]:
                slot = CardSlot.from_dict(s_data)
                self.save_card_slot(slot)
        if "samples" in data:
            for smp_data in data["samples"]:
                sample = GestureSample.from_dict(smp_data)
                self.save_gesture_sample(sample)
                imported_count += 1
        return imported_count

