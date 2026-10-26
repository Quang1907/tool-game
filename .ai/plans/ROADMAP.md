# PRODUCT ROADMAP — BINH 13 ANALYZER (macOS)

---

## 1. GIAI ĐOẠN 1: NỀN TẢNG CỐT LÕI & SOLVER TỐI ƯU (ĐÃ HOÀN THÀNH - V1.0)
- [x] Mô hình hóa bộ bài chuẩn 52 lá, giá trị, chất, unicode, bitmask ID ($0..51$).
- [x] Bộ đánh giá thứ bậc bài Chi Đầu (3 lá), Chi Giữa (5 lá), Chi Cuối (5 lá), kiểm tra Foul.
- [x] Thuật toán phân rã tổ hợp 36,036 thế bài và lọc bài Lủng.
- [x] Mô phỏng đối thủ ảo Monte Carlo sử dụng kỹ thuật Common Random Numbers (CRN).
- [x] Giao diện Desktop PySide6 Dark Theme chuẩn Apple HIG.
- [x] Lưu trữ phiên chơi và kết quả tính toán vào SQLite database cục bộ.
- [x] Đạt 100% kiểm thử (49 unit tests ban đầu).

---

## 2. GIAI ĐOẠN 2: THỊ GIÁC MÁY TÍNH & THƯ VIỆN MẪU (ĐÃ HOÀN THÀNH - V1.1)
- [x] Chụp ảnh màn hình macOS Retina (1x sang 2x coordinate mapping).
- [x] Tiền xử lý ảnh: perspective warp đưa về chuẩn 120x168, khử viền xanh chọn bài trong game.
- [x] Phát hiện vị trí bài ngẫu nhiên, không dùng ô cố định; tách bài xòe bằng margin gradient peaks.
- [x] Nhận diện độc lập Rank và Suit qua Multi-scale Template Matching.
- [x] Xây dựng Thư viện ảnh mẫu đã xác nhận (`CardReferenceLibrary`) lưu trong SQLite.
- [x] Dialog sửa bài (`CardEditDialog`) với 13 nút Rank, 4 nút Suit, lưới 52 lá, xem ảnh mẫu tương tự.
- [x] Dialog chẩn đoán thị giác (`VisionDebugDialog`) với 4 góc nhìn chi tiết.
- [x] Khắc phục triệt để lỗi avatar bị nhận diện thành `KD 50%` và lỗi nút Rank bị trống.
- [x] Đạt 104/104 unit tests passed.

---

## 3. GIAI ĐOẠN 3: GIÁM SÁT 3 CỬA SỔ BÀN CHƠI THỰC TẾ (HIỆN TẠI - V1.2)
- [x] Kiến trúc Multi-Window: Chụp 1 frame màn hình chung, crop 3 vùng ROI độc lập.
- [x] Bộ theo dõi quân bài (`CardTracker`) bất biến vị trí (`position_invariant_hash`), không tính lại khi bài chỉ di chuyển.
- [x] Giao diện Tab 2 giám sát đồng thời 3 bàn chơi.
- [ ] Thực nghiệm thực địa với 3 client game thật đang chạy trên macOS.
- [ ] Thu thập đủ 52 mẫu ảnh thực tế từ các bàn chơi khác nhau vào thư viện.

---

## 4. GIAI ĐOẠN 4: HỌC SÂU & MỞ RỘNG (TƯƠNG LAI - V2.0)
- [ ] Huấn luyện mô hình ONNX siêu nhẹ (YOLO-nano hoặc MobileNetV3) khi có đủ 500+ mẫu thực tế.
- [ ] Tích hợp inference ONNX trực tiếp vào `card_recognizer.py` để đạt tốc độ nhận diện dưới 10ms.
- [ ] Tối ưu hóa mô phỏng Monte Carlo 50,000 ván bằng C-extension / Cython.
- [ ] Tự động phát âm thanh cảnh báo bài Thắng Trắng qua macOS native `NSSound`.
- [ ] Tự động cập nhật (Auto-updater) cho ứng dụng macOS `.app`.
