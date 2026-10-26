# PROJECT BACKLOG — BINH 13 ANALYZER (macOS)

Danh sách các hạng mục công việc tồn đọng (Backlog items) được sắp xếp theo mức độ ưu tiên.

---

## 1. HẠNG MỤC ƯU TIÊN CAO (NEAR-TERM BACKLOG)

### BL-01: Thu thập đủ 52 quân bài cho Thư Viện Ảnh Mẫu
- **Trạng thái:** `PLANNED`
- **Mô tả:** Hiện tại fixture có 9 mẫu bài (KD, KC, JC, JH, 7D, 6D, 5D, 4H). Cần tiếp tục lưu các lá bài còn lại qua `CardEditDialog` khi chơi thực tế.
- **Phụ thuộc:** Chơi game thực tế hoặc nạp ảnh chụp bàn chơi.
- **Tiêu chí nghiệm thu:** Cả 52 lá bài đều có ít nhất 1 mẫu đã xác nhận trong database.

### BL-02: Thay thế Font "SF Pro Text" trong `styles.py`
- **Trạng thái:** `PLANNED`
- **Mô tả:** Đổi font `"SF Pro Text"` thành `".AppleSystemUIFont"` trong `app/ui/styles.py` để loại bỏ 68ms cảnh báo font của Qt khi khởi động.
- **Phụ thuộc:** Không có.
- **Tiêu chí nghiệm thu:** Chạy `python -m app.main` không còn in log cảnh báo font.

### BL-03: Kiểm thử thực địa 3 cửa sổ game đồng thời
- **Trạng thái:** `PLANNED`
- **Mô tả:** Mở 3 cửa sổ game thật trên MacBook, gán 3 ROI và kiểm tra khả năng tự động giải bài khi ván mới bắt đầu.
- **Phụ thuộc:** Có 3 cửa sổ game đang hoạt động.
- **Tiêu chí nghiệm thu:** Cả 3 bàn đều nhận diện và hiển thị thế bài tối ưu độc lập.

---

## 2. HẠNG MỤC DÀI HẠN (LONG-TERM BACKLOG)

### BL-04: Đóng gói kiểm tra PyInstaller Bundle `.app`
- **Trạng thái:** `PLANNED`
- **Mô tả:** Chạy `./scripts/build_macos.sh`, kiểm tra file `.app` trên macOS Sequoia độc lập.
- **Tiêu chí nghiệm thu:** Ứng dụng khởi chạy thành công qua Finder bằng click đúp.

### BL-05: Tích hợp âm thanh cảnh báo bài Thắng Trắng (`NSSound`)
- **Trạng thái:** `PLANNED`
- **Mô tả:** Phát âm thanh thông báo macOS khi phát hiện thế bài Sảnh Rồng, 6 Đôi, 3 Sảnh.
- **Tiêu chí nghiệm thu:** Nghe được âm thanh hệ thống khi có bài thắng trắng.

### BL-06: Huấn luyện và tích hợp Model ONNX Card Classifier
- **Trạng thái:** `PLANNED`
- **Mô tả:** Huấn luyện mô hình CNN nhỏ gọn khi thu thập đủ 500+ mẫu bài thực tế.
- **Tiêu chí nghiệm thu:** Tốc độ nhận diện $< 10\text{ms}$ mỗi lá bài mà không cần nạp font bitmap.
