# MODULE DOCUMENTATION: UI PRESENTATION (`app/ui/`)

---

## 1. MỤC ĐÍCH & PHẠM VI

Phân hệ UI Presentation xây dựng trên **PySide6 (Qt 6.8+)** cung cấp giao diện desktop native cho macOS theo phong cách Apple Human Interface Guidelines:
1. Giao diện Dark Theme cao cấp, độ tương phản cao, tối ưu cho màn hình Retina.
2. Trải nghiệm người dùng mượt mà, **Zero UI Lag**: Toàn bộ thuật toán Solver, mô phỏng Monte Carlo và xử lý ảnh chạy trên worker thread (`QThread`).
3. Khả năng tương tác trực tiếp với ảnh chụp: phóng to, thu nhỏ, kéo pan, click vào bounding box trên ảnh để mở dialog sửa bài.
4. Cung cấp đầy đủ công cụ chẩn đoán chuyên sâu (`VisionDebugDialog`) và quản trị ảnh mẫu (`CardReferenceManagerDialog`).

---

## 2. CÁC THÀNH PHẦN CHÍNH TRONG `app/ui/`

### 2.1. `main_window.py`
Cửa sổ chính của ứng dụng với thanh điều hướng 5 Tab:
1. **Vision (Đơn bàn):** Chụp màn hình bàn chơi, phát hiện 13 lá bài, duyệt bài nghi ngờ, mở debug dialog.
2. **Multi-Window (3 bàn):** Giám sát và nhận diện đồng thời 3 cửa sổ game Binh 13 trên một màn hình MacBook.
3. **Solver:** Khám phá bảng xếp hạng các cách xếp chi (Front, Middle, Back), điểm heuristic và kiểm tra bài lủng.
4. **Simulator:** Điều khiển mô phỏng Monte Carlo, hiển thị tiến độ (Progress bar), tính toán EV, win rate và 95% CI.
5. **History:** Xem lại lịch sử các ván bài đã lưu trong SQLite, tìm kiếm và phân tích lại.

### 2.2. `components/card_edit_dialog.py` ("Xác nhận & Sửa kết quả lá bài")
- Dialog mở ra khi người dùng click vào lá bài trên giao diện hoặc bấm "Duyệt bài nghi ngờ".
- **Hàng nút Rank (13 nút):**
  - Thứ tự: `A, 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K`.
  - Kích thước: `36x30 px`, `padding: 0; font-size: 12px; font-weight: 600; color: #FFFFFF; background-color: #2C2C2E;`.
  - **Click Rank giữ nguyên Suit hiện tại.**
- **Hàng nút Suit (4 nút):**
  - Thứ tự: `♠ Bích`, `♣ Tép`, `♦ Rô`, `♥ Cơ`.
  - **Click Suit giữ nguyên Rank hiện tại.**
- **Lưới 52 lá bài (52-Card Grid):** Hiển thị toàn bộ bộ bài, đồng bộ highlight viền xanh `#0A84FF` khi người dùng chọn nút Rank hoặc Suit.
- **Nút "Lưu làm ảnh mẫu":** Lưu ảnh thực tế vào `CardReferenceLibrary` dưới mã quân bài đang chọn; từ chối lưu nếu ảnh là `NON_CARD_OBJECT`.

### 2.3. `components/vision_debug_dialog.py` ("Chẩn đoán Thị giác Máy tính")
Cung cấp 4 Tab chẩn đoán toàn diện:
1. **1. Original Frame:** Ảnh gốc chưa qua xử lý, kích thước và kênh màu.
2. **2. Detection Overlay:** Khung nhận diện bounding box, polygon, danh sách đối tượng được chấp nhận, đối tượng bị loại và trùng lặp.
3. **3. Individual Card Crop:** So sánh ảnh gốc (Source Patch) tại tọa độ `(x, y, w, h)`, ảnh chuẩn hóa $120 \times 168\text{ px}$, thông số Crop Validation Status. Nếu đối tượng không phải bài, hiển thị nhãn đỏ `[ĐỐI TƯỢNG KHÔNG PHẢI LÁ BÀI]`.
4. **4. Recognition & Reference:** So sánh Rank Crop, Suit Crop, Query Crop và Ảnh mẫu khớp từ thư viện. Báo `Không hợp lệ` nếu crop thiếu cấu trúc bài.

### 2.4. `components/zoomable_viewer.py`
- Lớp kế thừa từ `QGraphicsView` hỗ trợ zoom mượt bằng trackpad/con lăn chuột, kéo pan bằng chuột trái.
- Phương thức `mapToScene()` chuyển đổi chính xác tọa độ click chuột trên viewport màn hình thành tọa độ pixel thực tế trên ảnh gốc của game.

---

## 3. NGUYÊN TẮC THIẾT KẾ CẦN TUÂN THỦ KHI SỬA UI

1. **Quy tắc Padding cho Button nhỏ:**
   Quy tắc CSS toàn cục trong `styles.py` có `padding: 7px 16px`. Bất kỳ QPushButton nào có chiều rộng nhỏ hơn 40px **bắt buộc phải có inline style `padding: 0;`** để tránh bị co mất chữ.
2. **Không gọi logic nặng trên Main Thread:**
   Tất cả các lệnh tính toán Solver hay Simulation phải gọi thông qua Services và Worker Thread.
