# PROJECT VISION — BINH 13 ANALYZER (macOS)

---

## 1. TỔNG QUAN DỰ ÁN

**Binh 13 Analyzer** (còn gọi là công cụ phân tích Mậu Binh / Thập Tam Tức / Chinese Poker) là một ứng dụng desktop chuyên nghiệp dành riêng cho nền tảng **macOS (Apple Silicon & Intel)**.

Mục tiêu cốt lõi của dự án là cung cấp cho người chơi một trợ lý phân tích xác suất và sắp xếp bài tối ưu toán học theo thời gian thực, kết hợp công nghệ **Computer Vision (thị giác máy tính)** và thuật toán **Monte Carlo EV Optimization (tối ưu giá trị kỳ vọng)**.

---

## 2. MỤC TIÊU CUỐI CÙNG (END GOALS)

### 2.1. Phân Tích & Giải Bài Tối Ưu (Optimal Combinatorial Solver)
- Phân tích toàn bộ $\binom{13}{3} \times \binom{10}{5} / 2 = 36,036$ cách chia 13 lá thành 3 chi (Chi Đầu: 3 lá, Chi Giữa: 5 lá, Chi Cuối: 5 lá).
- Loại bỏ tuyệt đối bài Binh Lủng (Foul hands: $\text{Chi Cuối} \ge \text{Chi Giữa} \ge \text{Chi Đầu}$).
- Hỗ trợ các trường hợp Thắng Trắng (Sảnh Rồng, Lục Phé Bôn, 3 Sảnh, 3 Thùng, Đồng Hoa).

### 2.2. Mô Phỏng Xác Suất Monte Carlo & Tối Ưu EV
- Mô phỏng 1,000 đến 10,000+ ván đấu ảo chia ngẫu nhiên 39 lá bài còn lại cho 1 đến 3 đối thủ.
- Áp dụng kỹ thuật **Common Random Numbers (CRN)** để triệt tiêu phương sai khi so sánh các cách xếp bài.
- Tính toán chính xác: Giá trị kỳ vọng điểm số (Expected Value - EV), tỷ lệ thắng/hòa/thua từng chi, tỷ lệ Bắt Sập (Scoop) và khoảng tin cậy 95% ($95\%\text{ CI}$).

### 2.3. Thị Giác Máy Tính Đọc Bài Không Xâm Phạm (Non-Invasive Vision Pipeline)
- Chụp ảnh màn hình bàn chơi trực tiếp trên macOS (Retina display support) mà không can thiệp vào bộ nhớ game hay mạng.
- Tự động phát hiện 13 lá bài ở bất kỳ vị trí nào: xếp xòe hình quạt, chồng lấp một phần, lệch hàng, không phụ thuộc vào ô chia cố định.
- Nhận diện độc lập Rank và Suit với độ chính xác cao.
- **Thư viện ảnh mẫu tự học (Card Reference Library):** Cho phép người dùng xác nhận và lưu các quân bài thực tế để tăng độ chính xác lên $100\%$ cho các phiên chơi tiếp theo.
- Khả năng giám sát đồng thời **3 cửa sổ bàn chơi riêng biệt** trên một màn hình MacBook.

### 2.4. Trải Nghiệm Người Dùng macOS Chuẩn Mực
- Xây dựng trên **PySide6 (Qt 6)** tuân thủ Apple Human Interface Guidelines.
- Đảm bảo **Zero UI Lag**: Mọi tính toán nặng và quét hình ảnh đều chạy trên luồng nền (`QThread`).
- Lưu trữ lịch sử ván bài đầy đủ bằng SQLite database cục bộ.

---

## 3. RÀNG BUỘC PHẠM VI (SCOPE BOUNDARIES)

| Thuộc phạm vi (In-Scope) | Ngoài phạm vi (Out-of-Scope) |
|---|---|
| Chụp màn hình qua macOS OS API / Qt Screen Grabber | Đọc bộ nhớ tiến trình (RAM injection / Hooking) |
| Nhận diện hình ảnh các lá bài trên bàn | Can thiệp gói tin mạng game (Packet sniffing) |
| Hỗ trợ tối đa 3 bàn chơi cùng lúc | Tự động click chuột đánh bài thay người (Auto-bot clicker) |
| Tính toán EV toán học và xếp chi tối ưu | Thay đổi mã nguồn trò chơi của bên thứ ba |
| Lưu trữ SQLite cục bộ | Gửi dữ liệu ra server bên ngoài (No telemetry) |
