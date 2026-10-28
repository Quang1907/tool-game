# TEST STATUS & VERIFICATION REPORT — BINH 13 ANALYZER

**Thời điểm kiểm tra gần nhất:** 2026-10-29 07:57:44 +09:00  
**Lệnh thực thi:** `.venv/bin/pytest tests/`  
**Kết quả chung:** **128 / 128 tests PASSED (100%)**  
**Thời gian chạy:** 24.86 giây  
**Nền tảng:** macOS Sequoia 15.4.1 (ARM64 Apple Silicon) | Python 3.11.17

---

## 1. BẢNG PHÂN BỔ KẾT QUẢ THEO FILE TEST

| File Test | Số test | Kết quả | Trọng tâm kiểm thử |
|---|:---:|:---:|---|
| `tests/test_card.py` | 10 | **10 PASSED** | Giá trị Card, Rank, Suit, Deck xáo bài, Hand parsing chuỗi |
| `tests/test_evaluator.py` | 14 | **14 PASSED** | Đánh giá Chi Đầu (3 lá), Chi Giữa/Cuối (5 lá), kiểm tra Foul |
| `tests/test_rules.py` | 5 | **5 PASSED** | Tính điểm đối đầu, bắt sập 1 người, sập làng, phạt lủng, sảnh rồng |
| `tests/test_solver.py` | 4 | **4 PASSED** | Khảo sát 36,036 thế bài, bảo toàn 13 quân bài, loại bài lủng |
| `tests/test_collaborative_analyzer.py` | 4 | **4 PASSED** | Suy luận 13 lá đối thủ, giải thế bài đối thủ, tối ưu phản công |
| `tests/test_simulator.py` | 4 | **4 PASSED** | Mô phỏng Monte Carlo, CRN tính EV, xếp hạng thế bài |
| `tests/test_database.py` | 1 | **1 PASSED** | Vòng đời Session SQLite, CRUD lịch sử ván bài |
| `tests/test_integration.py` | 1 | **1 PASSED** | Luồng tích hợp End-to-End từ bài nạp đến giải và mô phỏng |
| `tests/test_multi_window.py` | 9 | **9 PASSED** | 3 cửa sổ bàn chơi, direct capture, suy luận đối thủ, shared pipeline |
| `tests/test_ui.py` | 7 | **7 PASSED** | MainWindow, CardEditDialog, CardReferenceManager, ZoomableImageViewer |
| `tests/test_vision.py` | 28 | **28 PASSED** | Xử lý ảnh, template matching, NMS, tách bài xòe, 9 mẫu bài thực tế |
| `tests/test_card_detection_and_reference.py` | 40 | **40 PASSED** | Bộ test bắt buộc (A-E), hồi quy 6♥/5♥, màu Đen/Đỏ & Rank 10, cô lập Suit Pip J/Q/K, chống ghosting 2♠ |

---

## 2. BẰNG CHỨNG XÁC MINH TEST MỚI (FACE CARDS & GHOST WIDGET FIX)

Trong file `tests/test_card_detection_and_reference.py` (`TestFaceCardsRecognitionAndGhostWidgetFix`):

- **Test F1 (`test_face_card_suit_isolation_not_contaminated_by_portrait`):**  
  Tạo quân bài Tây có hình ảnh chân dung hoàng gia lớn màu đỏ/vàng thêu kim tuyến $\rightarrow$ `extract_dynamic_corner_patches` cô lập chính xác suit pip góc chuẩn ($w \le 36$), không bị bắt nhầm vào họa tiết áo của chân dung. `check_image_is_red(suit_crop)` trả về `False`.
- **Test F2 (`test_black_court_card_never_evaluated_as_red_even_with_portrait`):**  
  Nạp ảnh bài Tây đen (Q♠) với chân dung có viền áo đỏ $\rightarrow$ Hệ thống dự đoán đúng 100% là Q♠, tuyệt đối không bị ép sang Q♦ hoặc QH do nhiễm màu chân dung.
- **Test F3 (`test_card_reference_manager_dialog_clearing_unparents_widgets`):**  
  Trong `CardReferenceManagerDialog`, chuyển đổi từ lá bài 2♠ sang J♦ $\rightarrow$ Tất cả các widget của 2♠ trước đó được unparent (`parent() is None`) và ẩn hoàn toàn (`isHidden() is True`), triệt tiêu 100% hiện tượng quân bài 2♠ hiển thị đè lên các ô khác.
