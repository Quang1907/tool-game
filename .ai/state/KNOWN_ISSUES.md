# KNOWN ISSUES & TECHNICAL DEBT — BINH 13 ANALYZER

Tài liệu này ghi nhận toàn bộ các vấn đề đã biết, cảnh báo hệ thống và nợ kỹ thuật (Technical Debt) cần lưu ý.

---

## 1. CÁC VẤN ĐỀ ĐÃ BIẾT (KNOWN ISSUES)

### ISSUE 1: Cảnh báo Font "SF Pro Text" khi khởi động trên macOS
- **Mức độ:** Nhẹ (Cosmetic Warning).
- **Hiện tượng:** Khi chạy `python -m app.main`, terminal xuất hiện log:
  ```text
  qt.qpa.fonts: Populating font family aliases took 68 ms. Replace uses of missing font family "SF Pro Text" with one that exists to avoid this cost.
  ```
- **Nguyên nhân:** Qt QPA font engine tìm kiếm tên font chuẩn PostScript của Apple. Trong `app/ui/styles.py`, một số quy tắc sử dụng `"SF Pro Text"`.
- **Giải pháp đề xuất:** Thay thế bằng `".AppleSystemUIFont"` hoặc `"-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto"` để loại bỏ hoàn toàn 68ms trễ khi khởi động.
- **Trạng thái:** `DOCUMENTED` (Không ảnh hưởng đến chức năng).

### ISSUE 2: Quyền truy cập Screen Recording trên macOS Sequoia
- **Mức độ:** Trung bình (Quyền hệ thống macOS).
- **Hiện tượng:** Khi bấm "Chụp màn hình", nếu macOS chưa cấp quyền Screen Recording cho Terminal/Python/App, ảnh chụp sẽ chỉ trả về nền xám hoặc trống.
- **Giải pháp:** Cần cấp quyền trong **System Settings $\rightarrow$ Privacy & Security $\rightarrow$ Screen Recording** cho ứng dụng hoặc Terminal. `screen_capture.py` đã có cơ chế chẩn đoán và thông báo cho người dùng, hỗ trợ nạp file ảnh thay thế.
- **Trạng thái:** `MITIGATED`.

### ISSUE 3: Lá bài bị che khuất quá sâu (Extreme Occlusion)
- **Mức độ:** Thấp.
- **Hiện tượng:** Khi trong game các lá bài xòe quá hẹp (chỉ lộ dưới 15% diện tích và mất toàn bộ góc số), detector không thể phát hiện số bài.
- **Giải pháp:** Hệ thống chủ động kích hoạt cờ `is_uncertain = True`, mở `CardEditDialog` để người dùng xác nhận nhanh bằng 1 cú click.
- **Trạng thái:** `VERIFIED` (Graceful Degradation).

---

## 2. NỢ KỸ THUẬT (TECHNICAL DEBT)

1. **Phụ thuộc vào Template Matching thay vì mô hình Deep Learning:**
   - **Hiện tại:** Sử dụng Multi-scale Template Matching kết hợp Reference Library. Độ chính xác rất cao khi đã có mẫu, nhưng cần người dùng xác nhận vài mẫu đầu tiên.
   - **Định hướng:** Khi có đủ 500+ mẫu thực tế từ người dùng, có thể huấn luyện một model MobileNetV3 hoặc YOLO-nano xuất ra ONNX để nhận diện $100\%$ không cần đối chiếu.
