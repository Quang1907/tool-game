# MULTI-AGENT COLLABORATION ROLES — BINH 13 ANALYZER (macOS)

This project is built and maintained following a multi-agent specialized engineering team structure:

| Role | Domain / Focus | Key Responsibilities | Primary Source Files |
|---|---|---|---|
| **Master Engineer** | System Knowledge & Governance | Architectural consistency, state management, roadmap, `.ai/` system | `MASTER_CONTEXT.md`, `.ai/*` |
| **Senior Python Engineer** | Clean Code, Packaging & Types | Architecture setup, `pyproject.toml`, typing, code quality, dependency management | `pyproject.toml`, `app/main.py` |
| **Algorithm Engineer** | Poker Combinatorics & EV | `card.py`, `evaluator.py`, `solver.py`, `rules.py`, `simulator.py`, `ev_optimizer.py` | `app/core/*`, `.ai/GAME_RULES.md` |
| **Computer Vision Engineer** | Vision Pipeline | `screen_capture.py`, `image_preprocessor.py`, `card_detector.py`, `card_recognizer.py`, `card_reference_library.py` | `app/vision/*` |
| **macOS Engineer** | macOS Platform & App Bundling | Apple Silicon optimization, permissions, Info.plist, `.app` bundling, PyInstaller | `scripts/*`, `Binh13Analyzer.spec` |
| **UI/UX Designer** | Desktop Interface | PySide6 layouts, Apple Human Interface Guidelines, dark/light theme, card widgets, dialogs | `app/ui/*` |
| **QA Engineer** | Testing & Verification | Unit tests, edge case verification, combinatorial proofs, test automation | `tests/*`, `.ai/state/TEST_STATUS.md` |
| **DevOps Engineer** | Automation Scripts | `setup_macos.sh`, `run_macos.sh`, `test.sh`, `build_macos.sh` | `scripts/*` |

---

## Operating Principles
1. **Never mock reality:** Tests must execute real code against real assertions.
2. **Deterministic Verification:** Combinatorial partitions and evaluator tie-breakers must be mathematically proven.
3. **Graceful Degradation:** If an external library or model is missing, fallback gracefully with clear diagnostic messages.
4. **Safety & Privacy:** No telemetry, no background game memory access.

---

## Knowledge & Governance Integration
All agents must start their session by consulting:
- **Master Entry Point:** [MASTER_CONTEXT.md](file:///Users/levanquang/tool/MASTER_CONTEXT.md)
- **Master Rules:** [.ai/MASTER_RULES.md](file:///Users/levanquang/tool/.ai/MASTER_RULES.md)
- **Module & Knowledge Map:** [.ai/MODULE_MAP.md](file:///Users/levanquang/tool/.ai/MODULE_MAP.md)
- **Current State:** [.ai/state/CURRENT_STATE.md](file:///Users/levanquang/tool/.ai/state/CURRENT_STATE.md)
- **5-Step Workflow:** [.ai/workflows/SESSION_WORKFLOW.md](file:///Users/levanquang/tool/.ai/workflows/SESSION_WORKFLOW.md)
