# CURRENT STATE — BINH 13 ANALYZER (macOS)

**Cập nhật lần cuối:** 2026-11-11  
**Trạng thái kiểm thử:** 168/168 tests PASSED (100%)  
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
| **Vision Pipeline** | `layout_analyzer.py` (Bố cục 3-5-5, Khôi phục & Khử trùng) | `VERIFIED` | `test_layout_355.py` (7 tests passed)                  |
| **Vision Pipeline** | `template_engine.py` (Topological loop & Rank analysis)    | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `card_reference_library.py` (SQLite Ground-truth)          | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `roi_manager.py` & `window_manager.py` (3 Windows)         | `VERIFIED` | `test_multi_window.py` (13 tests passed)               |
| **Automation**      | `mouse_controller.py` (macOS CoreGraphics native events)   | `VERIFIED` | `test_auto_binh.py` passed                             |
| **Automation**      | `gesture_selector.py` (Weighted random & Bézier generator) | `VERIFIED` | `test_auto_binh.py` passed                             |
| **Automation**      | `move_planner.py` (Permutation cycles minimal swaps)       | `VERIFIED` | `test_auto_binh.py` passed                             |
| **Automation**      | `macro_recorder.py` (Real-time drag capture 60 Hz)         | `VERIFIED` | `test_auto_binh.py` passed                             |
| **Automation**      | `gesture_manager.py` (SQLite persistence & AutoBinhWorker) | `VERIFIED` | `test_auto_binh.py` passed                             |
| **Database**        | `db.py` & `repository.py` (Sessions, Slots, Gestures CRUD) | `VERIFIED` | `test_database.py` & `test_auto_binh.py` passed        |
| **Services**        | `analysis_service.py` & `simulation_service.py`            | `VERIFIED` | `test_integration.py` passed                           |
| **Services**        | `multi_window_service.py` (Tracking & Hash cache)          | `VERIFIED` | `test_multi_window.py` passed                          |
| **UI Layer**        | `main_window.py` (7 tabs, Tab 6 Chọn 1-3 Màn hình)        | `VERIFIED` | `test_ui.py` passed (7/7 tabs)                         |
| **UI Layer**        | `gesture_widget.py` (Tab 7 13x13 Matrix, Slot Editor)      | `VERIFIED` | `test_auto_binh.py` passed                             |
| **UI Layer**        | `multi_window_widget.py` (Chọn 1/2/3 màn hình chống rối)  | `VERIFIED` | `test_multi_window.py` & `test_auto_binh.py` passed   |
| **UI Layer**        | `card_edit_dialog.py` (13 nút Rank, 4 Suit, Contradiction) | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **UI Layer**        | `vision_debug_dialog.py` (4 tab chẩn đoán)                 | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **UI Layer**        | `zoomable_viewer.py` (Zoom, Pan, Click Bbox)               | `VERIFIED` | `test_ui.py` passed                                    |
| **UI Layer**        | `card_reference_manager.py` (Quản lý 52 lá)                | `VERIFIED` | `test_ui.py` passed                                    |

---

## 2. NHỮNG GÌ VỪA ĐƯỢC TRIỂN KHAI VÀ HOÀN TẤT GẦN NHẤT

1. **Triển khai Tính năng Chọn 1, 2 hoặc 3 Màn hình & Tối ưu Giao diện Chống Rối Mắt (Anti-Clutter Screen Selector):**
   - **Màn hình Lựa chọn Ban đầu (`ScreenSelectionWidget`):**
     - Khi mở Tab 6, hệ thống hiển thị màn hình chọn số lượng màn hình trực quan với 3 Card thiết kế chuẩn macOS HIG:
       - **1 Màn hình:** Chế độ tập trung 1 bàn duy nhất, phóng to hình ảnh tối đa, ẩn toàn bộ khung thừa chống rối mắt.
       - **2 Màn hình:** Giao diện chia đôi 50/50 cân đối, tự động binh luân phiên 2 bàn, ẩn bàn 3 và bảng đối thủ.
       - **3 Màn hình:** Chế độ tối đa 3 bàn, tự động suy luận 13 lá đối thủ #4 và tối ưu hóa thế bài bắt sập.
     - Sau khi người dùng nhấn chọn số màn hình tương ứng, giao diện Dashboard làm việc mới xuất hiện theo đúng lựa chọn.
   - **Tối ưu hóa Giao diện Dashboard Theo Số Màn Hình Đã Chọn:**
     - **Chế độ 1 Màn hình:**
       - Tự động ẩn 2 combo box `Cửa sổ 2` và `Cửa sổ 3`.
       - Mở rộng kích thước Panel 1 chiếm 100% chiều rộng, tăng chiều cao xem bài lên 240-340px giúp nhìn bài cực kỳ rõ nét.
       - Tự động ẩn khung "Khắc chế đối thủ #4" trên Panel 1 và ẩn toàn bộ `OpponentDeductionPanel` ở đáy màn hình.
       - Nút thao tác chuyển thành `▶ Bắt đầu quét 1 cửa sổ` và `⚡ Tự Động Binh Bài`.
     - **Chế độ 2 Màn hình:**
       - Tự động ẩn combo box `Cửa sổ 3`, hiển thị combo 1 & 2.
       - Hiển thị Panel 1 và Panel 2 chia đôi 50/50, ẩn Panel 3.
       - Ẩn khung đối thủ #4 vì 2 bàn không đủ 39 lá để suy luận đối thủ #4.
       - Nút thao tác chuyển thành `▶ Bắt đầu quét 2 cửa sổ` và `⚡ Binh bài cả 2 bàn (Luân phiên)`.
     - **Chế độ 3 Màn hình:**
       - Hiển thị đầy đủ 3 combo box, 3 panels và bảng suy luận đối thủ #4.
   - **Bộ Điều khiển Chuyển Đổi Nhanh trên Toolbar:**
     - Nút `[ 🔙 Đổi số màn ]` cho phép quay lại màn hình chọn bất kỳ lúc nào.
     - Cụm nút chuyển nhanh `[ 1 Màn ] [ 2 Màn ] [ 3 Màn ]` trên thanh công cụ cho phép đổi chế độ tức thời mà không cần rời khỏi màn hình làm việc.
   - **Kiểm thử tự động:**
     - Bổ sung 4 test case chuyên sâu trong `tests/test_multi_window.py`.
     - Toàn bộ 166/166 test case dự án chạy thật và **PASSED 100%**.

1. **Chuẩn hóa Bố cục Bài Binh 13 lá (3 - 5 - 5) & Thuật toán Phục hồi Lá bài Thiếu (`Layout355Analyzer`):**
   - **Phân cụm 3 Chi tự động:** Chi 1 (3 lá), Chi 2 (5 lá), Chi 3 (5 lá) dựa trên tọa độ Y và phân bổ không gian.
   - **Xác định vị trí lá bài bị thiếu (`infer_missing_slot_bboxes`):** Phân tích bước nhảy ngang $\Delta X$ và khoảng cách dọc $\Delta Y$, tính toán chính xác bounding box $(x, y, w, h)$ tại các khe hở nội tại (internal gap) hoặc vị trí biên (edge extrapolation).
   - **Xác minh con bài thực tế trên bàn chơi (`verify_and_crop_missing_card`):** Cắt trực tiếp vùng bài từ frame ảnh, chạy Candidate Validation (tỷ lệ trắng/sáng $\ge 18\%$), loại bỏ nền nỉ xanh, không đoán mò hay ép tạo bài giả. Nhận diện độc lập Rank/Suit và phục hồi lá bài vào danh sách.
   - **Khử trùng lặp và triệt tiêu đọc sai (`resolve_duplicate_cards`):** Khi phát hiện bài trùng lặp (ví dụ hai lá $7♣$), lá có độ tin cậy cao hơn giữ nguyên, lá còn lại được đối chiếu qua `alternative_candidates` và so khớp với 39 lá còn lại chưa xuất hiện trong bộ bài để gán lại chính xác.
   - **Gán nhãn Slots 1..13:** Tự động đánh số thứ tự từ 1 đến 13 cho từng quân bài, tương thích tuyệt đối với `MovePlanner` và `Evaluator`.
   - **Bảo toàn 100% kiểm thử:** Thêm mới `test_layout_355.py` (7 tests). Nâng tổng số test toàn dự án lên **162/162 tests PASSED (100%)** trong 35.73 giây.

1. **Triển khai Bộ điều khiển Chu kỳ Ván bài (Round Timing) & Cơ chế Khóa cứng sau khi Binh (Post-Binh Cooldown Lockdown):**
   - **Giao diện cấu hình Chu kỳ Ván bài:** Bổ sung thanh điều khiển `timing_bar` trên Tab 6 (Bot 3 Cửa Sổ) với:
     - `spin_round_time`: `⏱ Thời gian ván:` (10s – 180s, mặc định `45s`), kiểm soát thời gian diễn ra 1 hiệp binh bài.
     - `spin_cooldown`: `⏳ Thời gian chờ ván mới:` (5s – 120s, mặc định `20s`), kiểm soát thời gian game so bài, trả thưởng và dọn bàn.
     - `btn_reset_wait`: Nút `"🔓 Mở khóa tất cả chờ"` cho phép người dùng mở khóa cưỡng chế ngay lập tức khi muốn thử nghiệm nhanh.
   - **Cơ chế Khóa cứng Chuột 100% (Absolute Hard Lockdown):** Ngay sau khi hệ thống hoàn tất binh bài trên một bàn chơi:
     - Tự động tính toán tổng thời gian khóa: `Total Lock = (Thời gian ván - Thời gian đã xếp) + Thời gian chờ`.
     - Kích hoạt bộ đếm ngược thời gian thực `_cooldown_timer` (1Hz) cập nhật trạng thái trực quan: `⏳ ĐÃ BINH XONG VÁN #N — Khóa đợi ván mới (còn Xs)...` và nút bấm chuyển thành `⏳ Chờ ván mới (Xs)` ở trạng thái disabled.
     - **Triệt tiêu hoàn toàn lỗi chuột kéo thả tiếp:** Trong suốt thời gian đếm ngược, hệ thống cấm 100% việc kích hoạt `_start_auto_binh_for_window`, loại bỏ bàn đó khỏi hàng đợi tự động `auto_loop_queue`.
   - **Chặn Scanner phân tích trùng lặp khi đang kéo bài:** Trong lúc `is_auto_binh_executing` đang chạy hoặc bàn chơi đang trong thời gian đếm ngược `window_cooldown_remaining > 0`, các sự kiện `_on_frame_processed` và `_on_solution_found` sẽ bỏ qua việc phân tích/tính toán lại và không đẩy thêm lệnh vào hàng đợi, giữ nguyên vị trí bài đã xếp tối ưu.
   - **Quy tắc Bắt buộc Dọn Bàn (Table Cleared Rule) trước khi nhận diện Ván mới:** Sau khi hết thời gian đếm ngược, hệ thống chỉ chấp nhận ván mới khi và chỉ khi đã chứng kiến bàn chơi được dọn sạch bài cũ (`len(valid_cards) < 6`), sau đó chia đủ 13 lá bài mới ổn định qua ít nhất 2 frame liên tiếp. Điều này triệt tiêu hoàn toàn nguy cơ quét nhầm lại bài cũ trong lúc game đang chiếu kết quả so bài.
   - **Khắc phục triệt để lỗi giải phóng QThread (SIGABRT Exit 134):** Quản lý vòng đời `AutoBinhWorker` chuẩn mực, ngắt kết nối an toàn, chờ `wait(1000)` trước khi xóa bộ nhớ trong `closeEvent` và khi khởi tạo worker mới.
   - **Kiểm thử tự động toàn diện:** Viết mới 3 test case chuyên sâu trong `tests/test_auto_binh.py`. Nâng tổng số test toàn dự án lên **155/155 tests PASSED (100%)** trong 29.85 giây.

1. **Tự động nhận diện nhịp game thời gian thực (Auto Game Rhythm Detection Mode — Xóa bỏ thời gian chờ thủ công):**
   - **Checkbox chế độ tự động:** Bổ sung `chk_auto_game_timing` (`⚡ Tự động theo nhịp game (Tự phát hiện cộng tiền xong & chia bài mới)`) trên thanh công cụ Tab 6 (bật mặc định). Tự động vô hiệu hóa các ô SpinBox thời gian đếm ngược và nút mở khóa để tránh thao tác thừa.
   - **Event-Driven Payout & Clearing Detection:**
     - Ngay sau khi binh xong, hệ thống không đặt thời gian chờ cố định để tránh làm mù scanner, mà chuyển sang theo dõi thời gian thực: `⏳ Đang theo dõi game so bài & cộng tiền...`.
     - Khi game hiển thị hiệu ứng so bài, trả thưởng/cộng tiền và dọn bài cũ (`len(valid_cards) < 10`), hệ thống nhận diện `has_seen_table_cleared = True`, cập nhật trạng thái `⏳ Ván cũ đã dọn (Game đã tính tiền / dọn bàn xong) — Đang chờ chia bài ván mới...`.
   - **Tự động kích hoạt ván mới & Binh ngay lập tức:**
     - Khi 13 lá bài mới xuất hiện, hash bộ bài mới được tính toán bằng `CardStateManager.compute_position_invariant_hash(...)` và so khớp khác biệt với ván trước (`curr_hash != last_binned_hashes`).
     - Bộ lọc Debounce ổn định $\ge 2$ frame liên tiếp loại bỏ hoàn toàn nhiễu giật hình khi lật bài.
     - Hệ thống tự động nâng số thứ tự ván `#N`, cập nhật trạng thái `🎯 Phát hiện Ván mới #N! Đã nhận diện đủ 13 lá — Binh bài ngay!`, mở khóa nút `⚡ Tự Động Binh Bài (Ván #N)` và tự động đẩy vào hàng đợi `auto_loop_queue` để binh bài ngay lập tức khi bật chế độ Auto-Loop.
   - **Kiểm thử tự động:** Thêm mới test case `test_auto_game_rhythm_mode_triggers_without_timer_delay` trong `tests/test_auto_binh.py`. Toàn bộ **167/167 tests PASSED (100%)**.

1. **Tối ưu hóa Giao diện Responsive Siêu Gọn Gàng & Đẹp Mắt trên Tab 6 (`MultiWindowWidget`):**
   - **Thanh điều khiển thu gọn thông minh (Smart Rhythm Control Bar):**
     - Đóng gói toàn bộ các widget thời gian đếm lùi thủ công (`spin_round_time`, `spin_cooldown`, `btn_reset_wait`) vào `container_manual_timing`.
     - Tự động ẩn hoàn toàn khi bật chế độ `⚡ Tự động theo nhịp game` (Real-time), giải phóng hơn 320px chiều ngang. Khi tắt nhịp game tự động, các nút đếm lùi sẽ mượt mà xuất hiện trở lại.
     - Giới hạn chiều rộng ComboBox co giãn thông minh (80px - 160px), chống tràn viền trên màn hình hẹp.
   - **Khung nhìn cuộn thông minh (`QScrollArea`):**
     - Đóng gói cả `selection_page` lẫn `dashboard_page` vào `QScrollArea` có `setWidgetResizable(True)`, loại bỏ viền cứng và tích hợp thanh cuộn mờ chuẩn macOS HIG, triệt tiêu 100% hiện tượng bị cắt chữ, mất nút hay bảng suy luận ở bất kỳ độ phân giải nào.
   - **Panel bàn chơi siêu nét & phân tầng màu sắc chuẩn macOS:**
     - Giảm `minimumWidth` từ 250px xuống 200px giúp 3 bàn chơi nằm gọn gàng cạnh nhau ngay cả ở độ phân giải 900px - 1000px.
     - Thẻ bài thumbnail tự động co giãn (`30x44` ở chế độ đa màn; `38x54` ở chế độ 1 màn phóng to), strip bài thu gọn 62px.
     - Phân cấp màu sắc trực quan cho 3 Chi: Chi 1 (Xanh Cyan `#64D2FF`), Chi 2 (Vàng Cam `#FF9F0A`), Chi 3 (Xanh Lục Ngọc `#30D158`), và Khung đối thủ #4 (Tím Neon `#BF5AF2`).
   - **Tự động co giãn theo kích thước cửa sổ (`resizeEvent`):**
     - Co giãn nhãn các nút thông minh khi chiều rộng `< 1050px` (`"🔄 Quét"`, `"📚 Mẫu bài"`, `"⚡ Nhịp game"`, `"🔙 Đổi màn"`).
   - **Kiểm thử tự động:**
     - Bổ sung test case `test_responsive_layout_and_adaptive_resizing` trong `tests/test_multi_window.py`. Toàn bộ test suite **168/168 tests PASSED (100%)**.
