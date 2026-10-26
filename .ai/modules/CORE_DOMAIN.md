# MODULE DOCUMENTATION: DOMAIN CORE (`app/core/`)

---

## 1. MỤC ĐÍCH & PHẠM VI

Phân hệ Domain Core là trái tim toán học và logic của Binh 13 Analyzer. Phân hệ này chịu trách nhiệm:
1. Đại diện cho các thực thể quân bài, bộ bài, tay bài với hiệu năng cao.
2. Đánh giá thứ bậc tay bài (Chi Đầu 3 lá, Chi Giữa/Cuối 5 lá) và kiểm tra bài Lủng.
3. Giải bài toán tổ hợp phân rã 13 lá thành 36,036 thế bài hợp lệ.
4. Mô phỏng đối thủ ảo Monte Carlo và tính toán Expected Value (EV) với Common Random Numbers.

> [!IMPORTANT]
> **Ràng buộc kiến trúc:** Phân hệ này thuần túy sử dụng thư viện chuẩn Python và NumPy. Tuyệt đối **không phụ thuộc** vào GUI (`PySide6`), thị giác máy tính (`cv2`), hoặc cơ sở dữ liệu (`sqlite3`).

---

## 2. CÁC TẬP TIN NGUỒN VÀ CLASS CHÍNH

### 2.1. `card.py`
- `Rank(IntEnum)`: Giá trị từ `TWO = 2` đến `ACE = 14`.
- `Suit(IntEnum)`: Chất bài `SPADES = 1`, `CLUBS = 2`, `DIAMONDS = 3`, `HEARTS = 4`.
- `Card`: Thực thể quân bài bất biến (`frozen=True`, `slots=True`).
  - `id`: Mã số nguyên từ $0..51$ ($(\text{rank} - 2) \times 4 + (\text{suit} - 1)$).
  - `unicode_name`: Chuỗi hiển thị đẹp (ví dụ `A♠`, `10♦`, `K♥`).
  - `from_str(s)`: Parser nhận chuỗi `As`, `10d`, `Kh`, `2c`.
- `Deck`: Bộ bài 52 lá, hỗ trợ xáo bài chuẩn Fisher-Yates kèm hạt giống ngẫu nhiên (`seed`).
- `Hand`: Vùng chứa 13 lá bài với kiểm tra trùng lặp và tính toàn vẹn.

### 2.2. `evaluator.py`
- `HandCategory(IntEnum)`: Thứ tự từ `HIGH_CARD = 1` đến `STRAIGHT_FLUSH = 9`.
- `HandEvaluation`: Tuple điểm số có thể so sánh trực tiếp bằng toán tử `<`, `>`, `==`:
  `score_vector = (category, tie_breaker_tuple)`.
- `evaluate_front(cards: Sequence[Card])`: Đánh giá 3 lá Chi Đầu (High Card, Pair, Trips).
- `evaluate_five(cards: Sequence[Card])`: Đánh giá 5 lá Chi Giữa / Chi Cuối. Hỗ trợ cấu hình sảnh A-2-3-4-5 (`wheel_straight_rule`).
- `is_foul(front_eval, middle_eval, back_eval) -> bool`:
  Trả về `True` nếu $\text{Back} < \text{Middle}$ hoặc $\text{Middle} < \text{Front}$.

### 2.3. `solver.py`
- `HandArrangement`: Đại diện cho một cách xếp bài hợp lệ 3 chi kèm điểm đánh giá heuristic.
- `Solver.solve(hand: Hand) -> List[HandArrangement]`:
  - Chọn 3 lá cho Chi Đầu: $\binom{13}{3} = 286$.
  - Chọn 5 lá cho Chi Giữa từ 10 lá còn lại: $\binom{10}{5} = 252$.
  - 5 lá còn lại là Chi Cuối.
  - Khử tính đối xứng: $\frac{286 \times 252}{2} = 36,036$ thế bài duy nhất.
  - Lọc bỏ ngay các thế bài vi phạm điều kiện chống Binh Lủng.
  - Sắp xếp sơ bộ bằng Heuristic để chọn ra các ứng viên hàng đầu cho Monte Carlo.

### 2.4. `simulator.py` & `ev_optimizer.py`
- `MonteCarloSimulator`: Chia 39 lá bài chưa thấy cho 1 đến 3 đối thủ ảo (mô hình Random Legal, Heuristic hoặc Greedy).
- `EVOptimizer`: Sử dụng **Common Random Numbers (CRN)**. Tất cả các cách xếp ứng viên đều được thử thách trên cùng một bộ ván đấu ngẫu nhiên, giúp loại bỏ phương sai ngoại cảnh.
- Trả về: `mean_ev`, `std_dev`, `win_rate`, `scoop_rate`, `ci_95`.

---

## 3. CÁC BÀI KIỂM THỬ LIÊN QUAN

- `tests/test_card.py`: 10 tests kiểm tra thuộc tính, encoding ID $0..51$, parsing chuỗi, immutability.
- `tests/test_evaluator.py`: 14 tests kiểm tra phân cấp tay bài, so sánh tie-breakers, sảnh A-2-3-4-5, phát hiện bài lủng.
- `tests/test_rules.py`: 5 tests kiểm tra tính điểm đối đầu, bắt sập, phạt lủng, sảnh rồng, 6 đôi.
- `tests/test_solver.py`: 4 tests chứng minh tổng số 36,036 thế bài và tính toàn vẹn 13 quân.
- `tests/test_simulator.py`: 4 tests kiểm tra mô phỏng Monte Carlo, tính lặp lại của seed, EV ranking.
