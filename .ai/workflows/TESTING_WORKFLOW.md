# WORKFLOW: KIỂM THỬ VÀ ĐẢM BẢO CHẤT LƯỢNG (TESTING WORKFLOW)

Quy chuẩn và hướng dẫn kiểm thử toàn diện trên Binh 13 Analyzer.

---

## 1. NGUYÊN TẮC KIỂM THỬ BẤT BIẾN
1. **Never mock reality (Không bao giờ giả lập thực tế):**
   - Thuật toán tổ hợp, bộ đánh giá bài, pipeline nhận diện ảnh và SQLite database phải được kiểm thử trên dữ liệu thật và thuật toán thật.
   - Chỉ được dùng mock khi cần mô phỏng sự tương tác modal của người dùng trong headless test (như `QMessageBox.question` trả về `Yes`).
2. **Tính tất định (Determinism):**
   - Các bài test ngẫu nhiên (như xáo bài, Monte Carlo) bắt buộc phải truyền hạt giống (`seed`) cố định để đảm bảo kết quả luôn tái lập $100\%$.

---

## 2. CẤU TRÚC BỘ TEST SUITE VÀ LỆNH CHẠY

```text
tests/
├── test_card.py                        # 10 tests: Card, Rank, Suit, Deck, Hand
├── test_evaluator.py                   # 14 tests: Chi đầu, chi giữa, chi cuối, foul
├── test_rules.py                       # 5 tests: Tính điểm, bắt sập, phạt lủng, sảnh rồng
├── test_solver.py                      # 4 tests: 36,036 thế bài, bảo toàn 13 lá
├── test_simulator.py                   # 4 tests: Monte Carlo, CRN, tính EV
├── test_database.py                    # 1 test: SQLite session lifecycle
├── test_integration.py                 # 1 test: End-to-end analysis pipeline
├── test_multi_window.py                # 5 tests: Retina 2x crop, occlusion, tracker
├── test_ui.py                          # 5 tests: MainWindow, CardEditDialog, ReferenceManager
├── test_vision.py                      # 28 tests: Tiền xử lý, template matching, fanned cards
└── test_card_detection_and_reference.py # 25 tests: Test bắt buộc A-E, thư viện mẫu
```

### Các Lệnh Chạy Kiểm Thử:
- **Chạy toàn bộ 104 tests:**
  ```bash
  .venv/bin/pytest tests/
  ```
- **Chạy riêng phân hệ Thị giác & Thư viện mẫu:**
  ```bash
  .venv/bin/pytest tests/test_card_detection_and_reference.py -v
  ```
- **Chạy riêng phân hệ Giao diện người dùng:**
  ```bash
  .venv/bin/pytest tests/test_ui.py -v
  ```
- **Chạy riêng phân hệ Thuật toán & Solver:**
  ```bash
  .venv/bin/pytest tests/test_solver.py tests/test_evaluator.py -v
  ```

---

## 3. QUY TRÌNH KHI THÊM TEST CASE MỚI

1. Đặt tên hàm test rõ ràng: `test_<chức_năng>_<điều_kiện>_<kết_quả_mong_muốn>()`.
2. Tuân thủ mô hình **Arrange — Act — Assert**:
   - **Arrange:** Chuẩn bị quân bài, ảnh chụp hoặc đối tượng.
   - **Act:** Gọi hàm hoặc method cần kiểm thử.
   - **Assert:** Kiểm tra các giá trị trả về bằng `assert` tường minh.
3. Chạy test vừa viết và đảm bảo pass.
4. Cập nhật số lượng test vào [.ai/state/TEST_STATUS.md](file:///Users/levanquang/tool/.ai/state/TEST_STATUS.md).
