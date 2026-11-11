# ACTIVE TASK — BINH 13 ANALYZER

**Nhiệm vụ hiện tại:** Tự động xác nhận kết thúc ván / cộng tiền và chia bài mới theo nhịp game thời gian thực (Real-time Game Rhythm Auto-Detection) thay thế thời gian chờ thủ công.  
**Người yêu cầu:** User / Product Owner  
**Trạng thái nhiệm vụ:** `COMPLETED` (Đã hoàn thiện 100%, 167/167 tests PASSED)

---

## 1. MỤC TIÊU VÀ BỐI CẢNH
- **Vấn đề thực tế:** Việc thiết lập thời gian cố định (`spin_round_time` & `spin_cooldown`) gây lệch với nhịp độ game thực tế vì thời gian so bài, người chơi xếp bài và animation trả thưởng (+ tiền) thay đổi liên tục. Nếu đặt quá dài thì bot lỡ nhịp ván mới, nếu đặt quá ngắn thì bot nhận diện nhầm khi game chưa dọn bài xong.
- **Yêu cầu của người dùng:** Hệ thống phải tự động nhận diện được thời điểm game tính toán + tiền xong, gom bài cũ đi và chia bài mới ra thì hệ thống tự động binh ván mới ngay lập tức mà không cần xác nhận thủ công hay đếm ngược thời gian chờ.

---

## 2. GIẢI PHÁP & CÁC NÂNG CẤP ĐÃ TRIỂN KHAI

1. **Chế độ Tự động theo nhịp game (`chk_auto_game_timing`):**
   - Bổ sung tùy chọn `⚡ Tự động theo nhịp game (Tự phát hiện cộng tiền xong & chia bài mới)` trên thanh công cụ Tab 6 (bật mặc định).
   - Khi bật chế độ này:
     - 2 ô SpinBox thời gian (`spin_round_time` và `spin_cooldown`) và nút `[ 🔓 Mở khóa ]` tự động làm mờ (disabled) với tooltip hướng dẫn trực quan.
     - Hệ thống vận hành hoàn toàn theo mô hình Event-Driven dựa trên thị giác máy tính thay vì timer cứng.
   - Khi tắt: Trả lại quyền kiểm soát đếm ngược thủ công cho người dùng.

2. **Cơ chế Event-Driven phát hiện kết thúc ván, so bài & cộng tiền:**
   - Khi binh xong một bàn (`_finalize_round_and_lockdown`), hệ thống không đặt `window_cooldown_remaining` dài để tránh làm mù scanner, mà chuyển trạng thái sang `⏳ Đang theo dõi game so bài & cộng tiền...` và nút `⏳ Chờ game tính tiền...`.
   - Vision Scanner tiếp tục theo dõi frame bàn chơi liên tục trong nền.
   - **Nhận diện dọn bàn / cộng tiền xong:** Khi hiệu ứng so bài và trả thưởng diễn ra, bài cũ được gom đi (`len(valid_cards) < 10`), hệ thống tự động bật cờ `has_seen_table_cleared[window_id] = True`, cập nhật trạng thái `⏳ Ván cũ đã dọn (Game đã tính tiền / dọn bàn xong) — Đang chờ chia bài ván mới...` và nút `⏳ Đang chờ chia bài mới...`.

3. **Tự động kích hoạt ván mới & Binh bài tức thì:**
   - Khi 13 lá bài mới được chia xong:
     - Tính hash vị trí `CardStateManager.compute_position_invariant_hash(state.detected_cards)`.
     - So khớp với hash của ván trước đó: `curr_hash != last_binned_hashes[window_id]` (xác suất trùng ngẫu nhiên là $\approx 1.57 \times 10^{-12}$).
     - Bộ lọc chống nhiễu Debounce qua $\ge 2$ frame ổn định (hoặc $\ge 3$ frame nếu chưa qua giai đoạn dọn bàn) loại bỏ hiện tượng giật lag khi bài đang lật.
     - Hệ thống tự động:
       - Tăng số ván bài `#N` và cập nhật badge ván mới.
       - Cập nhật nhãn trạng thái `🎯 Phát hiện Ván mới #N! Đã nhận diện đủ 13 lá — Binh bài ngay!`.
       - Kích hoạt nút `⚡ Tự Động Binh Bài (Ván #N)`.
       - Nếu đang bật chế độ Tự động binh liên tục (`is_auto_loop_enabled`), ván bài được tự động đẩy vào hàng đợi `auto_loop_queue` và điều khiển chuột binh bài tự động ngay lập tức.

---

## 3. KẾT QUẢ KIỂM THỬ THỰC TẾ
- `tests/test_auto_binh.py`: **25/25 tests PASSED**.
- `tests/test_layout_355.py`: **7/7 tests PASSED**.
- `tests/test_multi_window.py`: **13/13 tests PASSED**.
- Toàn bộ test suite dự án: **167/167 tests PASSED (100%)**.
