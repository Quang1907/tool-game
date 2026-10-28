# MASTER CONTEXT — BINH 13 ANALYZER (macOS)

> **DÀNH CHO MỌI AI AGENT KHI BẮT ĐẦU PHIÊN LÀM VIỆC:**  
> File này là **Điểm vào duy nhất (Single Entry Point)**. Đọc file này trước tiên để hiểu bối cảnh, quy tắc và định vị chính xác tài liệu cần đọc tiếp theo mà không cần đọc lại toàn bộ mã nguồn.

---

## 1. PROJECT NÀY LÀ GÌ?
- **Tên dự án:** Binh 13 Analyzer (Mậu Binh / Chinese Poker Analyzer for macOS).
- **Mục tiêu cốt lõi:** Ứng dụng Desktop chuyên nghiệp trên macOS (Apple Silicon ARM64 & Intel), kết hợp **Computer Vision** (nhận diện bài tự do từ màn hình, hỗ trợ 3 bàn chơi cùng lúc, thư viện ảnh mẫu tự học) và **Monte Carlo EV Optimization** (giải 36,036 thế bài, mô phỏng 10,000+ ván đấu với Common Random Numbers để tìm cách xếp bài có giá trị kỳ vọng điểm số cao nhất).
- **Công nghệ chính:** Python 3.11.17 (`.venv`), PySide6 (Qt 6.8+), OpenCV, NumPy, SQLite 3.
- **Entry Point:** [app/main.py](file:///Users/levanquang/tool/app/main.py) | **Cách chạy:** `.venv/bin/python -m app.main`.
- **Cách test:** `.venv/bin/pytest tests/` (Hiện tại: 116/116 tests passed 100%).

---

## 2. NGUYÊN TẮC BẤT KHẢ XÂM PHẠM (MASTER RULES)
1. **Never mock reality:** Test phải chạy code thật, dữ liệu thật, không mock để che giấu lỗi.
2. **Không tạo project mới, không viết lại toàn bộ kiến trúc:** Sửa trực tiếp trên repo hiện tại.
3. **Phạm vi tác động tối thiểu:** Chỉ sửa các file thuộc phạm vi nhiệm vụ; không sửa module khác nếu không liên quan.
4. **Không nhận diện avatar thành bài:** Bắt buộc chạy Candidate Validation; nếu không phải bài thì trả về `card=None, conf=0.0`, không đoán mò.
5. **Zero UI Lag:** Mọi tác vụ nặng (Solver, Simulation, Capture) **bắt buộc chạy trên `QThread`**.
6. **Chi tiết đầy đủ:** Đọc [.ai/MASTER_RULES.md](file:///Users/levanquang/tool/.ai/MASTER_RULES.md).

---

## 3. BẢN ĐỒ ĐIỀU HƯỚNG TÀI LIỆU (DOCUMENTATION MAP)

| Mục đích cần tra cứu | File tài liệu chỉ định |
|---|---|
| **Quy tắc làm việc 5 bước của AI** | [.ai/workflows/SESSION_WORKFLOW.md](file:///Users/levanquang/tool/.ai/workflows/SESSION_WORKFLOW.md) |
| **Quy chế phê duyệt thay đổi (Change Policy)** | [.ai/workflows/CHANGE_APPROVAL_POLICY.md](file:///Users/levanquang/tool/.ai/workflows/CHANGE_APPROVAL_POLICY.md) |
| **Trạng thái kỹ thuật hiện tại** | [.ai/state/CURRENT_STATE.md](file:///Users/levanquang/tool/.ai/state/CURRENT_STATE.md) |
| **Nhiệm vụ đang thực hiện** | [.ai/state/ACTIVE_TASK.md](file:///Users/levanquang/tool/.ai/state/ACTIVE_TASK.md) |
| **Nhiệm vụ tiếp theo & Ưu tiên** | [.ai/state/NEXT_ACTIONS.md](file:///Users/levanquang/tool/.ai/state/NEXT_ACTIONS.md) |
| **Vấn đề đã biết & Nợ kỹ thuật** | [.ai/state/KNOWN_ISSUES.md](file:///Users/levanquang/tool/.ai/state/KNOWN_ISSUES.md) |
| **Báo cáo kiểm thử & 116 test cases** | [.ai/state/TEST_STATUS.md](file:///Users/levanquang/tool/.ai/state/TEST_STATUS.md) |
| **Bản đồ file mã nguồn theo nhiệm vụ** | [.ai/MODULE_MAP.md](file:///Users/levanquang/tool/.ai/MODULE_MAP.md) |
| **Kiến trúc tổng thể & Nguyên tắc tầng** | [.ai/ARCHITECTURE.md](file:///Users/levanquang/tool/.ai/ARCHITECTURE.md) |
| **Luồng dữ liệu đầu-cuối** | [.ai/DATA_FLOW.md](file:///Users/levanquang/tool/.ai/DATA_FLOW.md) |
| **Luật Mậu Binh & Bảng điểm chi tiết** | [.ai/GAME_RULES.md](file:///Users/levanquang/tool/.ai/GAME_RULES.md) |
| **Quyết định kiến trúc (ADR)** | [.ai/DECISIONS.md](file:///Users/levanquang/tool/.ai/DECISIONS.md) |
| **Nhật ký thay đổi phiên bản** | [.ai/logs/CHANGELOG.md](file:///Users/levanquang/tool/.ai/logs/CHANGELOG.md) |

---

## 4. QUY TRÌNH KHI BẮT ĐẦU VÀ KẾT THÚC MỘT TASK

1. **Bắt đầu:**
   - Kiểm tra `git status` (không đè code chưa commit của người dùng).
   - Tra cứu [.ai/MODULE_MAP.md](file:///Users/levanquang/tool/.ai/MODULE_MAP.md) để biết file cần đọc/sửa.
   - Lập kế hoạch theo [.ai/workflows/SESSION_WORKFLOW.md](file:///Users/levanquang/tool/.ai/workflows/SESSION_WORKFLOW.md).
2. **Triển khai & Kiểm thử:**
   - Sửa code tối thiểu.
   - Chạy test tương ứng trong `tests/`.
   - Chạy toàn bộ `.venv/bin/pytest tests/` để kiểm tra hồi quy.
3. **Kết thúc (Đồng bộ):**
   - Cập nhật [.ai/state/CURRENT_STATE.md](file:///Users/levanquang/tool/.ai/state/CURRENT_STATE.md) và [.ai/logs/CHANGELOG.md](file:///Users/levanquang/tool/.ai/logs/CHANGELOG.md).
   - Báo cáo kết quả và minh chứng test đã chạy thật.
