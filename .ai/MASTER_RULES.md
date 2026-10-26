# MASTER RULES — BINH 13 ANALYZER (macOS)

Tài liệu này chứa các quy tắc bất khả xâm phạm và bắt buộc áp dụng cho mọi AI Agent làm việc trên repository này.

---

## 1. NGUYÊN TẮC VẬN HÀNH TỐI CAO (CORE PRINCIPLES)

1. **Never mock reality (Không bao giờ giả lập thực tế):**
   - Mọi unit test và integration test phải chạy code thật trên dữ liệu/ảnh thật, không dùng mock để che giấu lỗi thuật toán.
2. **Deterministic Verification (Kiểm chứng tất định):**
   - Mọi tổ hợp bài (36,036 splits), tie-breaker của bộ bài (High Card, Pairs, Full House, Straight Flush) phải được chứng minh bằng toán học xác suất và combinatorial test.
3. **Graceful Degradation (Suy thoái mềm):**
   - Nếu thiếu thư viện bên ngoài hoặc chưa có model ONNX, hệ thống phải tự động fallback về Template Matching & Reference Library với thông báo chẩn đoán rõ ràng, không được crash ứng dụng.
4. **Safety & Privacy (An toàn & Riêng tư):**
   - Ứng dụng hoạt động theo cơ chế Computer Vision qua Screen Capture hoặc ảnh nạp vào. **Tuyệt đối KHÔNG** truy cập trực tiếp vào memory (RAM), reverse engineering client, hoặc can thiệp network packets của game.
   - Không chứa telemetry, không gửi dữ liệu ra bên ngoài.

---

## 2. QUY TẮC BẢO TOÀN VÀ THAY ĐỔI MÃ NGUỒN

1. **Không tạo project mới, không viết lại toàn bộ kiến trúc:**
   - Phải phát triển và sửa lỗi trực tiếp trên repository hiện tại.
2. **Phạm vi tác động tối thiểu (Minimal Scope):**
   - Chỉ chỉnh sửa các file thuộc phạm vi nhiệm vụ được giao.
   - Khi sửa lỗi một module (ví dụ Vision), **không được tự ý sửa** các module không liên quan (ví dụ Core Rules, Solver, Evaluator, Database).
3. **Bảo toàn giao diện công khai (Public Interface Preservation):**
   - Không được thay đổi signature của các class và method công khai (`Card`, `Hand`, `Solver`, `CardDetector`, `CardRecognizer`, `DatabaseManager`) mà không kiểm tra toàn bộ các nơi đang gọi (call-sites).
4. **Bảo toàn comment và docstring:**
   - Giữ nguyên các chú thích kỹ thuật, type annotations và docstring giải thích lý do thiết kế.

---

## 3. QUY TẮC NHẬN DIỆN HÌNH ẢNH (VISION RULES)

1. **Không coi mọi detection là lá bài:**
   - Phải thực hiện Candidate Validation trước khi đưa vào nhận diện rank/suit.
   - Các đối tượng: avatar người chơi, nút UI, nền bàn, text game phải bị loại bỏ với trạng thái `NON_CARD_OBJECT` hoặc `INVALID_CARD_CROP`.
2. **Không ép tạo lá bài giả:**
   - Khi một crop không thỏa mãn cấu trúc lá bài (thiếu góc số hoặc ký hiệu chất hợp lệ), hệ thống **phải trả về `card=None, confidence=0.0`**, không được đoán mò hoặc ép tạo card code (như `KD 50%`).
3. **Phân tách độc lập Rank và Suit:**
   - Rank và Suit phải được nhận diện bằng hai luồng độc lập: màu sắc (Red/Black) $\rightarrow$ Rank matching $\rightarrow$ Suit matching.
   - Không được lấy độ tương đồng của Suit để suy diễn Rank.
4. **Quy tắc thư viện ảnh mẫu (Reference Library):**
   - Ảnh mẫu chỉ được lưu khi có xác nhận từ người dùng (`user_confirmed`).
   - Tuyệt đối không tự động lưu dự đoán nghi ngờ hoặc crop lỗi thành ảnh mẫu.
   - Một ảnh mẫu chỉ được coi là khớp nếu Rank và Suit độc lập đều đạt ngưỡng tin cậy cao ($\ge 70\%$).

---

## 4. QUY TẮC GIAO DIỆN (UI & THREADING RULES)

1. **Zero UI Freeze (Không treo giao diện):**
   - Các tác vụ nặng: tính toán 36,036 thế bài (`Solver`), mô phỏng Monte Carlo 10,000 ván (`EVOptimizer`), quét nhận diện màn hình (`VisionService`) **bắt buộc chạy trong worker thread (`QThread`)**, giao tiếp với UI thông qua Qt Signals/Slots.
2. **Apple Human Interface Guidelines (macOS):**
   - Giao diện sử dụng dark theme sang trọng, độ tương phản chuẩn WCAG AA.
   - Hỗ trợ màn hình Retina Retina 2x coordinate mapping (`PassThrough` HighDPI policy).
   - Nút bấm phải có kích thước tối thiểu, không bị clipping chữ do xung đột padding.

---

## 5. QUY TẮC QUẢN LÝ TRẠNG THÁI (STATE MANAGEMENT RULES)

Mọi tính năng, nhiệm vụ và lỗi phải được phân loại chính xác theo 6 trạng thái:
- `PLANNED`: Đã lên kế hoạch trong Roadmap/Backlog, chưa viết code.
- `IN_PROGRESS`: Đang viết mã nguồn trong phiên làm việc hiện tại.
- `BLOCKED`: Đang bị tắc nghẽn do thiếu phụ thuộc hoặc chờ phê duyệt.
- `IMPLEMENTED`: Đã viết code nhưng **chưa chạy test kiểm chứng**.
- `VERIFIED`: Đã chạy test thực tế thành công và có bằng chứng (test log, assertions).
- `DEPRECATED`: Mã nguồn hoặc tài liệu cũ đã được thay thế.

> [!CAUTION]
> **Tuyệt đối không được đánh dấu `VERIFIED` nếu chưa chạy test thực tế trong phiên làm việc!**
