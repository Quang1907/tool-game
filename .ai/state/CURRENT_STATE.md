# CURRENT STATE — BINH 13 ANALYZER (macOS)

**Cập nhật lần cuối:** 2026-10-27  
**Trạng thái kiểm thử:** 116/116 tests PASSED (100%)  
**Môi trường thực thi:** Python 3.11.17 (`.venv`), macOS Sequoia 15.4.1 (ARM64 Apple Silicon)

---

## 1. BẢNG TRẠNG THÁI CÁC PHÂN HỆ

| Phân hệ             | Thành phần                                                | Trạng thái | Bằng chứng xác minh                                    |
| ------------------- | --------------------------------------------------------- | :--------: | ------------------------------------------------------ |
| **Domain Core**     | `card.py` (Rank, Suit, Card, Deck, Hand)                  | `VERIFIED` | `test_card.py` (10 tests passed)                       |
| **Domain Core**     | `evaluator.py` (3-card, 5-card, Foul detection)           | `VERIFIED` | `test_evaluator.py` (14 tests passed)                  |
| **Domain Core**     | `rules.py` (Scoring, Scoop, Penalties, Special hands)     | `VERIFIED` | `test_rules.py` (5 tests passed)                       |
| **Domain Core**     | `solver.py` (36,036 partitions, pruning)                  | `VERIFIED` | `test_solver.py` (4 tests passed, toán học chứng minh) |
| **Domain Core**     | `simulator.py` & `ev_optimizer.py` (Monte Carlo CRN)      | `VERIFIED` | `test_simulator.py` (4 tests passed)                   |
| **Vision Pipeline** | `screen_capture.py` (macOS Retina 2x)                     | `VERIFIED` | `test_vision.py` & `test_multi_window.py` passed       |
| **Vision Pipeline** | `image_preprocessor.py` (Warp 120x168, green border)      | `VERIFIED` | `test_vision.py` passed                                |
| **Vision Pipeline** | `card_detector.py` (Candidate validation, NMS, Fanned)    | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `card_recognizer.py` (Decoupled Rank/Suit matching)       | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `template_engine.py` (Topological loop & Rank analysis)  | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `card_reference_library.py` (SQLite Ground-truth)         | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **Vision Pipeline** | `roi_manager.py` & `window_manager.py` (3 Windows)        | `VERIFIED` | `test_multi_window.py` (5 tests passed)                |
| **Database**        | `db.py` & `repository.py` (Sessions, References CRUD)     | `VERIFIED` | `test_database.py` (1 test passed)                     |
| **Services**        | `analysis_service.py` & `simulation_service.py`           | `VERIFIED` | `test_integration.py` passed                           |
| **Services**        | `multi_window_service.py` (Tracking & Hash cache)         | `VERIFIED` | `test_multi_window.py` passed                          |
| **UI Layer**        | `main_window.py` (5 main tabs)                            | `VERIFIED` | `test_ui.py` passed, khởi chạy app thành công          |
| **UI Layer**        | `card_edit_dialog.py` (13 nút Rank, 4 Suit, Contradiction)| `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **UI Layer**        | `vision_debug_dialog.py` (4 tab chẩn đoán)                | `VERIFIED` | `test_card_detection_and_reference.py` passed          |
| **UI Layer**        | `zoomable_viewer.py` (Zoom, Pan, Click Bbox)              | `VERIFIED` | `test_ui.py` passed                                    |
| **UI Layer**        | `card_reference_manager.py` (Quản lý 52 lá)               | `VERIFIED` | `test_ui.py` passed                                    |

---

## 2. NHỮNG GÌ VỪA ĐƯỢC SỬA VÀ HOÀN TẤT GẦN NHẤT

1. **Khắc phục triệt để lỗi các lá bài đen (10♠, 5♠, 4♣, 8♣, A♠) bị nhận nhầm thành chất Rô (♦) và báo bài trùng:**
   - **Sửa hàm phân biệt màu đỏ/đen `check_image_is_red` trong `card_reference_library.py`:** Thuật toán cũ đếm pixel HSV với ngưỡng cực thấp (> 15 px) khiến các vùng viền khử răng cưa/bóng mờ xám đậm trên lá bài đen bị nhận nhầm là màu đỏ. Hệ thống chuyển sang đo lường màu đỏ rực rỡ ($R > 90, R - \max(G, B) > 25, S > 50$) và so sánh tương quan với pixel đen/tối ($R_{\text{red}} > 0.35 \times B_{\text{black}}$). Đồng thời tự động thu hẹp phạm vi kiểm tra vào góc index nếu nhận vào ảnh toàn lá để tránh ảnh minh họa áo đỏ của các quân Tây (J, Q, K).
   - **Xử lý số 10 hai chữ số ('1' và '0') trong `card_reference_library.py`:** Phân đoạn dynamic corner patch gom nhóm cả 2 thành phần số '1' và '0' ở nửa trên thành một vùng rank thống nhất, không còn cắt nhầm số '0' làm rank và số '1' làm suit khiến chất Bích bị mất.
   - **Cải tiến `CardTemplateEngine` cho quân 10:** Thêm template số 10 thu nhỏ liền khối và thuật toán nhận diện topo 2 ký tự số song song, match chính xác 100% không còn bị dự đoán nhầm thành rank 8.
   - **Sửa bản ghi nhiễm độc trong SQLite `data.db`:** Bản ghi `8c5524b6-079f-470b-9a9c-d734316d84ac` có ảnh thực tế là 5♠ nhưng bị lưu nhãn sai thành `5D` đã được cập nhật thành `5S` chuẩn xác.
   - **Bổ sung `TestBlackCardsColorIntegrityAndRank10Segmentation`:** 3 bài test xác minh độc lập, nâng toàn bộ test suite dự án lên 116/116 PASSED (100%).
