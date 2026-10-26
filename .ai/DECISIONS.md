# ARCHITECTURAL DECISION RECORDS (ADR) — BINH 13 ANALYZER

Tài liệu này ghi lại toàn bộ các quyết định kiến trúc, bối cảnh, lựa chọn kỹ thuật và trạng thái phê duyệt.

Trạng thái:
- `APPROVED`: Đã được phê duyệt và triển khai thực tế.
- `PROPOSED`: Đang đề xuất, chờ người dùng phê duyệt trước khi thực hiện.
- `REJECTED`: Đã xem xét nhưng bị từ chối.
- `SUPERSEDED`: Đã bị thay thế bởi quyết định mới hơn.

---

## ADR 1: Python Runtime & Apple Silicon Target
- **Trạng thái:** `APPROVED`
- **Bối cảnh:** macOS Sequoia 15.4.1 chạy trên chip Apple Silicon ARM64. Python mặc định của hệ thống là 3.9.6 (giới hạn về type hints và hiệu năng).
- **Quyết định:** Chuẩn hóa trên **Python 3.11.17** cài đặt qua Homebrew với môi trường ảo cách ly (`.venv/`).
- **Hệ quả:** Tối ưu hóa hiệu năng biên dịch ARM64 cho PySide6, OpenCV, NumPy trên Apple Silicon.

---

## ADR 2: PySide6 (Qt for Python) cho Ứng Dụng Desktop
- **Trạng thái:** `APPROVED`
- **Bối cảnh:** Cần giao diện người dùng desktop native, tốc độ phản hồi tức thì, hỗ trợ màn hình Retina và luồng nền.
- **Quyết định:** Sử dụng **PySide6 (Qt 6.8+)**.
- **Hệ quả:** Hỗ trợ HighDPI native, kiến trúc Signals/Slots và `QThread` đảm bảo Zero UI lag; giao diện chuẩn Apple HIG.

---

## ADR 3: Domain Core Thuần Túy Không Phụ Thuộc GUI hay Database
- **Trạng thái:** `APPROVED`
- **Bối cảnh:** Độ phức tạp tổ hợp cao ($36,036$ thế bài) và mô phỏng Monte Carlo ($10,000+$ ván).
- **Quyết định:** `app/core/` có **ZERO dependencies** đối với GUI, thị giác máy tính hay SQLite.
- **Hệ quả:** Tốc độ tính toán tối đa, kiểm thử headless tức thì, không rò rỉ bộ nhớ.

---

## ADR 4: Thuật Toán Phân Rã Tổ Hợp 36,036 Thế Bài
- **Trạng thái:** `APPROVED`
- **Bối cảnh:** Cần duyệt toàn bộ cách chia 13 lá thành 3 chi (3, 5, 5).
- **Quyết định:** Chọn 3 lá cho Chi Đầu $\binom{13}{3} = 286$, sau đó chọn 5 lá từ 10 lá còn lại cho Chi Giữa $\binom{10}{5} = 252$. Triệt tiêu tính đối xứng giữa Chi Giữa và Chi Cuối: $\frac{286 \times 252}{2} = 36,036$ cách chia độc nhất.
- **Hệ quả:** Giảm không gian tìm kiếm xuống đúng 36,036 thế bài tất định.

---

## ADR 5: Kỹ Thuật Common Random Numbers (CRN) Trong Mô Phỏng Monte Carlo
- **Trạng thái:** `APPROVED`
- **Bối cảnh:** So sánh nhiều thế bài ứng viên trong điều kiện phương sai ngẫu nhiên cao.
- **Quyết định:** Mọi thế bài ứng viên trong một lượt mô phỏng đều đối đầu với **cùng một chuỗi phân bài đối thủ ngẫu nhiên**.
- **Hệ quả:** Triệt tiêu phương sai ngoại cảnh, xếp hạng chính xác với số lượng vòng lặp ít hơn.

---

## ADR 6: Thị Giác Máy Tính Không Xâm Phạm (Non-Invasive Vision)
- **Trạng thái:** `APPROVED`
- **Bối cảnh:** Nhận diện bài mà không vi phạm quy định an toàn hay can thiệp trò chơi.
- **Quyết định:** Chỉ chụp màn hình qua macOS OS APIs (`screencapture` hoặc Qt QScreen). Không đọc RAM, không sửa bộ nhớ game, không bắt gói tin mạng.
- **Hệ quả:** An toàn tuyệt đối, không bị phần mềm bảo mật cảnh báo.

---

## ADR 7: Tách Bài Xòe Qua Dải Biên An Toàn (Margin Strips Gradient)
- **Trạng thái:** `APPROVED`
- **Bối cảnh:** Bài trong game thường xòe hình quạt, chồng lấp lên nhau; hình vẽ tướng J, Q, K ở giữa thân bài tạo ra các đỉnh cạnh giả gây chia cắt sai.
- **Quyết định:** Chỉ phân tích biên gradient trên dải biên $16\%$ trên và $16\%$ dưới thân bài (vùng không chứa hình vẽ tướng).
- **Hệ quả:** Tách chính xác từng lá bài xòe mà không bị nhầm lẫn bởi hình vẽ bên trong lá bài.

---

## ADR 8: Nhận Diện Độc Lập Rank & Suit Kèm Thư Viện Ảnh Mẫu Tự Học
- **Trạng thái:** `APPROVED`
- **Bối cảnh:** Nhận diện cả lá bài thường bị nhầm lẫn giữa các lá cùng chất (ví dụ $9♦$ và $Q♦$).
- **Quyết định:** Phân tách hoàn toàn nhận diện Rank và nhận diện Suit thành hai luồng độc lập. Cho phép lưu ảnh mẫu đã xác nhận của người dùng vào SQLite để đối chiếu trong tương lai.
- **Hệ quả:** Loại bỏ hoàn toàn lỗi dùng mẫu $9♦$ để suy diễn $Q♦$.

---

## ADR 9: Kiến Trúc 1-Frame Chụp Chung, 3-ROI Cho Multi-Window
- **Trạng thái:** `APPROVED`
- **Bối cảnh:** Giám sát đồng thời 3 cửa sổ game trên một màn hình MacBook mà không gây quá tải CPU.
- **Quyết định:** Chụp một frame màn hình chung duy nhất rồi crop 3 ROI. Dùng mã băm `position_invariant_hash` để không tính lại khi bài chỉ di chuyển vị trí.
- **Hệ quả:** Tiết kiệm CPU, nhận diện tức thì trên cả 3 bàn chơi.

---

## ADR 10: Candidate Validation Chặt Chẽ Loại Bỏ Avatar & Nút Bấm
- **Trạng thái:** `APPROVED`
- **Bối cảnh:** Detector bắt nhầm avatar người chơi hình vuông/tròn và nhận diện thành `K♦ 50% UNCERTAIN`.
- **Quyết định:** Bổ sung bước kiểm tra hình học (độ tròn $> 0.65$, khối vuông $0.82 \le w/h \le 1.28$ có độ trắng $< 50\%$, độ bão hòa màu cao). Bắt buộc `CardRecognizer` trả về `card=None, confidence=0.0` nếu đối tượng không phải là bài.
- **Hệ quả:** Chấm dứt hoàn toàn false positive avatar người chơi.

---

## ADR 11: Thay Thế Font "SF Pro Text" Bằng System Font
- **Trạng thái:** `PROPOSED`
- **Bối cảnh:** Qt QPA font engine in cảnh báo mất 68ms khi nạp font `"SF Pro Text"` trên macOS.
- **Đề xuất:** Thay thế bằng `".AppleSystemUIFont"` trong `app/ui/styles.py`.
- **Hệ quả dự kiến:** Khởi động nhanh hơn 68ms, không còn log cảnh báo font trong console.
