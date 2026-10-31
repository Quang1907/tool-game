# CURRENT STATE — BINH 13 ANALYZER (macOS)

**Cập nhật lần cuối:** 2026-10-31  
**Trạng thái kiểm thử:** 149/149 tests PASSED (100%)  
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
| **Automation**      | `mouse_controller.py` (macOS CoreGraphics native events)   | `VERIFIED` | `test_auto_binh.py` passed                             |
| **Automation**      | `gesture_selector.py` (Weighted random & Bézier generator) | `VERIFIED` | `test_auto_binh.py` passed                             |
| **Automation**      | `move_planner.py` (Permutation cycles minimal swaps)       | `VERIFIED` | `test_auto_binh.py` passed                             |
| **Automation**      | `macro_recorder.py` (Real-time drag capture 60 Hz)         | `VERIFIED` | `test_auto_binh.py` passed                             |
| **Automation**      | `gesture_manager.py` (SQLite persistence & AutoBinhWorker) | `VERIFIED` | `test_auto_binh.py` passed                             |
| **Database**        | `db.py` & `repository.py` (Sessions, Slots, Gestures CRUD) | `VERIFIED` | `test_database.py` & `test_auto_binh.py` passed        |
| **Services**        | `analysis_service.py` & `simulation_service.py`            | `VERIFIED` | `test_integration.py` passed                           |
| **Services**        | `multi_window_service.py` (Tracking & Hash cache)          | `VERIFIED` | `test_multi_window.py` passed                          |
| **UI Layer**        | `main_window.py` (7 tabs, Tab 7 Tự động binh bài)          | `VERIFIED` | `test_ui.py` passed (7/7 tabs)                         |
| **UI Layer**        | `gesture_widget.py` (Tab 7 13x13 Matrix, Slot Editor)      | `VERIFIED` | `test_auto_binh.py` passed                             |
| **UI Layer**        | `multi_window_widget.py` (Nút Auto-Binh 3 cửa sổ)          | `VERIFIED` | `test_multi_window.py` passed                          |
| **UI Layer**        | `card_edit_dialog.py` (13 nút Rank, 4 Suit, Contradiction) | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **UI Layer**        | `vision_debug_dialog.py` (4 tab chẩn đoán)                 | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **UI Layer**        | `zoomable_viewer.py` (Zoom, Pan, Click Bbox)               | `VERIFIED` | `test_ui.py` passed                                    |
| **UI Layer**        | `card_reference_manager.py` (Quản lý 52 lá)                | `VERIFIED` | `test_ui.py` passed                                    |

---

## 2. NHỮNG GÌ VỪA ĐƯỢC TRIỂN KHAI VÀ HOÀN TẤT GẦN NHẤT

1. **Triển khai toàn diện Tab 7 ("7. Tự động binh bài & Cử chỉ") và Bộ điều khiển kéo chuột 156 cặp vị trí bài:**
   - **Quản lý 13 ô vị trí bài (`CardSlot`):** Chuẩn hóa tọa độ tương đối theo kích thước cửa sổ game $[0.0, 1.0]$. Hỗ trợ hộp thoại `SlotEditorDialog` chỉnh sửa trực quan tọa độ 3 Chi (3 Chi Đầu, 5 Chi Giữa, 5 Chi Cuối) và tự động lưu bền vững vào SQLite `data.db`.
   - **Quản lý ma trận 156 cặp vị trí có hướng ($13 \times 12$):** Bảng hiển thị 13x13 tương tác trực tiếp (`table_matrix`). Mỗi ô thể hiện số lượng mẫu cử chỉ đã lưu, gắn nhãn xanh `#30D158` nếu đã kiểm tra và xanh lam `#64D2FF` nếu chưa kiểm tra. Hỗ trợ xem chi tiết, test phát lại, đổi tên, thay đổi trọng số, nhân bản và xóa mẫu.
   - **Bộ chọn mẫu ngẫu nhiên (`GestureSelector`):** Hỗ trợ chọn ngẫu nhiên có trọng số (`weighted random`), lọc chỉ dùng mẫu đã kiểm tra, tránh lặp lại mẫu liên tiếp và cấu hình tốc độ kéo chuột / thời gian nghỉ giữa các lượt.
   - **Tự động sinh 156 đường cong Bézier tự nhiên:** Hàm `generate_natural_bezier_sample` sinh đường cong mượt mà theo thuật toán Cubic Bézier kèm gia tốc tự nhiên (Cubic ease-in-out) và độ rung vi mô mô phỏng tay người, giúp người dùng lập tức có đủ 156 mẫu chuẩn ngay lần đầu mở ứng dụng.
   - **Ghi macro chuột thực tế (`MacroRecorder`):** Bắt sự kiện chuột qua `CGEventSourceButtonState` và `QCursor.pos()` ở tần số 60 Hz, ghi nhận đường đi thực tế khi người dùng kéo thả trên cửa sổ game và chuẩn hóa về tọa độ tương đối.
   - **Lập kế hoạch hoán đổi tối ưu (`MovePlanner`):** Phân tích 13 quân bài hiện tại trên các ô bàn chơi so với thế bài tối ưu được giải bởi `Solver` $\rightarrow$ phân rã thành các chu trình hoán đổi tối thiểu (Disjoint Permutation Cycles), đảm bảo đưa 13 lá về đúng vị trí với số lượt kéo chuột ít nhất.
   - **Điều khiển chuột macOS native (`MouseController`):** Sử dụng `CoreGraphics` CGEvents qua `ctypes`, chuyển đổi tọa độ tương đối sang tọa độ màn hình thực tế, tích hợp cơ chế ngắt an toàn khẩn cấp (Failsafe) khi chuột di chuyển vào góc $(0, 0)$.
   - **Tích hợp Tab 6 ("Bot 3 Cửa Sổ"):** Bổ sung nút bấm `"⚡ Tự Động Binh Bài (Auto-Binh)"` trên từng panel cửa sổ. Khi đã phát hiện đủ 13 lá và có thế bài tối ưu, người dùng bấm nút này để hệ thống tự động kéo xếp bài trên cửa sổ game chạy ngầm trên `QThread` (`AutoBinhWorker`) mà không gây đơ lag giao diện.
   - **Kiểm thử tự động toàn diện:** Viết mới file `tests/test_auto_binh.py` gồm 8 test case kiểm tra Model, Database, MovePlanner, Selector, Bézier, MouseController và UI. Nâng tổng số test toàn dự án lên **138/138 PASSED (100%)**.
