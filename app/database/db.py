"""SQLite Database connection and schema manager."""

from __future__ import annotations
import os
from pathlib import Path
import sqlite3
from typing import Optional


class DatabaseManager:
    """Manages SQLite database connections and table migrations."""

    DEFAULT_DB_PATH = Path.home() / ".binh13_analyzer" / "data.db"

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else self.DEFAULT_DB_PATH
        self._ensure_dir()
        self.init_schema()

    def _ensure_dir(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_schema(self) -> None:
        """Initializes SQLite schema if not already present."""
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS analysis_sessions (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    input_method TEXT NOT NULL,
                    raw_input_cards TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT
                );

                CREATE TABLE IF NOT EXISTS hand_arrangements (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    rank_order INTEGER NOT NULL,
                    front_cards TEXT NOT NULL,
                    middle_cards TEXT NOT NULL,
                    back_cards TEXT NOT NULL,
                    front_category TEXT NOT NULL,
                    middle_category TEXT NOT NULL,
                    back_category TEXT NOT NULL,
                    heuristic_score REAL NOT NULL,
                    expected_value REAL,
                    is_foul BOOLEAN NOT NULL DEFAULT 0,
                    FOREIGN KEY(session_id) REFERENCES analysis_sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS simulation_runs (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    num_opponents INTEGER NOT NULL DEFAULT 3,
                    num_iterations INTEGER NOT NULL DEFAULT 1000,
                    opponent_model TEXT NOT NULL,
                    random_seed INTEGER,
                    elapsed_seconds REAL NOT NULL,
                    rules_config_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES analysis_sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS simulation_results (
                    id TEXT PRIMARY KEY,
                    simulation_run_id TEXT NOT NULL,
                    arrangement_id TEXT,
                    expected_value REAL NOT NULL,
                    win_rate REAL NOT NULL,
                    tie_rate REAL NOT NULL,
                    loss_rate REAL NOT NULL,
                    front_win_rate REAL NOT NULL,
                    middle_win_rate REAL NOT NULL,
                    back_win_rate REAL NOT NULL,
                    scoop_rate REAL NOT NULL,
                    scooped_rate REAL NOT NULL,
                    std_dev REAL,
                    std_err REAL,
                    ci_95_lower REAL,
                    ci_95_upper REAL,
                    FOREIGN KEY(simulation_run_id) REFERENCES simulation_runs(id) ON DELETE CASCADE,
                    FOREIGN KEY(arrangement_id) REFERENCES hand_arrangements(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS card_references (
                    id TEXT PRIMARY KEY,
                    card_code TEXT NOT NULL,
                    rank TEXT NOT NULL,
                    suit TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'user_confirmed',
                    confirmed BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    image_hash TEXT NOT NULL,
                    metadata_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_card_references_code ON card_references(card_code);
                CREATE INDEX IF NOT EXISTS idx_card_references_hash ON card_references(image_hash);
            """)
