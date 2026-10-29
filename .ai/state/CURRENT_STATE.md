# CURRENT STATE — BINH 13 ANALYZER (macOS)

**Cập nhật lần cuối:** 2026-10-29  
**Trạng thái kiểm thử:** 129/129 tests PASSED (100%)  
**Môi trường thực thi:** Python 3.11.17 (`.venv`), macOS Sequoia 15.4.1 (ARM64 Apple Silicon)

---

## 1. BẢNG TRẠNG THÁI CÁC PHÂN HỆ

| Phân hệ             | Thành phần                                                 | Trạng thái | Bằng chứng xác minh                                    |
| ------------------- | ---------------------------------------------------------- | :--------: | ------------------------------------------------------ |
| **Domain Core**     | `card.py` (Rank, Suit, Card, Deck, Hand)                   | `VERIFIED` | `test_card.py` (10 tests passed)                       |
| **Domain Core**     | `evaluator.py` (3-card, 5-card, Foul detection)            | `VERIFIED` | `test_evaluator.py` (14 tests passed)                  |
| **Domain Core**     | `rules.py` (Scoring, Scoop, Penalties, Special hands)      | `VERIFIED` | `test_rules.py` (5 tests passed)                       |
| **Domain Core**     | `solver.py` (36,036 partitions, pruning)                   | `VERIFIED` | `test_solver.py` (4 tests passed, toán học chứng minh) |
| **Domain Core**     | `simulator.py` & `ev_optimizer.py` (Monte Carlo CRN)       | `VERIFIED` | `test_simulator.py` (4 tests passed)                   |
| **Vision Pipeline** | `screen_capture.py` (macOS Retina 2x & CGWindowID direct)  | `VERIFIED` | `test_vision.py` & `test_multi_window.py` passed       |
| **Vision Pipeline** | `image_preprocessor.py` (Warp 120x168, green border)       | `VERIFIED` | `test_vision.py` passed                                |
| **Vision Pipeline** | `card_detector.py` (Candidate validation, NMS, Fanned)     | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `card_recognizer.py` (Decoupled Rank/Suit matching)        | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `template_engine.py` (Topological loop & Rank analysis)    | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `card_reference_library.py` (SQLite Ground-truth)          | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `roi_manager.py` & `window_manager.py` (3 Windows)         | `VERIFIED` | `test_multi_window.py` (7 tests passed)                |
| **Database**        | `db.py` & `repository.py` (Sessions, References CRUD)      | `VERIFIED` | `test_database.py` (1 test passed)                     |
| **Services**        | `analysis_service.py` & `simulation_service.py`            | `VERIFIED` | `test_integration.py` passed                           |
| **Services**        | `multi_window_service.py` (Tracking & Hash cache)          | `VERIFIED` | `test_multi_window.py` passed                          |
| **UI Layer**        | `main_window.py` (6 tabs, tab 6 Bot 3 Cửa Sổ)              | `VERIFIED` | `test_ui.py` passed, khởi chạy app thành công          |
| **UI Layer**        | `card_edit_dialog.py` (13 nút Rank, 4 Suit, Contradiction) | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **UI Layer**        | `vision_debug_dialog.py` (4 tab chẩn đoán)                 | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **UI Layer**        | `zoomable_viewer.py` (Zoom, Pan, Click Bbox)               | `VERIFIED` | `test_ui.py` passed                                    |
| **UI Layer**        | `card_reference_manager.py` (Quản lý 52 lá)                | `VERIFIED` | `test_ui.py` passed                                    |
| **UI Layer**        | `multi_window_widget.py` (Direct capture, auto solve)      | `VERIFIED` | `test_multi_window.py` passed                          |

---

## 2. NHỮNG GÌ VỪA ĐƯỢC SỬA VÀ HOÀN TẤT GẦN NHẤT

1. **Khắc phục lỗi Tab 6 ("Bot 3 Cửa Sổ") không lấy được ảnh từ cửa sổ, báo "Cửa sổ bị che (Occluded)" vô tận, không hiện lá bài và không hiện gợi ý xếp bài:**
   - **Chụp ảnh trực tiếp từ macOS Window ID (CGWindowID Direct Capture):** Thêm phương thức `ScreenCapture.capture_window_by_id(window_id)` sử dụng macOS `/usr/sbin/screencapture -l <window_id> -o -x`. Cho phép chụp chính xác cửa sổ game được chỉ định kể cả khi cửa sổ Binh 13 Analyzer hay cửa sổ khác đang đè lên trước mặt.
   - **Sửa lỗi lệch Window ID và Occlusion:** `WindowROI` trước đây truyền nhầm số thứ tự panel (`idx=1,2,3`) làm `window_id`, khiến thuật toán `compute_occlusion` không tìm thấy cửa sổ trên hệ thống và mặc định coi như bị che 100%. Đã bổ sung trường `cg_window_id` vào `WindowROI` và kết nối trực tiếp với macOS CGWindowID. Đồng thời loại trừ ứng dụng "Binh 13 Analyzer" khỏi danh sách các cửa sổ gây che khuất cửa sổ game.
   - **Xác nhận tức thì khi chọn cửa sổ trong Dropdown:** Kết nối sự kiện `combo_w1/w2/w3.currentIndexChanged` với hàm `_on_window_selected`. Ngay khi người dùng chọn một cửa sổ trong danh sách, hệ thống chụp ngay cửa sổ đó, cập nhật ảnh vào Viewer, tự động chạy nhận diện lá bài hiển thị trên thanh thumbnail, và giải bài đưa ra gợi ý xếp bài tối ưu (Chi Đầu, Chi Giữa, Chi Cuối).
   - **Tối ưu danh sách phát hiện cửa sổ macOS:** Cập nhật helper Swift `macos_window_helper.swift` lọc bỏ chính cửa sổ Binh 13 Analyzer và các tiến trình daemon hệ thống không có giao diện.
   - **Bổ sung `TestDirectWindowCaptureAndSelection` và cập nhật `tests/conftest.py`:** Nâng tổng số test toàn dự án lên **119/119 PASSED (100%)**.

2. **Khắc phục lỗi crash `AttributeError: 'Solver' object has no attribute 'solve_heuristic'` và cảnh báo font:**
   - **Bổ sung phương thức `solve_heuristic` trong [solver.py](file:///Users/levanquang/tool/app/core/solver.py):** Phương thức ủy quyền cho `solve()` trả về danh sách các thế bài hợp lệ được sắp xếp theo heuristic score tối ưu nhất.
   - **Bổ sung bọc an toàn `try...except`:** Cả trong [multi_window_widget.py](file:///Users/levanquang/tool/app/ui/components/multi_window_widget.py) và [multi_window_service.py](file:///Users/levanquang/tool/app/services/multi_window_service.py) khi giải bài, đảm bảo không bao giờ làm crash tiến trình ứng dụng hay QThread nếu có bất thường.
   - **Triệt tiêu cảnh báo font Qt `SF Pro Text`:** Thay thế `SF Pro Text` bằng native macOS font alias `.AppleSystemUIFont` trong [styles.py](file:///Users/levanquang/tool/app/ui/styles.py) và [card_widget.py](file:///Users/levanquang/tool/app/ui/components/card_widget.py), tăng tốc độ khởi tạo GUI và loại bỏ 100% cảnh báo font.
   - **Bổ sung thuộc tính `code` vào class [Card](file:///Users/levanquang/tool/app/core/card.py):** Cho phép truy xuất mã chuỗi thuận tiện (`short_name`).
