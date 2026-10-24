# ARCHITECTURAL DECISION RECORDS (ADR) — BINH 13 ANALYZER (macOS)

## ADR 1: Python Runtime & Apple Silicon Target
- **Context:** macOS Sequoia 15.4.1 runs on ARM64 Apple Silicon. The system Python is 3.9.6 (limited type hints and performance).
- **Decision:** Installed and standardized on **Python 3.11.17** via Homebrew with an isolated virtual environment (`.venv/`).
- **Consequences:** Native ARM64 compilation, optimal performance for PySide6, OpenCV, and NumPy on Apple Silicon.

## ADR 2: PySide6 over Tkinter or Web-based Desktop
- **Context:** Desktop UI required for macOS with high responsiveness and native aesthetics.
- **Decision:** Selected **PySide6 (Qt for Python)**.
- **Consequences:** Native macOS styling, high DPI retina support, built-in asynchronous worker threading (`QThread`), hardware acceleration, superior to Tkinter in design elegance.

## ADR 3: Pure Python & NumPy Domain Core without GUI Dependencies
- **Context:** High combinatorial complexity ($36,036$ partitions per 13 cards) and Monte Carlo iterations ($10,000+$ rounds).
- **Decision:** The domain core (`app/core/`) must have **zero UI dependencies**. Hand ranks and cards are represented as lightweight integer tuples and bitmasks.
- **Consequences:** Maximum execution speed, zero GUI thread stalls, seamless headless testing in CI/CD.

## ADR 4: Combinatorial Partitioning Algorithm
- **Context:** Partitioning 13 cards into 3 (front), 5 (middle), 5 (back).
- **Decision:** Partition by choosing 3 cards for front $\binom{13}{3} = 286$, then 5 cards from remaining 10 for middle $\binom{10}{5} = 252$. The remaining 5 cards automatically form the back. Since middle and back both have size 5, swapping them gives symmetry, but because $\text{Back} \ge \text{Middle}$, we canonically assign $\text{Back} = \max(\text{group}_1, \text{group}_2)$ and $\text{Middle} = \min(\text{group}_1, \text{group}_2)$.
- **Consequences:** Reduces the search space to $286 \times 126 = 36,036$ unique unordered splits.

## ADR 5: Common Random Numbers (CRN) for Monte Carlo Comparison
- **Context:** Comparing multiple candidate hand arrangements with high variance.
- **Decision:** All candidate arrangements in an optimization run are evaluated against the exact same stream of generated opponent deals.
- **Consequences:** Drastically reduces variance in pairwise comparisons, enabling reliable ranking with fewer simulation iterations.

## ADR 6: Non-Invasive Computer Vision Pipeline
- **Context:** Card recognition without modifying or reading game process memory.
- **Decision:** Capture screen regions via standard macOS OS APIs (`screencapture` or Qt native grabber). Provide modular CV interface: Stage 1 template matching with full manual human verification; Stage 2 pluggable ONNX model.
- **Consequences:** 100% compliant with operating system security; does not trigger anti-cheat software; completely ethical and safe.
