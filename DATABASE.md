# DATABASE DESIGN & SCHEMA — BINH 13 ANALYZER (macOS)

## 1. Overview
The application uses SQLite as an embedded, zero-configuration, ACID-compliant local database. It persists analysis sessions, recognized card inputs, candidate hand arrangements, Monte Carlo simulation runs, and configuration settings.

Database location: `~/.binh13_analyzer/data.db` (or user configurable path).

---

## 2. Entity Relationship & Schema

```sql
-- 1. Analysis Sessions
CREATE TABLE IF NOT EXISTS analysis_sessions (
    id TEXT PRIMARY KEY,               -- UUID4
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    input_method TEXT NOT NULL,         -- 'MANUAL' | 'SCREEN_CAPTURE' | 'IMAGE_FILE'
    raw_input_cards TEXT NOT NULL,      -- JSON array of 13 card codes: ["As", "Kd", ...]
    status TEXT NOT NULL,               -- 'INITIALIZED' | 'SOLVED' | 'SIMULATED' | 'FAILED'
    notes TEXT
);

-- 2. Hand Arrangements (Combinatorial solutions)
CREATE TABLE IF NOT EXISTS hand_arrangements (
    id TEXT PRIMARY KEY,               -- UUID4
    session_id TEXT NOT NULL,
    rank_order INTEGER NOT NULL,       -- Ranking among solutions (1 = highest EV/heuristic)
    front_cards TEXT NOT NULL,         -- JSON array of 3 card strings: ["3s", "3c", "Ah"]
    middle_cards TEXT NOT NULL,        -- JSON array of 5 card strings: ["4d", "5d", "6d", "7d", "8d"]
    back_cards TEXT NOT NULL,          -- JSON array of 5 card strings: ["10s", "10h", "10d", "Jc", "Qc"]
    front_category TEXT NOT NULL,      -- 'ONE_PAIR', etc.
    middle_category TEXT NOT NULL,     -- 'STRAIGHT_FLUSH', etc.
    back_category TEXT NOT NULL,       -- 'THREE_OF_A_KIND', etc.
    heuristic_score REAL NOT NULL,
    expected_value REAL,               -- Populated after Monte Carlo simulation
    is_foul BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY(session_id) REFERENCES analysis_sessions(id) ON DELETE CASCADE
);

-- 3. Simulation Runs
CREATE TABLE IF NOT EXISTS simulation_runs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    num_opponents INTEGER NOT NULL DEFAULT 3,
    num_iterations INTEGER NOT NULL DEFAULT 10000,
    opponent_model TEXT NOT NULL,       -- 'RANDOM_LEGAL' | 'HEURISTIC' | 'GREEDY'
    random_seed INTEGER,
    elapsed_seconds REAL NOT NULL,
    rules_config_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES analysis_sessions(id) ON DELETE CASCADE
);

-- 4. Simulation Results (Per arrangement)
CREATE TABLE IF NOT EXISTS simulation_results (
    id TEXT PRIMARY KEY,
    simulation_run_id TEXT NOT NULL,
    arrangement_id TEXT NOT NULL,
    expected_value REAL NOT NULL,
    win_rate REAL NOT NULL,
    tie_rate REAL NOT NULL,
    loss_rate REAL NOT NULL,
    front_win_rate REAL NOT NULL,
    middle_win_rate REAL NOT NULL,
    back_win_rate REAL NOT NULL,
    scoop_rate REAL NOT NULL,           -- Rate of winning all 3 hands against an opponent
    scooped_rate REAL NOT NULL,         -- Rate of losing all 3 hands
    std_dev REAL,
    std_err REAL,
    ci_95_lower REAL,
    ci_95_upper REAL,
    FOREIGN KEY(simulation_run_id) REFERENCES simulation_runs(id) ON DELETE CASCADE,
    FOREIGN KEY(arrangement_id) REFERENCES hand_arrangements(id) ON DELETE CASCADE
);

-- 5. Application Settings & Rule Profiles
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. Data Integrity & Privacy Controls
- **Zero Cloud Sync:** All data resides exclusively on local user storage.
- **Privacy Mode:** Screen captures used for vision recognition are kept strictly in RAM and never written to disk or stored in SQLite unless the user explicitly clicks "Save Screenshot for Dataset".
- **Cascading Deletions:** Deleting a session cleans up all related arrangements and simulation logs.
