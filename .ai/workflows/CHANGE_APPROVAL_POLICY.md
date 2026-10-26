# CHANGE APPROVAL POLICY — BINH 13 ANALYZER

Tài liệu này phân định ranh giới giữa những thay đổi AI được phép tự chủ thực hiện và những thay đổi **bắt buộc phải có sự phê duyệt** của người dùng.

---

## 1. THAY ĐỔI ĐƯỢC PHÉP TỰ CHỦ THỰC HIỆN (AUTONOMOUS CHANGES)

AI được phép chủ động thực hiện mà không cần xin phép trước nếu thỏa mãn toàn bộ test:
1. **Sửa lỗi cục bộ (Bug Fixes):** Sửa lỗi trong phạm vi module được yêu cầu (ví dụ: sửa padding nút UI, sửa candidate validation của detector, sửa mapping tọa độ crop).
2. **Bổ sung bài kiểm thử (Adding Tests):** Thêm test case vào `tests/` để tái hiện lỗi, kiểm chứng edge-case hoặc nâng cao độ bao phủ (coverage).
3. **Cập nhật tài liệu & trạng thái:** Tạo và cập nhật tài liệu trong `.ai/`, ghi chép changelog, cập nhật kết quả test.
4. **Tối ưu hóa nội bộ hàm:** Tối ưu hóa hiệu năng bên trong một method mà không làm thay đổi input/output và không phá vỡ tính tất định.
5. **Thêm phương thức phụ trợ nội bộ (Private Helpers):** Tạo các hàm nội bộ có tiền tố `_` để chia nhỏ code cho dễ bảo trì.

---

## 2. THAY ĐỔI BẮT BUỘC PHẢI CÓ PHÊ DUYỆT (REQUIRES USER APPROVAL)

AI **tuyệt đối không được tự ý thực hiện** các thay đổi sau trừ khi có yêu cầu rõ ràng từ người dùng:

| Hạng mục thay đổi | Lý do cấm tự ý thay đổi | Quy trình bắt buộc |
|---|---|---|
| **Thay đổi cấu trúc toàn bộ dự án / Refactoring diện rộng** | Rủi ro gây mất ổn định và phá vỡ 104 test đang chạy | Ghi đề xuất vào `.ai/DECISIONS.md` với trạng thái `PROPOSED` và hỏi ý kiến người dùng. |
| **Thay đổi Public Interface của Domain Core** (`Card`, `Hand`, `Solver`, `Evaluator`) | Ảnh hưởng diện rộng đến toàn bộ các phân hệ UI, Services, Tests | Đánh giá impact matrix, thông báo các nơi bị ảnh hưởng và chờ phê duyệt. |
| **Thêm thư viện bên ngoài vào `pyproject.toml`** | Tăng kích thước ứng dụng và rủi ro tương thích Apple Silicon | Nêu rõ lý do tại sao các thư viện hiện có (`numpy`, `cv2`, `PySide6`) không giải quyết được. |
| **Sửa đổi Schema SQLite không tương thích ngược** | Nguy cơ mất dữ liệu ván bài và thư viện ảnh mẫu đã lưu | Viết migration script bảo toàn dữ liệu cũ trước khi đề xuất. |
| **Thay đổi luật tính điểm mặc định (`default_rules.json`)** | Ảnh hưởng đến tính chính xác của solver và kỳ vọng EV | Xác nhận luật nhà cái/luật chơi cụ thể với người dùng. |
| **Can thiệp mạng hoặc bộ nhớ game** | Vi phạm nguyên tắc bảo mật và an toàn tài khoản người dùng | Nghiêm cấm tuyệt đối. |
