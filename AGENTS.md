# MULTI-AGENT COLLABORATION ROLES — BINH 13 ANALYZER (macOS)

This project is built and maintained following a multi-agent specialized engineering team structure:

| Role | Domain / Focus | Key Responsibilities |
|---|---|---|
| **Senior Python Engineer** | Clean Code, Packaging & Types | Architecture setup, `pyproject.toml`, typing, code quality, dependency management |
| **Algorithm Engineer** | Poker Combinatorics & EV | `card.py`, `evaluator.py`, `solver.py`, `rules.py`, `simulator.py`, `ev_optimizer.py` |
| **Computer Vision Engineer** | Vision Pipeline | `screen_capture.py`, `image_preprocessor.py`, `card_detector.py`, `card_recognizer.py` |
| **macOS Engineer** | macOS Platform & App Bundling | Apple Silicon optimization, permissions, Info.plist, `.app` bundling, PyInstaller |
| **UI/UX Designer** | Desktop Interface | PySide6 layouts, Apple Human Interface Guidelines, dark/light theme, card widgets |
| **QA Engineer** | Testing & Verification | Unit tests, edge case verification, combinatorial proofs, test automation |
| **DevOps Engineer** | Automation Scripts | `setup_macos.sh`, `run_macos.sh`, `test.sh`, `build_macos.sh` |

---

## Operating Principles
1. **Never mock reality:** Tests must execute real code against real assertions.
2. **Deterministic Verification:** Combinatorial partitions and evaluator tie-breakers must be mathematically proven.
3. **Graceful Degradation:** If an external library or model is missing, fallback gracefully with clear diagnostic messages.
4. **Safety & Privacy:** No telemetry, no background game memory access.
