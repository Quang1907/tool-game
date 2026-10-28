# CHANGELOG — BINH 13 ANALYZER (macOS)

Tất cả các thay đổi đáng chú ý của dự án được ghi chép tại đây theo định dạng [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.3.0] — 2026-10-28

### Added

- **Tính năng Suy Luận 13 Lá Bài Đối Thủ (Nhà Thứ 4) & Chiến Lược Tập Thể Khắc Chế Triệt Hạ:**
  - **Module phân tích tập thể ([collaborative_analyzer.py](file:///Users/levanquang/tool/app/core/collaborative_analyzer.py)):**
    - Loại trừ 39 lá bài từ 3 cửa sổ khỏi bộ bài chuẩn 52 cây ($52 - 39 = 13$) để khóa chặt chính xác 100% 13 lá bài của nhà đối thủ còn lại.
    - Tự động dùng `Solver` giải ra thế bài 3 chi mạnh nhất mà đối thủ có thể xếp.
    - Chạy thuật toán đối đầu trực tiếp (`compare_head_to_head`) giữa tất cả các thế bài hợp lệ của từng cửa sổ người chơi với bài đối thủ, tự động tối ưu hóa để **Bắt sập 3 chi (+6 điểm)** hoặc thắng tối đa số chi trước đối thủ.
  - **Bảng điều khiển đối thủ `OpponentDeductionPanel` ([multi_window_widget.py](file:///Users/levanquang/tool/app/ui/components/multi_window_widget.py)):**
    - Hiển thị thanh trạng thái khóa chặt đối thủ và tổng điểm 3 nhà vs đối thủ.
    - Hiển thị 13 quân bài thumbnail của đối thủ.
    - Hiển thị thế bài 3 chi đối thủ sẽ xếp (Chi Đầu, Chi Giữa, Chi Cuối).
  - **Huy hiệu kết quả đối đầu trên từng cửa sổ:**
    - Hiển thị dự đoán đối đầu: `🏆 BẮT SẬP 3 CHI (+6 điểm)` (xanh lá), `✓ Thắng (+X điểm)` (xanh dương), cùng kết quả chi tiết từng chi (Đầu, Giữa, Cuối).
    - Tự động chuyển thế bài gợi ý sang thế bài khắc chế tối ưu.
  - **Bộ kiểm thử toàn diện:**
    - Thêm suite unit test độc lập `tests/test_collaborative_analyzer.py` (4 tests).
    - Thêm test tích hợp giao diện `test_multi_window_deduces_opponent_and_optimizes_counter_strategy` trong `tests/test_multi_window.py`.
    - Nâng tổng số bài test toàn dự án đạt **124/124 PASSED (100%)**.

---

## [1.2.3] — 2026-10-28

### Fixed

- **Khắc phục lỗi Tab 6 ("Bot 3 Cửa Sổ") không lấy được hình ảnh từ cửa sổ, báo che khuất (Occluded), không nhận diện bài và không gợi ý xếp bài:**
  - **Chụp ảnh trực tiếp theo CGWindowID ([screen_capture.py](file:///Users/levanquang/tool/app/vision/screen_capture.py)):** Tích hợp lệnh `screencapture -l <window_id> -o -x` để lấy trực tiếp frame hình ảnh của chính xác cửa sổ game từ macOS WindowServer, bất kể cửa sổ app Binh 13 Analyzer hay các cửa sổ khác có đang đè lên trên hay không.
  - **Sửa lỗi lệch Window ID và tính toán Occlusion ([multi_window_widget.py](file:///Users/levanquang/tool/app/ui/components/multi_window_widget.py), [window_manager.py](file:///Users/levanquang/tool/app/vision/window_manager.py)):** Trước đây slot UI truyền số thứ tự 1, 2, 3 làm `window_id`, khiến thuật toán `compute_occlusion` không tìm thấy và gán nhầm tỷ lệ che khuất 100%. Đã bổ sung trường `cg_window_id` vào `WindowROI` và kết nối trực tiếp với macOS CGWindowID. Loại trừ cửa sổ ứng dụng Binh 13 Analyzer khỏi danh sách các cửa sổ che khuất.
  - **Xác nhận tức thì khi chọn cửa sổ trong dropdown:** Thêm callback `_on_window_selected` cho sự kiện `combo_w1/w2/w3.currentIndexChanged`. Ngay khi người dùng chọn cửa sổ, app chụp ảnh tức thì, nạp vào viewer để người dùng xác nhận đúng cửa sổ, tự động chạy card detection để hiển thị thumbnail lá bài phát hiện và tính toán gợi ý xếp bài tối ưu (Chi Đầu, Chi Giữa, Chi Cuối).
  - **Không chặn quét khi cửa sổ bị che một phần ([multi_window_service.py](file:///Users/levanquang/tool/app/services/multi_window_service.py)):** Tiếp tục phát hiện và nhận diện bài nếu frame ảnh hợp lệ.
  - **Cập nhật bộ lọc cửa sổ Swift ([macos_window_helper.swift](file:///Users/levanquang/tool/scripts/macos_window_helper.swift)):** Bỏ flag `optionOnScreenOnly` để nhận diện các cửa sổ game nằm phía dưới, đồng thời loại trừ chính cửa sổ Binh 13 Analyzer.
  - **Khắc phục lỗi crash `AttributeError: 'Solver' object has no attribute 'solve_heuristic'` ([solver.py](file:///Users/levanquang/tool/app/core/solver.py)):** Bổ sung phương thức `solve_heuristic` ủy quyền cho `solve()`, đồng thời thêm bọc an toàn `try...except` khi gọi bộ giải trong [multi_window_widget.py](file:///Users/levanquang/tool/app/ui/components/multi_window_widget.py) và [multi_window_service.py](file:///Users/levanquang/tool/app/services/multi_window_service.py).
  - **Triệt tiêu cảnh báo font Qt `SF Pro Text` ([styles.py](file:///Users/levanquang/tool/app/ui/styles.py), [card_widget.py](file:///Users/levanquang/tool/app/ui/components/card_widget.py)):** Thay thế `SF Pro Text` bằng native macOS font `.AppleSystemUIFont`, loại bỏ hoàn toàn cảnh báo font và tăng tốc độ khởi tạo giao diện.
  - **Bổ sung kiểm thử và cấu hình session fixture:** Thêm test xác minh tích hợp giải bài 13 lá trong `tests/test_multi_window.py` và tạo `tests/conftest.py`, nâng tổng số test suite đạt **119/119 PASSED (100%)**.

---

## [1.2.2] — 2026-10-27

### Fixed

- **Khắc phục triệt để lỗi toàn bộ các lá bài đen (10♠, 5♠, 4♣, 8♣, A♠) bị gán nhầm thành chất Rô (♦) và báo bài trùng:**
  - **Sửa phân biệt màu đỏ/đen trong [card_reference_library.py](file:///Users/levanquang/tool/app/vision/card_reference_library.py):** Ngưỡng pixel HSV cũ (> 15 px) bị nhiễu do viền khử răng cưa và đổ bóng xám đen, khiến các lá bài đen bị coi là màu đỏ và loại trừ hoàn toàn Bích/Tép trong quá trình match. Hệ thống đã chuyển sang thuật toán đo chênh lệch màu đỏ rực rỡ ($R > 90, R - \max(G, B) > 25, S > 50$) và kiểm tra tương quan với pixel đen tối ($R_{\text{red}} > 0.35 \times B_{\text{black}}$). Đồng thời tự động thu hẹp vùng kiểm tra vào góc index nếu nhận vào ảnh toàn lá để tránh áo đỏ của các quân Tây (J, Q, K).
  - **Khắc phục lỗi cắt xén tách rời 2 chữ số của quân 10 ('1' và '0'):** Thuật toán trích xuất góc động gom nhóm cả 2 chữ số '1' và '0' ở nửa trên thành một vùng rank duy nhất, ngăn việc chữ số '0' bị gán làm rank và chữ số '1' bị gán nhầm làm suit (làm biến mất biểu tượng Bích ♠).
  - **Tối ưu hóa nhận diện rank 10 trong [template_engine.py](file:///Users/levanquang/tool/app/vision/template_engine.py):** Thêm mẫu template số 10 liền khối và cơ chế nhận diện topo 2 ký tự số song song, match đạt độ tin cậy tuyệt đối và không còn bị nhầm sang rank 8.
  - **Sửa bản ghi SQLite `data.db`:** Cập nhật bản ghi `8c5524b6-079f-470b-9a9c-d734316d84ac` (ảnh 5♠ nhưng trước đó bị lưu sai thành 5D) về đúng mã `5S`.
  - **Thêm suite kiểm thử hồi quy `TestBlackCardsColorIntegrityAndRank10Segmentation`:** 116/116 tests toàn dự án đạt 100% PASSED.

---

## [1.2.1] — 2026-10-27

### Fixed

- **Khắc phục triệt để lỗi nhận diện 6 Cơ (6♥) thành 5 Cơ (5♥):**
  - **Phân tích hình học & topo chữ số (Topological Hole Analysis) trong `template_engine.py`:** Sử dụng `cv2.RETR_CCOMP` phát hiện lỗ khép kín. Ký tự '6' bắt buộc có lỗ khép kín ở nửa dưới ($y \ge 0.40$), trong khi '5' không có lỗ khép kín. Áp dụng cơ chế phạt điểm nặng đối với các ứng viên không khớp cấu trúc topo lỗ, và căn giữa glyph trong bounding box 28x36.
  - **Chấm dứt ghi đè nhãn ngầm (Silent Auto-Healing) trong `card_reference_library.py`:** Loại bỏ hoàn toàn khối lệnh tự ý `UPDATE card_references` trong `_add_to_cache`. Nhãn do người dùng xác nhận luôn là chân lý tối cao.
  - **Sửa dữ liệu mẫu bị nhiễm độc trong SQLite (`data.db`):** Di chuyển bản ghi ID `1499111f-9cce-46f2-83a5-3cf6e4dce15c` từ `5H` sang `6H` và cập nhật lại đường dẫn ảnh file mẫu chuẩn.
  - **Thêm hộp thoại `CardContradictionDialog` trong `card_edit_dialog.py`:** Cảnh báo trực quan nếu có sự mâu thuẫn lớn giữa nhãn người dùng chọn và kết quả nhận diện, bảo vệ người dùng không vô tình lưu đè mẫu sai.
  - **Bổ sung 9 bài kiểm thử hồi quy `TestSavedCardReferenceLabelMismatchRegression`:** 113/113 tests toàn dự án đều vượt qua.

---

## [1.2.0] — 2026-10-26

### Added

- **AI Master Engineer System:**
  - Thiết lập thư mục `.ai/` quản lý toàn diện tri thức, kiến trúc, trạng thái, quy tắc và lộ trình phát triển.
  - Tạo `MASTER_CONTEXT.md` đóng vai trò bản đồ điều hướng cho mọi phiên AI tương lai.
  - Tạo `GEMINI.md` định hướng cho Gemini Agent.
  - Cập nhật `AGENTS.md` tương thích với cơ chế phân vai kỹ thuật.
  - Tạo các tài liệu quản lý trạng thái: `CURRENT_STATE.md`, `ACTIVE_TASK.md`, `NEXT_ACTIONS.md`, `KNOWN_ISSUES.md`, `TEST_STATUS.md`.
  - Tạo tài liệu quy trình: `SESSION_WORKFLOW.md`, `CHANGE_APPROVAL_POLICY.md`.
  - Tạo tài liệu chi tiết từng phân hệ: `CORE_DOMAIN.md`, `VISION_PIPELINE.md`, `UI_PRESENTATION.md`, `DATABASE_PERSISTENCE.md`, `SERVICES_ORCHESTRATION.md`.

---

## [1.1.2] — 2026-10-26

### Fixed

- **Khắc phục lỗi False Positive Avatar người chơi bị nhận diện thành `K♦ 50% UNCERTAIN`:**
  - Thêm Candidate Validation trong `CardDetector.validate_crop()`: Loại bỏ các contour avatar hình tròn (độ tròn $> 0.65$), khối vuông $0.82 \le w/h \le 1.28$ có độ trắng $< 50\%$, và nút bấm UI có độ bão hòa màu cao.
  - Cập nhật `CardRecognizer.recognize_crop()`: Trả về `card=None, confidence=0.0` ngay khi phát hiện `NON_CARD_OBJECT` hoặc góc bài thiếu nền trắng ($< 35\%$), không đoán mò.
- **Khắc phục lỗi 13 nút Rank trong dialog bị trống (khối xanh không chữ):**
  - Khắc phục xung đột CSS: Nút Rank kích thước $36 \times 30\text{ px}$ được ghi đè inline `padding: 0; font-size: 12px; font-weight: 600; color: #FFFFFF` để tránh bị padding toàn cục $16\text{px}$ đẩy mất chữ.
  - Sắp xếp 13 nút Rank đúng thứ tự: `A, 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K`.
  - Đảm bảo tính độc lập: Chọn Rank giữ nguyên Suit hiện tại; chọn Suit giữ nguyên Rank hiện tại.
- **Đồng bộ tọa độ crop:**
  - Trích xuất `raw_patch` từ frame gốc của bàn chơi; gán `raw_crop=source_crop` trong `DetectedCard`.
  - Cập nhật `VisionDebugDialog` hiển thị tọa độ Bbox ảnh gốc, kích thước crop, kích thước Rank/Suit crop và trạng thái validation.
- **An toàn thư viện mẫu:**
  - Chặn tuyệt đối việc lưu ảnh avatar / non-card vào `CardReferenceLibrary`.

### Added

- Bổ sung `TestMandatoryVerificationTestSuite` trong `tests/test_card_detection_and_reference.py` kiểm chứng Test A (Avatar), Test B (Nút Rank), Test C (Nút Suit), Test D (Tọa độ crop), Test E (An toàn xác nhận mẫu).

---

## [1.1.1] — 2026-10-25

### Added

- Tách biệt nhận diện Rank và Suit độc lập (`extract_dynamic_corner_patches` qua Connected Components).
- Xây dựng Thư viện ảnh mẫu đã xác nhận (`CardReferenceLibrary`) lưu trong SQLite.
- Thêm `CardEditDialog` cho phép người dùng xác nhận và sửa bài trực quan.
- Thêm `VisionDebugDialog` với 4 tab chẩn đoán chuyên sâu.
- Thêm `ZoomableImageViewer` hỗ trợ zoom, pan và click vào bounding box bài.

---

## [1.1.0] — 2026-10-25

### Added

- Hỗ trợ giám sát 3 cửa sổ bàn chơi game đồng thời trên một màn hình MacBook.
- Cơ chế 1-frame chụp chung, crop 3 ROI độc lập qua `ROIManager`.
- Bộ theo dõi quân bài `CardTracker` bất biến vị trí (`position_invariant_hash`), không tính lại solver khi bài chỉ di chuyển.

---

## [1.0.0] — 2026-10-25

### Added

- Khởi tạo kiến trúc Clean Architecture 5 tầng.
- Mô hình hóa bài (`card.py`), bộ đánh giá (`evaluator.py`), luật tính điểm (`rules.py`).
- Thuật toán phân rã tổ hợp 36,036 thế bài (`solver.py`).
- Bộ mô phỏng Monte Carlo tối ưu EV với Common Random Numbers (`simulator.py`, `ev_optimizer.py`).
- Giao diện PySide6 Dark Theme Apple HIG (`app/ui/main_window.py`).
- Lưu trữ phiên chơi vào SQLite cục bộ (`app/database/`).
