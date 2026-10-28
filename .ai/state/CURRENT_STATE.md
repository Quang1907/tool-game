# CURRENT STATE — BINH 13 ANALYZER (macOS)

**Cập nhật lần cuối:** 2026-10-29  
**Trạng thái kiểm thử:** 128/128 tests PASSED (100%)  
**Môi trường thực thi:** Python 3.11.17 (`.venv`), macOS Sequoia 15.4.1 (ARM64 Apple Silicon)

---

## 1. BẢNG TRẠNG THÁI CÁC PHÂN HỆ

| Phân hệ             | Thành phần                                                | Trạng thái | Bằng chứng xác minh                                    |
| ------------------- | --------------------------------------------------------- | :--------: | ------------------------------------------------------ |
| **Domain Core**     | `card.py` (Rank, Suit, Card, Deck, Hand)                  | `VERIFIED` | `test_card.py` (10 tests passed)                       |
| **Domain Core**     | `evaluator.py` (3-card, 5-card, Foul detection)           | `VERIFIED` | `test_evaluator.py` (14 tests passed)                  |
| **Domain Core**     | `rules.py` (Scoring, Scoop, Penalties, Special hands)     | `VERIFIED` | `test_rules.py` (5 tests passed)                       |
| **Domain Core**     | `solver.py` (36,036 partitions, pruning, solve_heuristic) | `VERIFIED` | `test_solver.py` (4 tests passed, toán học chứng minh) |
| **Domain Core**     | `collaborative_analyzer.py` (4th hand deduction & counter)| `VERIFIED` | `test_collaborative_analyzer.py` (4 tests passed)      |
| **Domain Core**     | `simulator.py` & `ev_optimizer.py` (Monte Carlo CRN)      | `VERIFIED` | `test_simulator.py` (4 tests passed)                   |
| **Vision Pipeline** | `screen_capture.py` (macOS Retina 2x & CGWindowID direct) | `VERIFIED` | `test_vision.py` & `test_multi_window.py` passed       |
| **Vision Pipeline** | `image_preprocessor.py` (Warp 120x168, green border)      | `VERIFIED` | `test_vision.py` passed                                |
| **Vision Pipeline** | `card_detector.py` (Candidate validation, NMS, Fanned)    | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `card_recognizer.py` (Decoupled Rank/Suit, Face Card isolation)| `VERIFIED` | `test_card_detection_and_reference.py` passed (100% user refs) |
| **Vision Pipeline** | `template_engine.py` (Topological loop & Rank analysis)  | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `card_reference_library.py` (SQLite Ground-truth)         | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `roi_manager.py` & `window_manager.py` (3 Windows)        | `VERIFIED` | `test_multi_window.py` (9 tests passed)                |
| **Database**        | `db.py` & `repository.py` (Sessions, References CRUD)     | `VERIFIED` | `test_database.py` (1 test passed)                     |
| **Services**        | `vision_service.py` (`recognize_cards_pipeline` unified)  | `VERIFIED` | `test_multi_window.py` & `test_vision.py` passed       |
| **Services**        | `multi_window_service.py` (Unified recognition & Hash cache)| `VERIFIED` | `test_multi_window.py` passed                          |
| **UI Layer**        | `main_window.py` (Shared vision pipeline instances)       | `VERIFIED` | `test_multi_window.py` & `test_ui.py` passed           |
| **UI Layer**        | `card_edit_dialog.py` (13 nút Rank, 4 Suit, Grid 52 lá)  | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **UI Layer**        | `vision_debug_dialog.py` (4 tab chẩn đoán)                | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **UI Layer**        | `zoomable_viewer.py` (Zoom, Pan, Click Bbox)              | `VERIFIED` | `test_ui.py` passed                                    |
| **UI Layer**        | `card_reference_manager.py` (Quản lý 52 lá, no ghosting)  | `VERIFIED` | `test_ui.py` passed                                    |
| **UI Layer**        | `multi_window_widget.py` (Unified pipeline, Ref manager)   | `VERIFIED` | `test_multi_window.py` passed                          |

---

## 2. NHỮNG GÌ VỪA ĐƯỢC SỬA VÀ HOÀN TẤT GẦN NHẤT

1. **Hợp nhất quy trình nhận diện lá bài (Unified Recognition Pipeline) giữa Tab 2 và Tab 6:**
   - **Bản chất nguyên nhân lệch kết quả:** Tab 6 trước đây khởi tạo `CardRecognizer` độc lập (không nạp các ảnh mẫu đã lưu/xác nhận ở Tab 2), đồng thời gọi `recognize_all(crops)` trực tiếp mà không qua bộ lọc candidate validation loại bỏ vật thể giao diện. Khi quét cửa sổ game có nút bấm/chip/avatar, các vùng này bị đoán mò thành lá bài có độ tin cậy thấp, làm sai lệch bộ 13 lá.
   - **Hàm chuẩn hóa chung `recognize_cards_pipeline` ([vision_service.py](file:///Users/levanquang/tool/app/services/vision_service.py)):** Đóng gói trọn vẹn quy trình: phát hiện vật thể bài (`detect_card_objects`), nhận diện decoupled Rank/Suit (`recognize_crop`), lọc chặt chẽ $rank\_conf \ge 0.65$ & $suit\_conf \ge 0.65$, loại trừ `NON_CARD_OBJECT`, khử trùng lặp và xác lập trạng thái `CONFIRMED`.
   - **Chia sẻ chung thư viện ảnh mẫu ([main_window.py](file:///Users/levanquang/tool/app/ui/main_window.py)):** `MainWindow` truyền trực tiếp `tab_vision.detector`, `tab_vision.recognizer`, và `tab_vision.reference_library` vào `MultiWindowWidget`. Bất kỳ ảnh mẫu nào được người dùng lưu ở Tab 2 sẽ có hiệu lực ngay lập tức tại Tab 6 mà không cần khởi động lại app.
   - **Nút "📚 Thư viện ảnh mẫu" trong Tab 6:** Cho phép người dùng duyệt và quản lý 52 lá bài mẫu trực tiếp ngay trên giao diện Tab 6.
   - **Xác minh kiểm thử:** Bổ sung test `test_shared_vision_pipeline_and_reference_library`, nâng tổng số test lên **128/128 tests PASSED (100%)**.

2. **Khắc phục triệt để lỗi nhận diện các quân bài hình ảnh (J, Q, K / Tây) bị nhầm chất (vd: Q♠ nhầm thành Q♦ 91%, QC nhầm thành QD, KC nhầm thành KH):**
   - **Bản chất nguyên nhân:** Trên bài Tây, trang phục hoàng gia và chân dung ở trung tâm chứa rất nhiều họa tiết thêu chỉ đỏ và vàng bắt đầu từ $x \ge 25, y \ge 40$. Thuật toán tách patch góc `extract_dynamic_corner_patches` trước đây sắp xếp diện tích giảm dần nên đã chọn nhầm trang phục chân dung (diện tích $>700$) thay vì suit pip góc (diện tích $100-350$), khiến quân bài đen như Q♠, QC, KC bị kiểm tra ra màu đỏ (`check_image_is_red = True`) và ép nhận diện thành chất đỏ (Rô ♦, Cơ ♥).
   - **Thuật toán cô lập Suit Pip góc chuẩn xác:** Ràng buộc chặt chẽ suit pip phải nằm trong cột biên lề góc ($x < 38, y \in [45, 98]$) và thẳng hàng theo trục dọc với Rank glyph ($|center\_x_{suit} - center\_x_{rank}| \le 8$), nằm ngay phía dưới Rank glyph. Áp dụng hàm phạt nặng khoảng cách ngang và phạt các vùng đồ họa chân dung quá khổ ($w > 30, h > 35, area > 550$). Kết quả: 100% quân bài J, Q, K trích xuất chính xác suit pip góc chuẩn 28x28.
   - **Bảo toàn tính toàn vẹn màu sắc (Color Integrity):** Trong `card_recognizer.py` và `card_reference_library.py`: Nếu Rank glyph là màu đen (`check_image_is_red(rank_crop) == False`), quân bài KHÔNG BAO GIỜ bị coi là chất đỏ, loại bỏ hoàn toàn hiện tượng nhiễm màu đỏ từ chân dung.
   - **Xác minh thực tế 96/96 ảnh mẫu (100.0%):** Kiểm tra đối chiếu toàn bộ 96 ảnh mẫu người dùng đã xác nhận trong thư viện, tất cả quân bài J, Q, K và số đều đạt độ chính xác 100.0% và khớp mẫu [Mẫu].

2. **Triệt tiêu lỗi giao diện hiển thị đè quân bài 2 Bích (2♠) trên tất cả các ô:**
   - **Bản chất nguyên nhân:** Khi làm mới layout danh sách (`while layout.count(): item = layout.takeAt(0); item.widget().deleteLater()`), trong PySide6/Qt việc gọi `deleteLater()` chỉ xếp lịch xóa ở event loop tiếp theo và KHÔNG hề tự động ngắt widget khỏi widget cha (`parent()`). Do đó khi người dùng bấm chọn 2♠ rồi bấm sang lá khác (như J♦), widget 2♠ cũ vẫn hiển thị đè ở vị trí cũ bên trong container.
   - **Sửa triệt để:** Bổ sung `w.setParent(None)` và `w.hide()` trước `w.deleteLater()` tại tất cả các vị trí dọn dẹp layout (`card_reference_manager.py`, `vision_widget.py`, `multi_window_widget.py`).

3. **Hiển thị rõ ràng ký tự Rank trong lưới 52 lá của CardEditDialog:**
   - Thêm `padding: 0;` vào stylesheet của 52 nút lá bài trong `CardEditDialog` để không bị đè bởi padding mặc định `padding: 7px 16px;` của macOS QPushButton làm co hẹp ký tự rank bên trong.

4. **Bổ sung `TestFaceCardsRecognitionAndGhostWidgetFix`:** Nâng tổng số test toàn dự án lên **127/127 PASSED (100%)**.
