# CURRENT STATE — BINH 13 ANALYZER (macOS)

**Cập nhật lần cuối:** 2026-10-26  
**Git Head:** `b2d2358` (branch: `main`)  
**Trạng thái kiểm thử:** 104/104 tests PASSED (100%)  
**Môi trường thực thi:** Python 3.11.17 (`.venv`), macOS Sequoia 15.4.1 (ARM64 Apple Silicon)

---

## 1. BẢNG TRẠNG THÁI CÁC PHÂN HỆ

| Phân hệ | Thành phần | Trạng thái | Bằng chứng xác minh |
|---|---|:---:|---|
| **Domain Core** | `card.py` (Rank, Suit, Card, Deck, Hand) | `VERIFIED` | `test_card.py` (10 tests passed) |
| **Domain Core** | `evaluator.py` (3-card, 5-card, Foul detection) | `VERIFIED` | `test_evaluator.py` (14 tests passed) |
| **Domain Core** | `rules.py` (Scoring, Scoop, Penalties, Special hands) | `VERIFIED` | `test_rules.py` (5 tests passed) |
| **Domain Core** | `solver.py` (36,036 partitions, pruning) | `VERIFIED` | `test_solver.py` (4 tests passed, toán học chứng minh) |
| **Domain Core** | `simulator.py` & `ev_optimizer.py` (Monte Carlo CRN) | `VERIFIED` | `test_simulator.py` (4 tests passed) |
| **Vision Pipeline** | `screen_capture.py` (macOS Retina 2x) | `VERIFIED` | `test_vision.py` & `test_multi_window.py` passed |
| **Vision Pipeline** | `image_preprocessor.py` (Warp 120x168, green border) | `VERIFIED` | `test_vision.py` passed |
| **Vision Pipeline** | `card_detector.py` (Candidate validation, NMS, Fanned) | `VERIFIED` | `test_card_detection_and_reference.py` passed |
| **Vision Pipeline** | `card_recognizer.py` (Decoupled Rank/Suit matching) | `VERIFIED` | `test_card_detection_and_reference.py` passed |
| **Vision Pipeline** | `card_reference_library.py` (SQLite Ground-truth) | `VERIFIED` | `test_card_detection_and_reference.py` passed |
| **Vision Pipeline** | `roi_manager.py` & `window_manager.py` (3 Windows) | `VERIFIED` | `test_multi_window.py` (5 tests passed) |
| **Database** | `db.py` & `repository.py` (Sessions, References CRUD) | `VERIFIED` | `test_database.py` (1 test passed) |
| **Services** | `analysis_service.py` & `simulation_service.py` | `VERIFIED` | `test_integration.py` passed |
| **Services** | `multi_window_service.py` (Tracking & Hash cache) | `VERIFIED` | `test_multi_window.py` passed |
| **UI Layer** | `main_window.py` (5 main tabs) | `VERIFIED` | `test_ui.py` passed, khởi chạy app thành công |
| **UI Layer** | `card_edit_dialog.py` (13 nút Rank, 4 nút Suit, Save ref) | `VERIFIED` | `test_card_detection_and_reference.py` passed |
| **UI Layer** | `vision_debug_dialog.py` (4 tab chẩn đoán) | `VERIFIED` | `test_card_detection_and_reference.py` passed |
| **UI Layer** | `zoomable_viewer.py` (Zoom, Pan, Click Bbox) | `VERIFIED` | `test_ui.py` passed |
| **UI Layer** | `card_reference_manager.py` (Quản lý 52 lá) | `VERIFIED` | `test_ui.py` passed |

---

## 2. NHỮNG GÌ VỪA ĐƯỢC SỬA VÀ HOÀN TẤT GẦN NHẤT

1. **Khắc phục False Positive nhận diện Avatar thành `K♦ 50%`:**
   - Đã thêm Candidate Validation vào `CardDetector.validate_crop()` loại bỏ avatar hình tròn/vuông $0.82 \le w/h \le 1.28$ có độ trắng $< 50\%$.
   - `CardRecognizer` trả về ngay `card=None, confidence=0.0, crop_status='NON_CARD_OBJECT'` khi crop là avatar, không đoán mò sang `K♦`.
2. **Khắc phục 13 nút Rank trong dialog bị trống (khối xanh):**
   - Đã gán kích thước `36x30 px` và override inline `padding: 0; font-size: 12px; font-weight: 600; color: #FFFFFF` ghi đè CSS toàn cục.
   - 13 nút Rank hiển thị đầy đủ `A, 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K`.
   - Chọn Rank bảo toàn Suit hiện tại; chọn Suit bảo toàn Rank hiện tại.
3. **Đồng bộ tọa độ crop ảnh gốc:**
   - Trích xuất `raw_patch` từ ảnh gốc, `DetectedCard.raw_crop` phản ánh chính xác vùng pixel frame gốc.
4. **Bảo vệ an toàn thư viện mẫu:**
   - Chặn tuyệt đối việc lưu ảnh avatar / non-card vào thư viện mẫu.
