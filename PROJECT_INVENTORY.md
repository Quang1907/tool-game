# PROJECT INVENTORY — BINH 13 ANALYZER (macOS)

**Repository Path:** `/Users/levanquang/tool`  
**Audit Date:** 2026-10-25  
**Auditor:** Antigravity Engineering Team  

---

## 1. System Environment & Hardware
- **Operating System:** macOS Sequoia 15.4.1 (Build 24E263, Darwin Kernel 24.4.0)
- **Architecture:** Apple Silicon arm64 (MacBook Air Apple Silicon)
- **Package Manager:** Homebrew 7.0.8 installed at `/opt/homebrew`
- **Global Python:** `/usr/bin/python3` (Python 3.9.6 - macOS command line tools)
- **Target Project Python:** `/opt/homebrew/bin/python3.11` (Python 3.11.17_1 installed via Homebrew)
- **Virtual Environment:** `/Users/levanquang/tool/.venv` (Python 3.11.17)

---

## 2. Repository Initial State
- Initial state: Empty workspace directory (`/Users/levanquang/tool`).
- Git repository: Initialized (`git init`) on 2026-10-25.
- Existing code: None prior to Phase 0.
- Existing models/datasets: None. Pipeline and interface must be prepared without pretending pre-trained weights exist.

---

## 3. Directory Layout (Target Architecture)
```text
/Users/levanquang/tool/
├── .venv/                         # Python 3.11 Virtual Environment
├── app/
│   ├── __init__.py
│   ├── main.py                    # Entry point for GUI application
│   ├── config.py                  # Global application configuration
│   ├── core/                      # Domain Core: Pure logic, zero GUI dependencies
│   │   ├── __init__.py
│   │   ├── card.py                # Card, Suit, Rank, Deck, Hand, Parsers, Validators
│   │   ├── evaluator.py           # Front (3-card), Middle (5-card), Back (5-card) Hand Evaluators
│   │   ├── rules.py               # Configurable scoring & settlement engine
│   │   ├── solver.py              # Combinatorial hand partitioning (13 -> 3-5-5) & validity filter
│   │   ├── simulator.py           # Monte Carlo opponent simulator (1-3 opponents, head-to-head)
│   │   └── ev_optimizer.py        # Expected Value (EV) optimizer using Common Random Numbers
│   ├── vision/                    # Computer Vision: Image processing & Card Detection
│   │   ├── __init__.py
│   │   ├── screen_capture.py      # macOS screen & region capture via CoreGraphics / screencapture / PySide6
│   │   ├── image_preprocessor.py  # Contrast, contour detection, card perspective rectification
│   │   ├── card_detector.py       # Card bounding-box localization
│   │   ├── card_recognizer.py     # Template matching & ONNX inference wrapper
│   │   └── recognition_validator.py # 13-card completeness and uniqueness validator
│   ├── database/                  # Data persistence (SQLite)
│   │   ├── __init__.py
│   │   ├── db.py                  # SQLite connection manager & schema migrations
│   │   ├── models.py              # Data models (Session, Arrangement, SimulationResult)
│   │   └── repository.py          # Repository pattern for sessions and history
│   ├── services/                  # Application Services orchestrating Core & DB
│   │   ├── __init__.py
│   │   ├── analysis_service.py    # High-level analysis workflows
│   │   └── simulation_service.py  # Background worker orchestration
│   └── ui/                        # PySide6 Modern macOS Desktop Presentation Layer
│       ├── __init__.py
│       ├── main_window.py         # Main macOS window layout & tabs
│       ├── styles.py              # Apple Human Interface Guideline styles (Dark/Light mode)
│       ├── components/            # Modular reusable UI widgets
│       │   ├── card_widget.py     # Interactive visual card representation
│       │   ├── card_selector.py   # Manual 13-card picker dialog
│       │   ├── vision_widget.py   # Screenshot capture & card crop validator
│       │   ├── solver_widget.py   # Arrangement comparison & EV ranking
│       │   ├── simulator_widget.py# Monte Carlo simulation control & progress
│       │   └── history_widget.py  # History search, table & export
├── config/
│   └── default_rules.json         # Configurable game rules
├── docs/                          # Detailed architecture, algorithm, and guide docs
├── models/                        # Directory for ONNX card recognition models
├── scripts/                       # macOS automation scripts (setup, run, test, build)
│   ├── setup_macos.sh
│   ├── run_macos.sh
│   ├── test.sh
│   └── build_macos.sh
├── tests/                         # Pytest test suite
│   ├── __init__.py
│   ├── test_card.py
│   ├── test_evaluator.py
│   ├── test_rules.py
│   ├── test_solver.py
│   ├── test_simulator.py
│   ├── test_ev_optimizer.py
│   └── test_vision.py
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 4. Installed Dependencies & Tools
| Package / Tool | Version | Purpose |
|---|---|---|
| Python | 3.11.17 | Core runtime (ARM64 Apple Silicon) |
| pytest | 9.1.1 | Unit, integration & property-based testing |
| numpy | 2.4.6 | Vectorized computations & Monte Carlo matrices |
| PySide6 | Pending install | Native macOS desktop UI framework |
| opencv-python | Pending install | Image preprocessing & template matching |
| Pillow | Pending install | Image format conversions & manipulation |
