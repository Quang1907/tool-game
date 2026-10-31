# CHANGELOG — BINH 13 ANALYZER (macOS)

Tất cả các thay đổi đáng chú ý của dự án được ghi chép tại đây theo định dạng [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.3.6] — 2026-10-31

### Added & Enhanced

- **Xác định ván bài mới tự động (New Hand/Round Detection) ([multi_window_widget.py](file:///Users/levanquang/tool/app/ui/components/multi_window_widget.py), [card_state.py](file:///Users/levanquang/tool/app/vision/card_state.py)):**
  - **Nhận diện ván bài mới:** Tự động phát hiện khi bộ 13 lá bài mới xuất hiện trên bàn chơi bằng cách so sánh hash nội dung lá bài bất biến vị trí (`CardStateManager.compute_position_invariant_hash`) với hash của ván bài đã binh gần nhất (`last_binned_hashes[window_idx]`).
  - **Lọc chống chớp nháy (Debounce 2 frames):** Yêu cầu 13 lá mới ổn định qua ít nhất 2 frame quét liên tiếp (~300ms) để loại bỏ hiện tượng animation bay bài khi chia dở, đảm bảo phát hiện chính xác ván bài mới trước khi xử lý.
  - **Nhận diện kết thúc ván cũ / dọn bàn:** Khi số lá bài trên bàn giảm xuống $< 8$ lá (do thu bài / tính tiền so chi), hệ thống tự động nhận biết ván cũ đã kết thúc và chuyển trạng thái sang `"⏳ Ván cũ đã xong — Đang chờ chia bài ván mới..."`.
  - **Huy hiệu hiển thị ván bài trực quan (`lbl_round_badge`):** Bổ sung huy hiệu ván bài trên header của từng bàn chơi:
    - `"Ván #N (MỚI)"`: Khi vừa phát hiện đủ 13 lá của ván mới (viền xanh lam phát sáng).
    - `"Ván #N (Đã binh)"`: Sau khi hệ thống đã hoàn tất xếp bài cho ván đó (nền xanh lục).
- **Chế độ Tự Động Binh Bài Liên Tục (Continuous Auto-Loop Mode):**
  - **Nút bật/tắt trên thanh công cụ Tab 6:** Nút `"🔄 Tự động binh liên tục: ĐANG BẬT / TẮT"` cho phép hệ thống tự vận hành 24/7 mà không cần người dùng phải bấm nút mỗi ván.
  - **Hàng đợi điều phối luân phiên (`auto_loop_queue`):** Khi nhiều bàn cùng xuất hiện ván bài mới, hệ thống tự động xếp theo hàng đợi bất đồng bộ (`QTimer.singleShot(400, ...)`), tránh xung đột chuột và luân phiên tự động xếp xong bàn này thì chuyển sang bàn tiếp theo.
  - **Bộ đếm ván bài thành công (`lbl_loop_counter`):** Hiển thị trực tiếp tổng số ván bài hệ thống đã tự động binh thành công (`"Đã binh: X ván"`).
  - **Bộ nhớ đệm lời giải (`_solution_cache`) ([multi_window_service.py](file:///Users/levanquang/tool/app/services/multi_window_service.py)):** Cache kết quả giải thế bài tối ưu theo hash quân bài, giảm tải CPU tối đa khi chạy quét liên tục 24/7.
- **Kiểm thử tự động:**
  - Bổ sung 2 test case mới trong `tests/test_auto_binh.py`:
    - `test_new_round_detection_and_badge_update`: Kiểm tra chu kỳ phát hiện ván mới, chuyển đổi ván cũ dọn bàn và tăng số thứ tự ván.
    - `test_continuous_auto_loop_mode`: Kiểm tra cơ chế tự động xếp bài khi bật chế độ Auto-Loop mà không cần click nút, không bị lặp lại trên cùng một ván bài.
  - Toàn bộ test suite đạt **149/149 tests PASSED (100%)**.

---

## [1.3.5] — 2026-10-31

### Fixed

- **Khắc phục lỗi `NameError: name 'time' is not defined` ([multi_window_widget.py](file:///Users/levanquang/tool/app/ui/components/multi_window_widget.py)):**
  - Thêm `import time` còn thiếu ở đầu module. Lỗi xuất hiện khi người dùng bấm nút *"⚡ Tự Động Binh Bài"* trên Tab 6 (tại vị trí chờ kích hoạt cửa sổ `time.sleep(0.18)`).
- **Khắc phục lỗi `QThread: Destroyed while thread is still running` và memory cleanup:**
  - Bổ sung `closeEvent` cho cả `MultiWindowWidget` và `MainWindow` để ngắt an toàn tất cả background worker (`_stop_bot`, `_auto_binh_workers`, `_sim_worker`) trước khi thoát ứng dụng.
  - Tối ưu cơ chế kết nối tín hiệu trong `AutoBinhWorker` ([gesture_manager.py](file:///Users/levanquang/tool/app/automation/gesture_manager.py)): tự động ngắt kết nối tín hiệu tạm thời (`disconnect`) trong khối `finally` của hàm `run()` để tránh tình trạng tích tụ listener và xung đột luồng khi thực hiện binh bài nhiều lần.
  - Ngăn ngừa việc người dùng nhấn lặp lại nút Binh Bài khi worker cũ trên cùng bàn chơi đang chạy.
- **Kiểm thử tự động:**
  - Bổ sung test case `test_start_auto_binh_uses_imported_time_and_cleans_up` trong `tests/test_auto_binh.py`.
  - Toàn bộ test suite đạt **147/147 tests PASSED (100%)**.

---

## [1.3.4] — 2026-10-30

### Added & Enhanced

- **Di chuyển chuột mượt mà và Click chọn bài trước khi kéo thả ([mouse_controller.py](file:///Users/levanquang/tool/app/automation/mouse_controller.py)):**
  - **Di chuyển chuột tự nhiên (`smooth_move_to`):** Thay vì dịch chuyển tức thời (teleport) làm giật trỏ chuột, hệ thống lấy vị trí con trỏ chuột hiện tại của người dùng (từ vị trí vừa bấm nút hoặc vị trí thả của lá bài trước) và di chuyển mượt mà dọc theo đường cong gia tốc ease-in-out đến vị trí con bài cần kéo đầu tiên.
  - **Nhấp chọn lá bài vào màn hình (`click_to_select`):** Khi chuột đến tâm con bài nguồn, hệ thống thực hiện một cú nhấp (mouse down -> 45ms hold -> mouse up) để kích hoạt focus cửa sổ game và chọn con bài đó trên giao diện web/client, sau đó tạm nghỉ 80ms tự nhiên rồi mới thực hiện chuỗi kéo thả (drag & drop) sang vị trí đích.
- **Tự động luân phiên xếp bài trên cả 3 cửa sổ / 3 tab game ([multi_window_widget.py](file:///Users/levanquang/tool/app/ui/components/multi_window_widget.py)):**
  - **Nút "⚡ Binh bài cả 3 bàn (Luân phiên)":** Bổ sung nút thao tác tổng trên thanh công cụ Bot 3 Cửa Sổ. Hệ thống tự động xếp bài lần lượt qua các bàn chơi: Kích hoạt Bàn 1 -> Tự động xếp Bàn 1 -> Nghỉ 400ms -> Chuyển và kích hoạt Bàn 2 -> Tự động xếp Bàn 2 -> Nghỉ 400ms -> Chuyển và kích hoạt Bàn 3 -> Tự động xếp Bàn 3.
- **Loại bỏ hộp thoại thông báo hoàn thành (Suppress Completion Dialog):**
  - Bỏ hoàn toàn các hộp thoại popup `QMessageBox.information` sau khi binh bài xong theo đúng yêu cầu người dùng ("thông báo thực hiện xong qua mấy bước không cần hiển thị"). Tiến trình và trạng thái hoàn thành được cập nhật mượt mà trực tiếp trên thanh trạng thái của từng panel mà không gây gián đoạn hay phải bấm OK.
- **Kiểm thử tự động:**
  - Bổ sung 2 test case mới kiểm tra `smooth_move_to`, `click_to_select` và luân phiên 3 cửa sổ không popup trong [test_auto_binh.py](file:///Users/levanquang/tool/tests/test_auto_binh.py).
  - 100% test suite đạt **146/146 tests PASSED**.

---

## [1.3.3] — 2026-10-30

### Added & Enhanced

- **Tự động kích hoạt và mở cửa sổ / tab trình duyệt khi chọn và ghi macro (Browser Auto-Activation on Selection & Recording):**
  - **Kích hoạt ứng dụng và cửa sổ native trên macOS ([window_manager.py](file:///Users/levanquang/tool/app/vision/window_manager.py)):**
    - Bổ sung hàm `activate_window(target, title)`: Sử dụng AppleScript và System Events với `AXRaise` (chạy siêu nhanh ~70-90ms) để tự động đưa cửa sổ hoặc ứng dụng game (Google Chrome, Safari, app client, v.v.) lên vị trí trên cùng (foreground/frontmost).
  - **Tự động mở khi duyệt và chọn trình duyệt ([gesture_widget.py](file:///Users/levanquang/tool/app/ui/components/gesture_widget.py)):**
    - Ngay khi người dùng chọn một cửa sổ game trong dropdown `combo_windows`, hệ thống tự động kích hoạt và mở tab trình duyệt/cửa sổ đó lên ngay trước màn hình để sẵn sàng thao tác mà không cần người dùng phải bấm Alt+Tab thủ công.
    - Tự động kích hoạt khi bấm nút *"🔴 Bắt đầu ghi bước này"*, *"▶️ Test thử"*, hoặc *"📸 Xem trước & 13 Ô bài"*.
    - Bổ sung tùy chọn checkbox *"⚡ Tự động mở cửa sổ khi chọn/ghi"* (mặc định bật).
- **Xác nhận đúng vị trí 13 con bài khớp chính xác với khung giao diện (kể cả khi toàn màn hình hay thu nhỏ):**
  - **Truy vấn kích thước cửa sổ động trong bộ ghi macro ([macro_recorder.py](file:///Users/levanquang/tool/app/automation/macro_recorder.py)):**
    - Bổ sung tham số `bounds_getter`: Trong suốt quá trình nhấn giữ chuột và kéo thả, hệ thống liên tục truy vấn kích thước thực tế của cửa sổ. Khi người dùng thu nhỏ cửa sổ game, tọa độ tương đối $[0.0, 1.0]$ luôn được chia cho đúng chiều rộng và chiều cao thực tế của khung giao diện hiện tại, loại bỏ hoàn toàn lỗi dồn góc hoặc lệch tọa độ khi thay đổi kích thước.
  - **Tự động nhận diện và thích ứng tọa độ 13 con bài thời gian thực ([gesture_widget.py](file:///Users/levanquang/tool/app/ui/components/gesture_widget.py)):**
    - Bổ sung hàm `get_live_card_slot_coords(window_id)`: Tự động chụp frame và phát hiện tâm 13 quân bài trên cửa sổ game hiện tại bằng Computer Vision.
    - Khi phát lại (Test thử) hoặc tự động binh bài, quỹ đạo macro (kể cả ghi ở toàn màn hình) sẽ được hàm `adapt_trajectory_to_endpoints` tự động co giãn và dịch chuyển để điểm nhấc chuột và điểm thả chuột rơi chính xác 100% vào tâm của quân bài nguồn và quân bài đích trên giao diện thu nhỏ.
  - **Xem trước trực quan 13 ô bài với Bounding Box có màu phân biệt:**
    - Cửa sổ *"📸 Xem trước & 13 Ô bài"* vẽ trực tiếp bounding box và số thứ tự của 13 lá bài lên ảnh thực tế: Vàng (Chi Đầu 1-2-3), Xanh lam (Chi Giữa 4-5-6-7-8), Xanh lục (Chi Cuối 9-10-11-12-13) giúp người dùng kiểm tra trực quan độ chính xác.
  - **Tự động kích hoạt cửa sổ trước khi tự động binh bài ([multi_window_widget.py](file:///Users/levanquang/tool/app/ui/components/multi_window_widget.py)):**
    - Khi bấm *"⚡ Tự Động Binh Bài"*, cửa sổ tương ứng sẽ được tự động kích hoạt lên phía trước trước khi phát chuỗi cử chỉ kéo thả.
- **Kiểm thử tự động:**
  - Bổ sung các bài test mới kiểm tra `activate_window` và `bounds_getter` khi cửa sổ bị thu nhỏ trong [test_auto_binh.py](file:///Users/levanquang/tool/tests/test_auto_binh.py).
  - 100% test suite đạt **144/144 tests PASSED**.

---

## [1.3.2] — 2026-10-30

### Fixed & Enhanced

- **Khắc phục lỗi lệch vị trí quân bài khi cửa sổ game thu nhỏ (Resized/Shrunk Window Resolution Invariance) và Tự động căn chỉnh tọa độ 13 lá bài:**
  - **Truy vấn kích thước cửa sổ game theo thời gian thực ([window_manager.py](file:///Users/levanquang/tool/app/vision/window_manager.py)):**
    - Bổ sung `get_window_bounds(window_id)` và `get_window_by_id(window_id)` truy vấn trực tiếp từ macOS WindowServer ngay trước khi ghi macro và trước khi thực thi Auto-Binh. Tọa độ `win_bounds` luôn cập nhật chính xác 100% dù người dùng có di chuyển hoặc thu nhỏ/phóng to cửa sổ game.
    - Sửa lỗi truy cập thuộc tính `win_item.bounds` dạng tuple trong [multi_window_widget.py](file:///Users/levanquang/tool/app/ui/components/multi_window_widget.py).
  - **Thích ứng quỹ đạo kéo chuột theo vị trí bài thực tế ([gesture_manager.py](file:///Users/levanquang/tool/app/automation/gesture_manager.py)):**
    - Bổ sung thuật toán `adapt_trajectory_to_endpoints`: Khi macro được ghi ở chế độ toàn màn hình (fullscreen), nếu cửa sổ game bị thu nhỏ, hệ thống tự động co giãn và dịch chuyển quỹ đạo sao cho điểm bắt đầu rơi chính xác vào tâm lá bài nguồn và điểm kết thúc rơi chính xác vào tâm lá bài đích trên khung hình thu nhỏ, bảo toàn nguyên vẹn độ cong, gia tốc và độ rung vi mô tự nhiên của bàn tay.
  - **Tự động trích xuất tọa độ 13 ô bài từ bounding box lá bài phát hiện ([multi_window_widget.py](file:///Users/levanquang/tool/app/ui/components/multi_window_widget.py)):**
    - Trong Tab 6 ("Bot 3 Cửa Sổ"), hệ thống tự động tính toán tâm `(cx, cy)` của cả 13 lá bài đã nhận diện trên frame thực tế (`live_slot_coords`), chuyển trực tiếp vào `AutoBinhWorker` để kéo chính xác tuyệt đối bất kể kích thước cửa sổ game.
  - **Nút "🔍 Tự động nhận diện 13 ô bài" trong Tab 7 ([gesture_widget.py](file:///Users/levanquang/tool/app/ui/components/gesture_widget.py)):**
    - Cho phép quét trực tiếp cửa sổ game đang chạy, nhận diện 13 quân bài và tự động cập nhật tọa độ 13 ô bài theo đúng kích thước khung hình hiện tại chỉ với 1 click.
  - **Suite Kiểm thử Toàn diện ([test_auto_binh.py](file:///Users/levanquang/tool/tests/test_auto_binh.py)):**
    - Bổ sung bài test cho `adapt_trajectory_to_endpoints` và `get_window_bounds`.
    - Tổng số test suite đạt **142/142 tests PASSED (100%)**.

---

## [1.3.1] — 2026-10-30

### Added

- **Nâng cấp giao diện trực quan Tab số 7 theo đúng cấu trúc 1-2-3 / 4-5-6-7-8 / 9-10-11-12-13 và Trợ lý Ghi Macro Tuần tự từng bước ([gesture_widget.py](file:///Users/levanquang/tool/app/ui/components/gesture_widget.py)):**
  - **Bàn bài 13 Ô trực quan (`CardSlotBox`):** Bố trí 13 ô bài chia làm 3 hàng trực quan:
    - Hàng 1 (Chi Đầu - 3 lá): `Ô 1`, `Ô 2`, `Ô 3`.
    - Hàng 2 (Chi Giữa - 5 lá): `Ô 4`, `Ô 5`, `Ô 6`, `Ô 7`, `Ô 8`.
    - Hàng 3 (Chi Cuối - 5 lá): `Ô 9`, `Ô 10`, `Ô 11`, `Ô 12`, `Ô 13`.
    - Tự động hiển thị nổi bật với viền phát sáng: `📍 NGUỒN (GIỮ CHUỘT)` (vàng cam `#FF9F0A`) và `🎯 ĐÍCH (THẢ CHUỘT)` (xanh lá `#30D158`).
    - Nhấp trực tiếp vào bất kỳ ô nào trên bàn bài để chọn làm Ô Nguồn thao tác.
  - **Trình hướng dẫn ghi macro tuần tự (`Sequential Macro Wizard`):**
    - Hướng dẫn người dùng nhấn giữ - kéo - thả lần lượt từ vị trí 1 đến 12 vị trí còn lại (1➔2, 1➔3, ..., 1➔13).
    - Sau đó tiếp tục chọn ghi cho vị trí số 2 đến 12 vị trí còn lại (2➔1, 2➔3, ..., 2➔13) và lần lượt đến hết 13 vị trí.
    - Hướng dẫn dạng thẻ to, rõ ràng: `👉 BƯỚC 1/12: KÉO TỪ [ Ô 1 ] ➔ [ Ô 2 ]`.
    - Tự động lưu mẫu vào SQLite và tự động chuyển bước kế tiếp ngay khi thả chuột (`chk_auto_advance`).
    - Các nút điều hướng nhanh: `[🔴 Bắt đầu ghi]`, `[🔄 Ghi lại]`, `[⏮️ Bước trước]`, `[⏭️ Bỏ qua]`, `[▶️ Test thử]`, `[✨ Tạo Bézier]`.
  - **Chọn tab / cửa sổ game để ghi:**
    - Dropdown quét danh sách các cửa sổ game đang chạy trên macOS (`WindowManager.list_windows()`), tự động lưu tọa độ `win_bounds` và có nút `[📸 Xem trước]` ảnh bàn chơi.
  - **Bộ lọc click chuột ngoài cửa sổ game và chống rung UI ([macro_recorder.py](file:///Users/levanquang/tool/app/automation/macro_recorder.py)):**
    - `MacroRecorder` tự động bỏ qua các click chuột bên trong giao diện ứng dụng Binh 13 Analyzer khi bấm nút; chỉ kích hoạt ghi macro khi chuột nhấn giữ bên trong cửa sổ game đã chọn.
  - **Kiểm thử tự động:**
    - Bổ sung các bài test cho layout bàn bài 13 ô 3 hàng và luồng điều hướng tuần tự 12 bước trong [tests/test_auto_binh.py](file:///Users/levanquang/tool/tests/test_auto_binh.py).
    - Toàn bộ test suite đạt **140/140 PASSED (100%)**.

---

## [1.3.0] — 2026-10-29

### Added

- **Xây dựng phân hệ Tự động hóa & Quản lý Cử chỉ Chuột (`app/automation/`) và Tab số 7 ("7. Tự động binh bài & Cử chỉ"):**
  - **Mô hình Dữ liệu Cử chỉ ([gesture_models.py](file:///Users/levanquang/tool/app/automation/gesture_models.py)):**
    - `CardSlot`: Định nghĩa 13 vị trí ô bài trên giao diện game (1..3 Chi Đầu, 4..8 Chi Giữa, 9..13 Chi Cuối) theo tọa độ chuẩn hóa $[0.0, 1.0]$ tương đối so với kích thước cửa sổ game.
    - `GesturePoint`: Tọa độ điểm trung gian (waypoint) `(rel_x, rel_y, time_ms)`.
    - `GestureSample`: Mẫu thao tác kéo thả giữa cặp ô nguồn - đích với UUID, danh sách waypoints, thời gian trễ giữ thẻ trước khi kéo (`press_delay_ms`), thời gian giữ sau khi thả (`release_delay_ms`), tổng thời gian kéo (`duration_ms`), trọng số lựa chọn ngẫu nhiên (`weight`), cờ kiểm tra thực tế (`is_verified`).
    - `MoveAction` & `MovePlan`: Kế hoạch chuỗi các bước hoán đổi ô bài để sắp xếp từ bộ bài hiện tại sang bộ bài tối ưu.
    - `GestureConfig`: Cấu hình tự động hóa (chọn ngẫu nhiên, chỉ dùng mẫu đã kiểm tra, hệ số tốc độ kéo, khoảng nghỉ giữa các thao tác).
  - **Tối ưu hóa Chuỗi Hoán đổi Bài ([move_planner.py](file:///Users/levanquang/tool/app/automation/move_planner.py)):**
    - Thuật toán phân rã chu trình hoán vị (Disjoint Permutation Cycle Decomposition) cho 13 ô bài: Tìm chuỗi hoán đổi ít lượt thao tác nhất ($\le 12$ lượt kéo) để đưa toàn bộ 13 quân bài từ vị trí quét nhận diện trên màn hình về đúng vị trí sắp xếp tối ưu của Mậu Binh (Chi Đầu 3 lá, Chi Giữa 5 lá, Chi Cuối 5 lá).
  - **Điều khiển Chuột macOS Native Sub-millisecond ([mouse_controller.py](file:///Users/levanquang/tool/app/automation/mouse_controller.py)):**
    - Tương tác trực tiếp với macOS WindowServer thông qua `CoreGraphics` CGEvents (`CGEventCreateMouseEvent`, `CGEventPost`) qua `ctypes`.
    - Tự động quy đổi tọa độ tương đối $[0.0, 1.0]$ sang tọa độ pixel màn hình vật lý theo vị trí thực tế của cửa sổ game (`win_bounds`).
    - Tích hợp chốt an toàn (Failsafe Mechanism): Tự động hủy thao tác ngay lập tức nếu người dùng di chuột vào góc trên bên trái $(0, 0)$ của màn hình.
  - **Bộ chọn Mẫu & Sinh Đường cong Bézier Tự nhiên ([gesture_selector.py](file:///Users/levanquang/tool/app/automation/gesture_selector.py)):**
    - Lựa chọn mẫu kéo thả ngẫu nhiên theo trọng số (Weighted Random Selection), tự động tránh lặp lại mẫu vừa sử dụng.
    - Sinh đường cong Cubic Bézier mượt mà với gia tốc phi tuyến tính (ease-in-out) kết hợp vi dao động ngẫu nhiên (micro-jitter) mô phỏng động học tay người khi kéo thả thẻ bài.
    - Hỗ trợ tạo tự động toàn bộ 156 mẫu Bézier chuẩn cho tất cả $13 \times 12$ cặp ô bài chỉ với 1 click.
  - **Bộ Ghi Macro Chuột Trực tiếp 60 Hz ([macro_recorder.py](file:///Users/levanquang/tool/app/automation/macro_recorder.py)):**
    - Thu thập tọa độ kéo chuột thực tế của người dùng trên bàn chơi theo thời gian thực (60 Hz) qua `CGEventSourceButtonState` và `QCursor.pos()`, tự động chuẩn hóa sang $[0.0, 1.0]$ theo cửa sổ game.
  - **Bộ Điều phối & QThread Worker ([gesture_manager.py](file:///Users/levanquang/tool/app/automation/gesture_manager.py)):**
    - `AutoBinhWorker(QThread)`: Thực thi tuần tự các lượt kéo bài ngầm, phát tín hiệu tiến độ `progress(current, total, msg)`, `step_completed(action)`, `finished(success, msg)` về UI, đảm bảo Zero UI Lag.
  - **Giao diện Quản trị Cử chỉ Tab 7 ([gesture_widget.py](file:///Users/levanquang/tool/app/ui/components/gesture_widget.py)):**
    - Ma trận trực quan $13 \times 13$: Hiển thị số lượng mẫu và trạng thái của từng cặp vị trí có hướng.
    - Thanh điều khiển: Ghi macro, tạo nhanh 156 mẫu Bézier, chạy thử mẫu, xóa mẫu, bật/tắt cờ `is_verified`.
    - Hộp thoại `SlotEditorDialog`: Xem và tinh chỉnh tọa độ tương đối $[0.0, 1.0]$ của 13 ô bài trực quan.
    - Sao lưu & Khôi phục: Nút Xuất JSON (`export_gestures_json`) và Nhập JSON (`import_gestures_json`).
  - **Tích hợp Nút "⚡ Tự Động Binh Bài" trên Tab 6 ([multi_window_widget.py](file:///Users/levanquang/tool/app/ui/components/multi_window_widget.py)):**
    - Mỗi panel cửa sổ trong Tab 6 có nút bấm chuyên dụng: Tự động trích xuất 13 lá bài đã nhận diện, kiểm tra thế bài tối ưu từ Solver, lấy tọa độ cửa sổ game và kích hoạt `AutoBinhWorker` thực hiện sắp xếp bài tự động.
  - **Lưu trữ Bền vững SQLite ([db.py](file:///Users/levanquang/tool/app/database/db.py), [repository.py](file:///Users/levanquang/tool/app/database/repository.py)):**
    - Tạo các bảng `card_slots` và `gesture_samples` kèm index tìm kiếm tối ưu.
  - **Suite Kiểm thử Toàn diện ([test_auto_binh.py](file:///Users/levanquang/tool/tests/test_auto_binh.py), [test_ui.py](file:///Users/levanquang/tool/tests/test_ui.py)):**
    - Thêm 8 bài test chuyên sâu cho toàn bộ phân hệ Automation.
    - Tổng số test suite toàn dự án đạt **138/138 tests PASSED (100%)**.

---

### Fixed

- **Khắc phục triệt để lỗi một số quân bài đã xác nhận đúng nhưng không thể nhận diện đúng hoàn toàn (ví dụ 3♠, 6♠ không hiện `[Mẫu]` mà điểm đối chiếu mẫu chỉ đạt 44%, hiển thị sai sang 3♣ trong danh sách gợi ý):**
  - **Bổ sung biên trượt dung sai tịnh tiến $\pm 2$ pixel (Translational Invariance):** Loại bỏ giới hạn cửa sổ cố định $1 \times 1$ của phép đo `cv2.matchTemplate(q, ref, cv2.TM_CCOEFF_NORMED)`. Thêm biên đệm viền 2 pixel (`cv2.copyMakeBorder(query, 2, 2, 2, 2, cv2.BORDER_CONSTANT)`) trước khi khớp mẫu glyph và lấy cực đại `np.max(res)` trong [card_reference_library.py](file:///Users/levanquang/tool/app/vision/card_reference_library.py). Điều này ngăn ngừa hiện tượng điểm tương quan rớt từ $0.99$ xuống $0.57$ chỉ vì lệch 1-2 pixel khi crop.
  - **Hàn gắn đứt gãy cuống biểu tượng Bích / Tép (Stem Preservation):** Áp dụng phép đóng hình thái học (`cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)`) với kernel ellipse $3 \times 3$ ngay sau khi binarize Otsu, kết hợp cơ chế tự động gom cụm cuống nằm ngay dưới thân chất. Khắc phục triệt để việc phần cuống bị ngắt lìa khiến thân bích bị cụt cuống và kéo giãn biến dạng khi resize về $28 \times 28$.
  - **Chuẩn hóa ngưỡng chấp thuận `[Mẫu]` ([card_recognizer.py](file:///Users/levanquang/tool/app/vision/card_recognizer.py)):** Đồng bộ ngưỡng chấp nhận cờ `is_reference_match = True` về mức $\ge 0.68$, đảm bảo hiển thị đúng nhãn `[Mẫu]` xanh cho tất cả các lá bài đã có mẫu trong cơ sở dữ liệu.
  - **Kết quả nghiệm thu:** 13/13 lá bài trên ảnh thực tế [IMG_1287.PNG](file:///Users/levanquang/Downloads/IMG_1287.PNG) đều đạt nhãn `[Mẫu]` $100\%$. Thêm unit test `test_subpixel_shift_and_separated_stem_glyph_matching`. Toàn bộ test suite đạt **130/130 PASSED (100%)**.

---

## [1.2.4] — 2026-10-29

### Fixed

- **Đồng bộ hóa pipeline nhận diện lá bài và loại bỏ hoàn toàn hiện tượng nhận diện sai 2 Bích (2♠) thành 2 Tép (2♣) giữa Tab 2 và Tab 6:**
  - Hợp nhất hàm nhận diện chung `recognize_cards_pipeline` trong [vision_service.py](file:///Users/levanquang/tool/app/services/vision_service.py) và chia sẻ instance bộ nhớ giữa Tab 2 và Tab 6.
  - Loại bỏ bản ghi corrupt `099c710e` (lá 4♠ bị dán nhãn 4C) trong thư viện mẫu.
  - Đảm bảo độ ưu tiên tuyệt đối của Full Card Reference khi đã khớp bài đã xác nhận.

---

## [1.2.3] — 2026-10-28

### Fixed

- **Khắc phục lỗi Tab 6 ("Bot 3 Cửa Sổ") không lấy được hình ảnh từ cửa sổ, báo che khuất (Occluded), không nhận diện bài và không gợi ý xếp bài:**
  - **Chụp ảnh trực tiếp theo CGWindowID ([screen_capture.py](file:///Users/levanquang/tool/app/vision/screen_capture.py)):** Tích hợp lệnh `screencapture -l <window_id> -o -x` để lấy trực tiếp frame hình ảnh của chính xác cửa sổ game từ macOS WindowServer, bất kể cửa sổ app Binh 13 Analyzer hay các cửa sổ khác có đang đè lên trên hay không.
  - **Sửa lỗi lệch Window ID và tính toán Occlusion ([multi_window_widget.py](file:///Users/levanquang/tool/app/ui/components/multi_window_widget.py), [window_manager.py](file:///Users/levanquang/tool/app/vision/window_manager.py)):** Trước đây slot UI truyền số thứ tự 1, 2, 3 làm `window_id`, khiến thuật toán `compute_occlusion` không tìm thấy và gán nhầm tỷ lệ che khuất 100%. Đã bổ sung trường `cg_window_id` vào `WindowROI` và kết nối trực tiếp với macOS CGWindowID. Loại trừ cửa sổ ứng dụng Binh 13 Analyzer khỏi danh sách các cửa sổ che khuất.
  - **Xác nhận tức thì khi chọn cửa sổ trong dropdown:** Thêm callback `_on_window_selected` cho sự kiện `combo_w1/w2/w3.currentIndexChanged`. Ngay khi người dùng chọn cửa sổ, app chụp ảnh tức thì, nạp vào viewer để người dùng xác nhận đúng cửa sổ, tự động chạy card detection để hiển thị thumbnail lá bài phát hiện và tính toán gợi ý xếp bài tối ưu (Chi Đầu, Chi Giữa, Chi Cuối).
  - **Không chặn quét khi cửa sổ bị che một phần ([multi_window_service.py](file:///Users/levanquang/tool/app/services/multi_window_service.py)):** Tiếp tục phát hiện và nhận diện bài nếu frame ảnh hợp lệ.
  - **Cập nhật bộ lọc cửa sổ Swift ([macos_window_helper.swift](file:///Users/levanquang/tool/scripts/macos_window_helper.swift)):** Bỏ flag `optionOnScreenOnly` để nhận diện các cửa sổ game nằm phía dưới, đồng thời loại trừ chính cửa sổ Binh 13 Analyzer.
  - **Khắc phục lỗi crash `AttributeError: 'Solver' object has no attribute 'solve_heuristic'` ([solver.py](file:///Users/levanquang/tool/app/core/solver.py)):** Bổ sung phương thức `solve_heuristic` ủy quyền cho `solve()`, đồng thời thêm bọc an toàn `try...except` khi gọi bộ giải trong [multi_window_widget.py](file:///Users/levanquang/tool/app/ui/components/multi_window_widget.py) và [multi_window_service.py](file:///Users/levanquang/tool/app/services/multi_window_service.py).
  - **Triệt tiêu cảnh báo font Qt `SF Pro Text` ([styles.py](file:///Users/levanquang/tool/app/ui/styles.py), [card_widget.py](file:///Users/levanquang/tool/app/ui/components/card_widget.py)):** Thay thế `SF Pro Text` bằng native macOS font `.AppleSystemUIFont`, loại bỏ hoàn toàn cảnh báo font và tăng tốc độ khởi tạo giao diện.
  - **Bổ sung kiểm thử và cấu hình session fixture:** Thêm test xác minh tích hợp giải bài 13 lá trong `tests/test_multi_window.py` và tạo `tests/conftest.py`, nâng tổng số test suite đạt **119/119 PASSED (100%)**.

---

## [1.2.2] — 2026-10-27

### Fixed

- **Khắc phục triệt để lỗi toàn bộ các lá bài đen (10♠, 5♠, 4♣, 8♣, A♠) bị gán nhầm thành chất Rô (♦) và báo bài trùng:**
  - **Sửa phân biệt màu đỏ/đen trong [card_reference_library.py](file:///Users/levanquang/tool/app/vision/card_reference_library.py):** Ngưỡng pixel HSV cũ (> 15 px) bị nhiễu do viền khử răng cưa và đổ bóng xám đen, khiến các lá bài đen bị coi là màu đỏ và loại trừ hoàn toàn Bích/Tép trong quá trình match. Hệ thống đã chuyển sang thuật toán đo chênh lệch màu đỏ rực rỡ ($R > 90, R - \max(G, B) > 25, S > 50$) và kiểm tra tương quan với pixel đen tối ($R_{\text{red}} > 0.35 \times B_{\text{black}}$). Đồng thời tự động thu hẹp vùng kiểm tra vào góc index nếu nhận vào ảnh toàn lá để tránh áo đỏ của các quân Tây (J, Q, K).
  - **Khắc phục lỗi cắt xén tách rời 2 chữ số của quân 10 ('1' và '0'):** Thuật toán trích xuất góc động gom nhóm cả 2 chữ số '1' và '0' ở nửa trên thành một vùng rank duy nhất, ngăn việc chữ số '0' bị gán làm rank và chữ số '1' bị gán nhầm làm suit (làm biến mất biểu tượng Bích ♠).
  - **Tối ưu hóa nhận diện rank 10 trong [template_engine.py](file:///Users/levanquang/tool/app/vision/template_engine.py):** Thêm mẫu template số 10 liền khối và cơ chế nhận diện topo 2 ký tự số song song, match đạt độ tin cậy tuyệt đối và không còn bị nhầm sang rank 8.
  - **Sửa bản ghi SQLite `data.db`:** Cập nhật bản ghi `8c5524b6-079f-470b-9a9c-d734316d84ac` (ảnh 5♠ nhưng trước đó bị lưu sai thành 5D) về đúng mã `5S`.
  - **Thêm suite kiểm thử hồi quy `TestBlackCardsColorIntegrityAndRank10Segmentation`:** 116/116 tests toàn dự án đạt 100% PASSED.

---

## [1.2.1] — 2026-10-27

### Fixed

- **Khắc phục triệt để lỗi nhận diện 6 Cơ (6♥) thành 5 Cơ (5♥):**
  - **Phân tích hình học & topo chữ số (Topological Hole Analysis) trong `template_engine.py`:** Sử dụng `cv2.RETR_CCOMP` phát hiện lỗ khép kín. Ký tự '6' bắt buộc có lỗ khép kín ở nửa dưới ($y \ge 0.40$), trong khi '5' không có lỗ khép kín. Áp dụng cơ chế phạt điểm nặng đối với các ứng viên không khớp cấu trúc topo lỗ, và căn giữa glyph trong bounding box 28x36.
  - **Chấm dứt ghi đè nhãn ngầm (Silent Auto-Healing) trong `card_reference_library.py`:** Loại bỏ hoàn toàn khối lệnh tự ý `UPDATE card_references` trong `_add_to_cache`. Nhãn do người dùng xác nhận luôn là chân lý tối cao.
  - **Sửa dữ liệu mẫu bị nhiễm độc trong SQLite (`data.db`):** Di chuyển bản ghi ID `1499111f-9cce-46f2-83a5-3cf6e4dce15c` từ `5H` sang `6H` và cập nhật lại đường dẫn ảnh file mẫu chuẩn.
  - **Thêm hộp thoại `CardContradictionDialog` trong `card_edit_dialog.py`:** Cảnh báo trực quan nếu có sự mâu thuẫn lớn giữa nhãn người dùng chọn và kết quả nhận diện, bảo vệ người dùng không vô tình lưu đè mẫu sai.
  - **Bổ sung 9 bài kiểm thử hồi quy `TestSavedCardReferenceLabelMismatchRegression`:** 113/113 tests toàn dự án đều vượt qua.

---

## [1.2.0] — 2026-10-26

### Added

- **AI Master Engineer System:**
  - Thiết lập thư mục `.ai/` quản lý toàn diện tri thức, kiến trúc, trạng thái, quy tắc và lộ trình phát triển.
  - Tạo `MASTER_CONTEXT.md` đóng vai trò bản đồ điều hướng cho mọi phiên AI tương lai.
  - Tạo `GEMINI.md` định hướng cho Gemini Agent.
  - Cập nhật `AGENTS.md` tương thích với cơ chế phân vai kỹ thuật.
  - Tạo các tài liệu quản lý trạng thái: `CURRENT_STATE.md`, `ACTIVE_TASK.md`, `NEXT_ACTIONS.md`, `KNOWN_ISSUES.md`, `TEST_STATUS.md`.
  - Tạo tài liệu quy trình: `SESSION_WORKFLOW.md`, `CHANGE_APPROVAL_POLICY.md`.
  - Tạo tài liệu chi tiết từng phân hệ: `CORE_DOMAIN.md`, `VISION_PIPELINE.md`, `UI_PRESENTATION.md`, `DATABASE_PERSISTENCE.md`, `SERVICES_ORCHESTRATION.md`.

---

## [1.1.2] — 2026-10-26

### Fixed

- **Khắc phục lỗi False Positive Avatar người chơi bị nhận diện thành `K♦ 50% UNCERTAIN`:**
  - Thêm Candidate Validation trong `CardDetector.validate_crop()`: Loại bỏ các contour avatar hình tròn (độ tròn $> 0.65$), khối vuông $0.82 \le w/h \le 1.28$ có độ trắng $< 50\%$, và nút bấm UI có độ bão hòa màu cao.
  - Cập nhật `CardRecognizer.recognize_crop()`: Trả về `card=None, confidence=0.0` ngay khi phát hiện `NON_CARD_OBJECT` hoặc góc bài thiếu nền trắng ($< 35\%$), không đoán mò.
- **Khắc phục lỗi 13 nút Rank trong dialog bị trống (khối xanh không chữ):**
  - Khắc phục xung đột CSS: Nút Rank kích thước $36 \times 30\text{ px}$ được ghi đè inline `padding: 0; font-size: 12px; font-weight: 600; color: #FFFFFF` để tránh bị padding toàn cục $16\text{px}$ đẩy mất chữ.
  - Sắp xếp 13 nút Rank đúng thứ tự: `A, 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K`.
  - Đảm bảo tính độc lập: Chọn Rank giữ nguyên Suit hiện tại; chọn Suit giữ nguyên Rank hiện tại.
- **Đồng bộ tọa độ crop:**
  - Trích xuất `raw_patch` từ frame gốc của bàn chơi; gán `raw_crop=source_crop` trong `DetectedCard`.
  - Cập nhật `VisionDebugDialog` hiển thị tọa độ Bbox ảnh gốc, kích thước crop, kích thước Rank/Suit crop và trạng thái validation.
- **An toàn thư viện mẫu:**
  - Chặn tuyệt đối việc lưu ảnh avatar / non-card vào `CardReferenceLibrary`.

### Added

- Bổ sung `TestMandatoryVerificationTestSuite` trong `tests/test_card_detection_and_reference.py` kiểm chứng Test A (Avatar), Test B (Nút Rank), Test C (Nút Suit), Test D (Tọa độ crop), Test E (An toàn xác nhận mẫu).

---

## [1.1.1] — 2026-10-25

### Added

- Tách biệt nhận diện Rank và Suit độc lập (`extract_dynamic_corner_patches` qua Connected Components).
- Xây dựng Thư viện ảnh mẫu đã xác nhận (`CardReferenceLibrary`) lưu trong SQLite.
- Thêm `CardEditDialog` cho phép người dùng xác nhận và sửa bài trực quan.
- Thêm `VisionDebugDialog` với 4 tab chẩn đoán chuyên sâu.
- Thêm `ZoomableImageViewer` hỗ trợ zoom, pan và click vào bounding box bài.

---

## [1.1.0] — 2026-10-25

### Added

- Hỗ trợ giám sát 3 cửa sổ bàn chơi game đồng thời trên một màn hình MacBook.
- Cơ chế 1-frame chụp chung, crop 3 ROI độc lập qua `ROIManager`.
- Bộ theo dõi quân bài `CardTracker` bất biến vị trí (`position_invariant_hash`), không tính lại solver khi bài chỉ di chuyển.

---

## [1.0.0] — 2026-10-25

### Added

- Khởi tạo kiến trúc Clean Architecture 5 tầng.
- Mô hình hóa bài (`card.py`), bộ đánh giá (`evaluator.py`), luật tính điểm (`rules.py`).
- Thuật toán phân rã tổ hợp 36,036 thế bài (`solver.py`).
- Bộ mô phỏng Monte Carlo tối ưu EV với Common Random Numbers (`simulator.py`, `ev_optimizer.py`).
- Giao diện PySide6 Dark Theme Apple HIG (`app/ui/main_window.py`).
- Lưu trữ phiên chơi vào SQLite cục bộ (`app/database/`).
