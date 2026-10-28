# ACTIVE TASK — BINH 13 ANALYZER

**Nhiệm vụ hiện tại:** Sửa lỗi chụp cửa sổ, tự động xác nhận đúng cửa sổ được chọn, hiển thị lá bài phát hiện và gợi ý xếp bài tối ưu trong Tab 6 ("Bot 3 Cửa Sổ").  
**Người yêu cầu:** User / Product Owner  
**Trạng thái nhiệm vụ:** `COMPLETED / VERIFIED` (119/119 tests PASSED)

---

## 1. MỤC TIÊU NHIỆM VỤ

1. **Lấy đúng hình ảnh cửa sổ:** Thay vì chụp toàn màn hình rồi crop (dễ bị chính cửa sổ app Binh 13 Analyzer đè lên tạo hiệu ứng lồng vô tận), sử dụng cơ chế chụp trực tiếp theo `CGWindowID` của macOS WindowServer.
2. **Xác nhận tức thì khi chọn cửa sổ:** Khi người dùng chọn một cửa sổ từ dropdown `Cửa số 1`, `Cửa số 2`, `Cửa số 3`, lập tức chụp và cập nhật khung hình vào viewer để người dùng xác nhận đúng cửa sổ mong muốn.
3. **Tự động nhận diện lá bài & Gợi ý xếp bài tối ưu:** Ngay khi cửa sổ được chọn hoặc khi chạy bot quét, tự động phát hiện các lá bài, hiển thị ảnh thumbnail và nếu phát hiện đủ 13 lá, giải bài tìm bộ 3 chi tối ưu (Chi Đầu, Chi Giữa, Chi Cuối) hiển thị trực quan lên giao diện.
4. **Khắc phục cảnh báo Occlusion ảo:** Loại bỏ việc cửa sổ ứng dụng Binh 13 Analyzer tự tính mình là đối tượng che khuất cửa sổ game, và sửa lỗi ánh xạ `window_id` (slot index 1,2,3 vs macOS CGWindowID).

---

## 2. TIẾN ĐỘ THỰC HIỆN

- [x] Thêm `ScreenCapture.capture_window_by_id` trực tiếp từ macOS WindowServer qua `/usr/sbin/screencapture -l <window_id> -o -x`.
- [x] Cập nhật `WindowROI` với trường `cg_window_id` để kết nối chính xác với WindowServer.
- [x] Sửa thuật toán `compute_occlusion` trong `WindowManager`: loại trừ cửa sổ Binh 13 Analyzer / Python.
- [x] Kết nối sự kiện `combo_w1/w2/w3.currentIndexChanged` với hàm `_on_window_selected` trong `MultiWindowWidget`.
- [x] Tích hợp pipeline nhận diện `CardDetector`, `CardRecognizer` và bộ giải `BinhSolver` vào `MultiWindowWidget` và `MultiWindowWorker`.
- [x] Thêm `tests/conftest.py` với fixture `qapp` cho PySide6 test.
- [x] Viết test `TestDirectWindowCaptureAndSelection` trong `tests/test_multi_window.py`.
- [x] Kiểm thử toàn bộ 119/119 tests PASSED (100%).
- [x] Cập nhật tài liệu và đồng bộ trạng thái `.ai/`.
