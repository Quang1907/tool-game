# MODULE DOCUMENTATION: APPLICATION SERVICES (`app/services/`)

---

## 1. MỤC ĐÍCH & PHẠM VI

Phân hệ Application Services đóng vai trò lớp trung gian điều phối (Orchestration Layer):
1. Kết nối giao diện người dùng (`app/ui/`) với các thuật toán miền (`app/core/`), thị giác máy tính (`app/vision/`) và cơ sở dữ liệu (`app/database/`).
2. Quản lý các worker thread (`QThread`) chạy ngầm, đảm bảo ứng dụng không bao giờ bị đơ (Unresponsive).
3. Duy trì trạng thái đồng thời của 3 cửa sổ bàn chơi game Binh 13 trên macOS.

---

## 2. CÁC SERVICES CHÍNH

### 2.1. `simulation_service.py`
- `SimulationWorker(QThread)`:
  - Nhận danh sách các thế bài ứng viên, số lượng ván mô phỏng (ví dụ 10,000), số đối thủ (1..3) và seed ngẫu nhiên.
  - Chạy `EVOptimizer` trên luồng phụ.
  - Định kỳ phát tín hiệu `progress = Signal(int, float)` cập nhật phần trăm hoàn thành và ETA cho UI.
  - Phát tín hiệu `finished = Signal(list)` khi hoàn tất, trả về danh sách kết quả EV.
  - Hỗ trợ dừng tức thì khi người dùng bấm Hủy (`cancel()`).

### 2.2. `analysis_service.py`
- `AnalysisService`:
  - Tiếp nhận danh sách 13 lá bài từ Vision hoặc CardSelector.
  - Khởi tạo `Hand`, gọi `Solver.solve()` để trích xuất toàn bộ thế bài hợp lệ.
  - Đánh giá thế bài có thuộc nhóm Mậu Binh Thắng Trắng hay không.
  - Chuẩn bị dữ liệu cho tầng UI và Simulator.

### 2.3. `multi_window_service.py`
- `MultiWindowService`:
  - Quản lý 3 bàn chơi đồng thời (`TableState` cho Table 1, Table 2, Table 3).
  - Tiếp nhận 1 ảnh chụp chung toàn màn hình $\rightarrow$ gọi `ROIManager.crop_rois()` lấy 3 ảnh bàn chơi.
  - Đối với từng bàn, gọi `CardDetector` và `CardRecognizer`.
  - **Tối ưu hóa tránh tính toán thừa (Position-Invariance):**
    Sử dụng `frozenset` mã bài để tạo `position_invariant_hash`.
    - Nếu 13 lá bài chỉ di chuyển vị trí, xòe lại hoặc lệch hàng: **Giữ nguyên kết quả, không chạy lại Solver.**
    - Nếu phát hiện bài mới chia: Tự động kích hoạt Solver và thông báo cho UI bàn chơi tương ứng.

---

## 3. NGUYÊN TẮC LUỒNG (THREADING INVARIANTS)

1. **Tuyệt đối không truy cập hoặc sửa đổi GUI Widget từ bên trong `QThread.run()`:**
   Mọi dữ liệu truyền từ background thread về GUI bắt buộc phải thông qua `Signal.emit()`.
2. **Xử lý ngoại lệ trong Worker:**
   Worker thread phải bắt toàn bộ ngoại lệ và emit tín hiệu `error = Signal(str)` thay vì để thread bị crash âm thầm.
