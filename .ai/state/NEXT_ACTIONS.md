# NEXT RECOMMENDED ACTIONS — BINH 13 ANALYZER

Tài liệu này định hướng các bước hành động tiếp theo cho các phiên AI tương lai dựa trên trạng thái kỹ thuật thực tế.

---

## 1. NHIỆM VỤ ƯU TIÊN CAO (HIGH PRIORITY)

1. **Thu thập và làm giàu Thư Viện Ảnh Mẫu (52 lá):**
   - **Mục tiêu:** Hiện tại `tests/fixtures/real_samples/` có 9 ảnh mẫu thực tế (KD, KC, JC, JH, 7D, 6D, 5D, 4H...). Khi người dùng chơi game thực tế, cần tiếp tục xác nhận qua `CardEditDialog` và bấm **"Lưu làm ảnh mẫu"** để bao phủ đủ 52 lá bài.
   - **Tác động:** Giúp tỷ lệ nhận diện đạt $100\%$ tự động, không còn xuất hiện trạng thái `UNCERTAIN`.

2. **Thực nghiệm thực địa với 3 cửa sổ game thực tế (Field Testing):**
   - **Mục tiêu:** Mở 3 cửa sổ game Binh 13 thực tế trên MacBook, chuyển sang Tab **"2. Multi-Window"**, bấm nạp 3 ROI và kiểm tra khả năng tự động nhận diện đồng thời khi bài được chia.
   - **Xác minh:** Kiểm tra xem `card_tracker` có nhận diện đúng trạng thái bài di chuyển (không tính lại) so với bài mới chia (tự động giải bài) hay không.

3. **Kiểm tra đóng gói macOS Bundle (`.app`):**
   - **Mục tiêu:** Chạy `./scripts/build_macos.sh` để kiểm tra quá trình tạo file `dist/Binh13Analyzer.app`.
   - **Xác minh:** Đảm bảo PyInstaller đóng gói đầy đủ `PySide6`, `cv2`, font bitmap và chạy được độc lập mà không cần môi trường terminal.

---

## 2. NHIỆM VỤ ƯU TIÊN TRUNG BÌNH (MEDIUM PRIORITY)

1. **Tối ưu tốc độ Monte Carlo EV cho 20,000+ ván:**
   - **Hiện tại:** `EVOptimizer` chạy bằng NumPy vectorization cho 1,000 - 5,000 ván trong ~1.5 giây.
   - **Đề xuất:** Cân nhắc tích hợp multiprocessing hoặc Numba nếu người dùng muốn mô phỏng 50,000 ván trong dưới 1 giây.

2. **Thông báo âm thanh macOS khi phát hiện thế bài mạnh:**
   - **Mục tiêu:** Thêm tùy chọn phát âm thanh native qua `NSSound` (System sounds của macOS) khi phát hiện bài Thắng Trắng (Sảnh Rồng, 6 Đôi, 3 Sảnh) hoặc khi một trong 3 bàn có bài mới được chia.

---

## 3. ĐIỀU KIỆN TIÊN QUYẾT ĐỂ BẮT ĐẦU NHIỆM VỤ MỚI

Trước khi nhận bất kỳ nhiệm vụ nào phía trên:
1. Đọc `.ai/MASTER_RULES.md` và `.ai/state/CURRENT_STATE.md`.
2. Kiểm tra Git status (phải clean, không đè code chưa commit của người dùng).
3. Đọc đúng file trong `MODULE_MAP.md`.
4. Viết plan và thực hiện theo quy trình bắt buộc.
