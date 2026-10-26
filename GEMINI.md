# GEMINI MASTER INSTRUCTIONS — BINH 13 ANALYZER (macOS)

Tài liệu này là chỉ dẫn cao nhất dành cho Gemini Coding Assistant khi làm việc trong repository Binh 13 Analyzer.

---

## 1. ĐIỂM BẮT ĐẦU BẮT BUỘC (MANDATORY FIRST STEP)

Khi bắt đầu bất kỳ phiên làm việc nào hoặc nhận bất kỳ yêu cầu nào từ người dùng:
1. **ĐỌC ĐẦU TIÊN:** [MASTER_CONTEXT.md](file:///Users/levanquang/tool/MASTER_CONTEXT.md).
2. **ĐỌC TRẠNG THÁI HIỆN TẠI:** [.ai/state/CURRENT_STATE.md](file:///Users/levanquang/tool/.ai/state/CURRENT_STATE.md) và [.ai/state/ACTIVE_TASK.md](file:///Users/levanquang/tool/.ai/state/ACTIVE_TASK.md).
3. **TRA CỨU FILE CẦN ĐỌC:** [.ai/MODULE_MAP.md](file:///Users/levanquang/tool/.ai/MODULE_MAP.md).
4. **KIỂM TRA GIT:** Chạy lệnh `git status` trước khi sửa file. Tuyệt đối không xóa hoặc ghi đè các thay đổi chưa commit của người dùng.

---

## 2. QUY TRÌNH 5 BƯỚC BẮT BUỘC (5-STEP WORKFLOW)

Mọi nhiệm vụ phải tuân thủ nghiêm ngặt quy trình trong [.ai/workflows/SESSION_WORKFLOW.md](file:///Users/levanquang/tool/.ai/workflows/SESSION_WORKFLOW.md):
1. **START SESSION:** Đọc context, kiểm tra git, xác định phạm vi.
2. **PLAN:** Xác định mục tiêu, rủi ro, file sửa, tiêu chí nghiệm thu.
3. **IMPLEMENT:** Triển khai từng bước nhỏ, bảo toàn kiến trúc, không mở rộng phạm vi tùy tiện.
4. **VERIFY:** Chạy test thực tế bằng `.venv/bin/pytest`. Tuyệt đối không tuyên bố pass nếu chưa chạy lệnh.
5. **SYNC:** Cập nhật trạng thái trong `.ai/state/` và ghi nhật ký vào `.ai/logs/CHANGELOG.md`.

---

## 3. CÁC QUY TẮC BẤT KHẢ XÂM PHẠM

- **Không tạo project mới, không viết lại toàn bộ kiến trúc.**
- **Never mock reality:** Test phải chạy trên code và dữ liệu thật.
- **Không nhận diện avatar thành lá bài:** Bắt buộc có candidate validation; nếu crop không phải bài thì trả về `card=None, confidence=0.0`.
- **Zero UI Lag:** Mọi tác vụ nặng chạy trên `QThread`.
- **Quy tắc phê duyệt thay đổi:** Đọc [.ai/workflows/CHANGE_APPROVAL_POLICY.md](file:///Users/levanquang/tool/.ai/workflows/CHANGE_APPROVAL_POLICY.md).
- **Chi tiết toàn bộ quy tắc:** [.ai/MASTER_RULES.md](file:///Users/levanquang/tool/.ai/MASTER_RULES.md).
