# IMPLEMENTATION PLAN — BINH 13 ANALYZER (macOS)

## Phase Breakdown

### Phase 0: Audit, Environment & Documentation (Completed)
- Environment verification: macOS Sequoia 15.4.1 ARM64 (Apple Silicon).
- Python 3.11.17 installed via Homebrew; virtual environment created at `.venv/`.
- Full project documentation created (`PROJECT_INVENTORY.md`, `PRD.md`, `ARCHITECTURE.md`, `DATABASE.md`, `IMPLEMENTATION_PLAN.md`, `TEST_PLAN.md`, `DECISIONS.md`, `AGENTS.md`).

### Phase 1: macOS Foundation & Project Configuration
- `pyproject.toml`, `requirements.txt`, `.gitignore`, `Makefile`.
- Scripts in `scripts/`: `setup_macos.sh`, `run_macos.sh`, `test.sh`, `build_macos.sh`.
- App configuration `app/config.py` with default paths and macOS retina/scaling support.

### Phase 2: Core Domain — Card, Deck, and Hand Modeling
- `app/core/card.py`:
  - Enums: `Suit` (Spades, Clubs, Diamonds, Hearts), `Rank` (2..10, J, Q, K, A).
  - Class `Card`: Integer ID (0..51), value rank comparison, unicode representation, hashable, immutable.
  - Class `Deck`: 52 unique cards, Fisher-Yates shuffle with seed support, deal.
  - Class `Hand`: Validation, parsing from strings (`As`, `Kh`, `10d`, `2c`), set conversion.
- Tests in `tests/test_card.py`.

### Phase 3: Core Domain — Evaluator Engine
- `app/core/evaluator.py`:
  - `HandCategory` enumeration.
  - `HandEvaluation`: Comparable data structure `(category, tie_breaker_tuple, description)`.
  - `evaluate_front(cards: 3)`: High Card, Pair, Three of a Kind.
  - `evaluate_five(cards: 5)`: High Card, Pair, Two Pair, Three of a Kind, Straight (including configurable wheel A-2-3-4-5), Flush, Full House, Four of a Kind, Straight Flush.
  - Comparison operator `__lt__`, `__gt__`, `__eq__`, `__ge__`, `__le__`.
  - Is-foul validator: `is_foul(front_eval, middle_eval, back_eval) -> bool` asserting $\text{Back} \ge \text{Middle} \ge \text{Front}$.
- Tests in `tests/test_evaluator.py`.

### Phase 4: Core Domain — Combinatorial Solver
- `app/core/solver.py`:
  - Combinatorial generation of all $36,036$ splits of 13 cards into 3-5-5.
  - Strict pruning of foul configurations.
  - Heuristic scoring strategies: Balanced, Front-heavy, Middle-heavy, Back-heavy.
- Tests in `tests/test_solver.py`.

### Phase 5: Core Domain — Rules Engine
- `app/core/rules.py`:
  - Configuration structure for scoring: Points per hand, scoop bonuses, foul penalties, special hands (Sảnh Rồng, Lục Phé Bôn, 3 Sảnh, 3 Thùng).
  - `config/default_rules.json` loading and overriding.
- Tests in `tests/test_rules.py`.

### Phase 6: Core Domain — Monte Carlo Simulator & EV Optimizer
- `app/core/simulator.py`:
  - Deals unseen cards to $N$ opponents (1 to 3).
  - Opponent models: Random Legal, Greedy, Heuristic.
  - Head-to-head evaluation against each opponent.
- `app/core/ev_optimizer.py`:
  - Common Random Numbers (CRN) simulation runner.
  - Statistical analysis (EV, win/tie/loss rate, scoop rate, standard error, 95% confidence intervals).
- Tests in `tests/test_simulator.py` and `tests/test_ev_optimizer.py`.

### Phase 7: Vision Pipeline & macOS Screen Capture
- `app/vision/screen_capture.py`: Interactive desktop area selection and screenshot grabbing on macOS.
- `app/vision/image_preprocessor.py`: Grayscale, contrast normalization, card contour extraction.
- `app/vision/card_detector.py`: Segmenting individual card boxes.
- `app/vision/card_recognizer.py`: Template matcher and ONNX interface.
- `app/vision/recognition_validator.py`: Human-in-the-loop validation of 13 cards.
- Tests in `tests/test_vision.py`.

### Phase 8: Database & Persistence Layer
- `app/database/db.py`: SQLite connection manager, schema initialization.
- `app/database/repository.py`: CRUD operations for sessions, arrangements, simulation results.

### Phase 9: PySide6 macOS Modern Desktop UI
- Native Apple dark/light styling (`app/ui/styles.py`).
- Components:
  - Card selector / editor widget.
  - Vision capture & recognition dialog.
  - Solver arrangement explorer.
  - Monte Carlo simulation panel with progress bar and statistical metrics.
  - History viewer.
- Background `QThread` workers to guarantee zero UI lag.

### Phase 10: macOS Packaging & Quality Assurance
- PyInstaller `.app` bundle builder script (`scripts/build_macos.sh`).
- Full automated test suite verification.
- Comprehensive end-to-end user documentation.
