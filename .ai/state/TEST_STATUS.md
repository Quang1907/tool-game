# TEST STATUS & VERIFICATION REPORT — BINH 13 ANALYZER

**Thời điểm kiểm tra gần nhất:** 2026-10-30 09:44:00 +09:00  
**Lệnh thực thi:** `.venv/bin/pytest tests/`  
**Kết quả chung:** **144 / 144 tests PASSED (100%)**  
**Thời gian chạy:** 32.51 giây  
**Nền tảng:** macOS Sequoia 15.4.1 (ARM64 Apple Silicon) | Python 3.11.17

---

## 1. BẢNG PHÂN BỔ KẾT QUẢ THEO FILE TEST

| File Test                                    | Số test |    Kết quả    | Trọng tâm kiểm thử                                                                      |
| -------------------------------------------- | :-----: | :-----------: | --------------------------------------------------------------------------------------- |
| `tests/test_card.py`                         |   10    | **10 PASSED** | Giá trị Card, Rank, Suit, Deck xáo bài, Hand parsing chuỗi                              |
| `tests/test_evaluator.py`                    |   14    | **14 PASSED** | Đánh giá Chi Đầu (3 lá), Chi Giữa/Cuối (5 lá), kiểm tra Foul                            |
| `tests/test_rules.py`                        |    5    | **5 PASSED**  | Tính điểm đối đầu, bắt sập 1 người, sập làng, phạt lủng, sảnh rồng                      |
| `tests/test_solver.py`                       |    4    | **4 PASSED**  | Khảo sát 36,036 thế bài, bảo toàn 13 quân bài, loại bài lủng                            |
| `tests/test_collaborative_analyzer.py`       |    4    | **4 PASSED**  | Suy luận 13 lá đối thủ, giải thế bài đối thủ, tối ưu phản công                          |
| `tests/test_simulator.py`                    |    4    | **4 PASSED**  | Mô phỏng Monte Carlo, CRN tính EV, xếp hạng thế bài                                     |
| `tests/test_database.py`                     |    1    | **1 PASSED**  | Vòng đời Session SQLite, CRUD lịch sử ván bài                                           |
| `tests/test_integration.py`                  |    1    | **1 PASSED**  | Luồng tích hợp End-to-End từ bài nạp đến giải và mô phỏng                               |
| `tests/test_multi_window.py`                 |    9    | **9 PASSED**  | Quản lý 3 cửa sổ bàn chơi, Retina 2x crop, CGWindowID direct capture, selection preview |
| `tests/test_ui.py`                           |    5    | **5 PASSED**  | MainWindow (7 tabs), CardEditDialog, CardReferenceManager, ZoomableImageViewer         |
| `tests/test_vision.py`                       |   28    | **28 PASSED** | Xử lý ảnh, template matching, NMS, tách bài xòe, 9 mẫu bài thực tế                      |
| `tests/test_card_detection_and_reference.py` |   42    | **42 PASSED** | Bộ test bắt buộc, 6♥/5♥, màu Đen/Đỏ, cô lập J/Q/K, chống ghosting 2♠, 2♠ vs 2♣, subpixel shift |
| `tests/test_auto_binh.py`                    |   14    | **14 PASSED** | Slot models, 156-pair CRUD, MovePlanner, Bézier, Visual 13-board, Wizard, Trajectory Warp, Window Activate, Shrunk Bounds Invariance |

---

## 2. BẰNG CHỨNG XÁC MINH CÁC TEST CASE BẮT BUỘC (MANDATORY TEST SUITE)

Trong file `tests/test_card_detection_and_reference.py`:

- **Test A (`test_a_avatar_not_recognized_as_card_and_no_fake_kd`):**  
  Nạp ảnh avatar người chơi hình vuông có khuôn mặt $\rightarrow$ Detector trả về `NON_CARD_OBJECT` $\rightarrow$ Recognizer trả về `card=None, confidence=0.0`. Không dự đoán `KD` hay card code giả.
- **Test B (`test_b_rank_buttons_all_13_visible_and_independent_selection`):**  
  Xác minh đủ 13 nút Rank `A, 2, 3..10, J, Q, K` có text hiển thị đầy đủ, không bị clipping; click chọn Rank Q giữ nguyên Suit Rô.
- **Test C (`test_c_suit_buttons_all_4_visible_and_independent_selection`):**  
  Xác minh đủ 4 nút Suit `♠♣♦♥`; click chọn Suit Cơ giữ nguyên Rank Q.
- **Test D (`test_d_crop_coordinates_unification_with_original_frame`):**  
  Xác minh bounding box của lá bài và mảng pixel `raw_patch` khớp chính xác 100% với frame gốc của bàn chơi.
- **Test E (`test_e_confirmation_safety_and_no_saving_non_card_objects`):**  
  Cố tình bấm lưu mẫu từ đối tượng `NON_CARD_OBJECT` $\rightarrow$ bị hệ thống chặn với cảnh báo, không ghi vào database; đóng dialog không làm thay đổi dữ liệu.
