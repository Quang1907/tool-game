# PRODUCT REQUIREMENTS DOCUMENT (PRD) — BINH 13 ANALYZER (macOS)

## 1. Product Overview
**Binh 13 Analyzer** is an offline, non-invasive tactical decision-support and Monte Carlo simulation tool for Mậu Binh (13-card Chinese Poker) on macOS. It enables players and strategists to input, recognize, evaluate, partition, and optimize hand arrangements based on rigorous Expected Value (EV) calculations against customizable opponent models.

**Key Principle:** The software operates solely through user-provided input and visual screen captures. It does not tamper with game processes, network streams, server calls, or opponent downcards.

---

## 2. Core Functional Requirements

### FR1: Card Input & Representation
- **FR1.1:** Manual card picker supporting standard 52-card deck (A, K, Q, J, 10-2 across ♠ Spades, ♣ Clubs, ♦ Diamonds, ♥ Hearts).
- **FR1.2:** Text parser supporting standard notations (e.g., `As`, `Kh`, `10d`, `2c` or Unicode `A♠`, `K♥`).
- **FR1.3:** Strict validation ensuring exactly 13 unique cards (no duplicates, no foreign cards).

### FR2: Hand Evaluation Engine (`evaluator.py`)
- **FR2.1:** Front Hand (Chi Đầu - 3 cards) evaluation:
  - High Card (Mậu Thầu)
  - One Pair (Đôi)
  - Three of a Kind (Sám Cô)
  - Full kicker tie-breaking.
- **FR2.2:** Middle (Chi Giữa - 5 cards) & Back (Chi Cuối - 5 cards) evaluation:
  - High Card, One Pair, Two Pair, Three of a Kind, Straight (Sảnh), Flush (Thùng), Full House (Cù Lũ), Four of a Kind (Tứ Quý), Straight Flush (Thùng Phá Sảnh).
  - Wheel straight handling (A-2-3-4-5) according to configurable rule set.
  - Complete tie-break vectors for identical category hands.
- **FR2.3:** Hand hierarchy validation:
  - Valid arrangement requirement: $\text{Back Hand} \ge \text{Middle Hand} \ge \text{Front Hand}$.
  - Any arrangement violating this is marked as Foul (Binh Lủng / Binh Binh) and discarded.

### FR3: Combinatorial Hand Solver (`solver.py`)
- **FR3.1:** Exhaustive partition of 13 cards into 3 cards (front), 5 cards (middle), 5 cards (back):
  $$\binom{13}{3} \times \binom{10}{5} / 2 = 286 \times 252 / 2 = 36,036 \text{ raw combinations.}$$
- **FR3.2:** Filtering out all foul hands, retaining only strictly legal arrangements.
- **FR3.3:** Multi-strategy heuristic ranking (Balanced, Front-loaded, Middle-loaded, Back-loaded, Aggressive).

### FR4: Configurable Game Rules Engine (`rules.py`)
- **FR4.1:** Number of players (2 to 4, default 4).
- **FR4.2:** Scoring per hand (Win: +1, Loss: -1, Tie: 0).
- **FR4.3:** Sweep bonuses (Sập 3 chi, Sập làng) and special hands (Mậu Binh thắng trắng: Dragon/Sảnh Rồng, 6 Pairs, 3 Straights, 3 Flushes) toggles.
- **FR4.4:** Fully configurable via JSON profile.

### FR5: Monte Carlo Opponent Simulation (`simulator.py`)
- **FR5.1:** Deal remaining $52 - 13 = 39$ cards among $N$ opponents (default 3 opponents $\times 13 = 39$ cards).
- **FR5.2:** Zero leakage: Opponent cards drawn strictly from remaining unseen deck.
- **FR5.3:** Configurable opponent strategy models (Random Legal, Heuristic Greedy, Strategic Balanced).
- **FR5.4:** Detailed head-to-head metrics: Hand-by-hand win/tie/loss rate, table win rate, average points, EV, variance, standard error, and 95% confidence intervals.

### FR6: Expected Value (EV) Optimizer (`ev_optimizer.py`)
- **FR6.1:** Common Random Numbers (CRN): Evaluates all candidate candidate arrangements across identical opponent scenarios to minimize variance.
- **FR6.2:** Multi-stage pruning: Fast heuristic filtering on candidate pool before full Monte Carlo iteration.
- **FR6.3:** Asynchronous non-blocking worker with progress reporting and cancellation.

### FR7: Vision Pipeline & macOS Screen Capture (`app/vision/`)
- **FR7.1:** Native macOS screen capture with interactive ROI (Region of Interest) selector.
- **FR7.2:** Image preprocessing, contour detection, card segmentation.
- **FR7.3:** Template matching & modular classifier interface (ready for ONNX model integration).
- **FR7.4:** Interactive verification UI allowing user review and correction of detected cards.

### FR8: macOS Desktop Application (`app/ui/`)
- **FR8.1:** Native PySide6 interface complying with macOS design guidelines (Dark & Light mode).
- **FR8.2:** Responsive layout, real-time feedback, non-blocking execution via QThread.
- **FR8.3:** Local database storage (SQLite) for analysis sessions, arrangements, and historical charts.

---

## 3. Non-Functional Requirements
- **Performance:** Complete combinatorial search ($36,036$ partitions) and foul-hand filter in $< 0.3$s on Apple Silicon.
- **Reliability:** 100% test coverage for core evaluator, solver combinatorial counts, and rule engine.
- **Privacy & Security:** Zero remote network telemetry, zero game process hooking, 100% offline capability.
- **Packaging:** Standalone macOS application bundle (`.app`) buildable via script.
