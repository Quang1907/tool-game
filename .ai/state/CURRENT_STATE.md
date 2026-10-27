# CURRENT STATE — BINH 13 ANALYZER (macOS)

**Cập nhật lần cuối:** 2026-10-27  
**Trạng thái kiểm thử:** 113/113 tests PASSED (100%)  
**Môi trường thực thi:** Python 3.11.17 (`.venv`), macOS Sequoia 15.4.1 (ARM64 Apple Silicon)

---

## 1. BẢNG TRẠNG THÁI CÁC PHÂN HỆ

| Phân hệ             | Thành phần                                                | Trạng thái | Bằng chứng xác minh                                    |
| ------------------- | --------------------------------------------------------- | :--------: | ------------------------------------------------------ |
| **Domain Core**     | `card.py` (Rank, Suit, Card, Deck, Hand)                  | `VERIFIED` | `test_card.py` (10 tests passed)                       |
| **Domain Core**     | `evaluator.py` (3-card, 5-card, Foul detection)           | `VERIFIED` | `test_evaluator.py` (14 tests passed)                  |
| **Domain Core**     | `rules.py` (Scoring, Scoop, Penalties, Special hands)     | `VERIFIED` | `test_rules.py` (5 tests passed)                       |
| **Domain Core**     | `solver.py` (36,036 partitions, pruning)                  | `VERIFIED` | `test_solver.py` (4 tests passed, toán học chứng minh) |
| **Domain Core**     | `simulator.py` & `ev_optimizer.py` (Monte Carlo CRN)      | `VERIFIED` | `test_simulator.py` (4 tests passed)                   |
| **Vision Pipeline** | `screen_capture.py` (macOS Retina 2x)                     | `VERIFIED` | `test_vision.py` & `test_multi_window.py` passed       |
| **Vision Pipeline** | `image_preprocessor.py` (Warp 120x168, green border)      | `VERIFIED` | `test_vision.py` passed                                |
| **Vision Pipeline** | `card_detector.py` (Candidate validation, NMS, Fanned)    | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `card_recognizer.py` (Decoupled Rank/Suit matching)       | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `template_engine.py` (Topological loop & Rank analysis)  | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `card_reference_library.py` (SQLite Ground-truth)         | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `roi_manager.py` & `window_manager.py` (3 Windows)        | `VERIFIED` | `test_multi_window.py` (5 tests passed)                |
| **Database**        | `db.py` & `repository.py` (Sessions, References CRUD)     | `VERIFIED` | `test_database.py` (1 test passed)                     |
| **Services**        | `analysis_service.py` & `simulation_service.py`           | `VERIFIED` | `test_integration.py` passed                           |
| **Services**        | `multi_window_service.py` (Tracking & Hash cache)         | `VERIFIED` | `test_multi_window.py` passed                          |
| **UI Layer**        | `main_window.py` (5 main tabs)                            | `VERIFIED` | `test_ui.py` passed, khởi chạy app thành công          |
| **UI Layer**        | `card_edit_dialog.py` (13 nút Rank, 4 Suit, Contradiction)| `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **UI Layer**        | `vision_debug_dialog.py` (4 tab chẩn đoán)                | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **UI Layer**        | `zoomable_viewer.py` (Zoom, Pan, Click Bbox)              | `VERIFIED` | `test_ui.py` passed                                    |
| **UI Layer**        | `card_reference_manager.py` (Quản lý 52 lá)               | `VERIFIED` | `test_ui.py` passed                                    |

---

## 2. NHỮNG GÌ VỪA ĐƯỢC SỬA VÀ HOÀN TẤT GẦN NHẤT

1. **Khắc phục lỗi nhận diện 6 Cơ (6♥) thành 5 Cơ (5♥) và lưu nhầm mẫu:**
   - **Phân tích hình học & topo ký tự số trong `template_engine.py`:** Thêm trích xuất và phân tích vòng khép kín (closed loops/holes qua `cv2.RETR_CCOMP`). Chữ số '6' bắt buộc có lỗ khép kín ở nửa dưới ($y \ge 0.40$), trong khi '5' không có lỗ khép kín nào. Đồng thời căn giữa ký tự (center alignment) thay vì dồn trái, chấm dứt tình trạng số 6 bị match nhầm thành số 5 với độ tin cậy 97%.
   - **Xóa bỏ mã tự động ghi đè nhãn (auto-healing) trong `card_reference_library.py`:** Loại bỏ hoàn toàn khối lệnh tự ý cập nhật nhãn trong `_add_to_cache`, đảm bảo nhãn do người dùng xác nhận và lưu vào SQLite luôn có hiệu lực tối cao, không bao giờ bị ghi đè ngầm.
   - **Di chuyển & sửa bản ghi mẫu bị nhiễm độc trong SQLite (`data.db`):** Đã sửa bản ghi `1499111f-9cce-46f2-83a5-3cf6e4dce15c` từ `card_code='5H'` thành `card_code='6H'`, đổi tên file ảnh tương ứng.
   - **Thêm `CardContradictionDialog` trong `card_edit_dialog.py`:** Hiển thị cảnh báo trực quan đa chiều nếu có xung đột rank, bảo vệ an toàn thư viện mẫu khi người dùng xác nhận hoặc lưu ảnh.
   - **Bổ sung Suite 9 bài kiểm thử hồi quy `TestSavedCardReferenceLabelMismatchRegression`** trong `tests/test_card_detection_and_reference.py`, nâng tổng số test suite lên 113/113 PASSED.
