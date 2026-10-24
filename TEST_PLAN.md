# TEST PLAN — BINH 13 ANALYZER (macOS)

## 1. Testing Strategy
All testing is automated via `pytest`. The system adheres to strict quality gates: no module is deemed complete without associated passing tests.

---

## 2. Test Matrix

### 2.1. Card & Deck (`tests/test_card.py`)
- Standard 52-card initialization.
- Rank and suit comparisons (Ace high = 14, 2 low = 2).
- Card string parsing (`As`, `10h`, `Kd`, `2c`, Unicode `A♠`).
- Invalid string error raising (`11s`, `Zx`, ``, `100h`).
- Deck shuffle randomness and reproducibility with fixed seed.
- Hand validation (exactly 13 cards, uniqueness check, duplicate detection).

### 2.2. Evaluator (`tests/test_evaluator.py`)
- **Front Hand (3 cards):**
  - High card comparison with kicker ordering (e.g. `A-K-2` vs `A-Q-J`).
  - Pair comparison (e.g. `8-8-A` vs `8-8-K`, `9-9-2` vs `8-8-A`).
  - Three of a kind (e.g. `3-3-3` vs `2-2-2`, beats any pair).
- **Five-Card Hands (Middle & Back):**
  - All 9 categories: High Card, Pair, Two Pair, Trips, Straight, Flush, Full House, Quads, Straight Flush.
  - Category hierarchy: $\text{Straight Flush} > \text{Quads} > \text{Full House} > \text{Flush} > \text{Straight} > \text{Trips} > \text{Two Pair} > \text{Pair} > \text{High Card}$.
  - Tie-breaking:
    - Two pair kicker tie-breaking (`K-K-4-4-A` vs `K-K-4-4-Q`).
    - Full House triplet comparison (`7-7-7-2-2` vs `6-6-6-A-A`).
    - Flush kicker comparison.
    - Straight comparison: Broad-way (`A-K-Q-J-10`), mid-straights, Wheel (`5-4-3-2-A`).
- **Foul Detection:**
  - Valid arrangement: $\text{Back} \ge \text{Middle} \ge \text{Front}$.
  - Invalid arrangements correctly flagged as Foul (e.g., Front Pair > Middle High Card).

### 2.3. Solver (`tests/test_solver.py`)
- Combinatorial partitioning: Verify exactly $\binom{13}{3} \times \binom{10}{5} / 2 = 36,036$ partitions generated.
- Legal hand filter: Verify 0 foul arrangements returned in legal list.
- Solvability guarantee: At least 1 valid arrangement returned for standard hands.
- Card preservation: Verify no cards lost, created, or duplicated during partition.

### 2.4. Rules Engine (`tests/test_rules.py`)
- Standard head-to-head point calculation (+1 win, -1 loss, 0 tie).
- Scoop bonus calculation (all 3 hands won).
- Default configuration loading and custom JSON loading.

### 2.5. Monte Carlo Simulator & EV Optimizer (`tests/test_simulator.py`, `tests/test_ev_optimizer.py`)
- Deck partitioning: No duplicate cards between player hand and opponent hands.
- Opponent hand sizes: Exactly 13 cards per opponent.
- Seed reproducibility: Identical seed produces identical EV and win rates.
- Common Random Numbers (CRN): Monotonic ranking consistency.

### 2.6. Vision Pipeline (`tests/test_vision.py`)
- Synthetic test card image generation.
- Corner crop extraction and normalized cross-correlation template matching.
- Detection validator: Correctly flags 12 cards (missing) and 14 cards (excess), and duplicate card detections.

---

## 3. Automated Test Execution
Run test suite:
```bash
./scripts/test.sh
# or
.venv/bin/pytest -v
```
