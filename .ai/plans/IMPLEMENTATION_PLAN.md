# IMPLEMENTATION PLAN — BINH 13 ANALYZER (macOS)

Tài liệu này theo dõi lộ trình kỹ thuật chi tiết theo các Phase thực tế của dự án.

---

## 1. TIẾN ĐỘ THỰC HIỆN CÁC PHÂN ĐOẠN (PHASES)

### Phase 0: Audit Môi Trường & Thiết Lập Dự Án (`VERIFIED`)
- [x] macOS Sequoia 15.4.1 ARM64 (Apple Silicon).
- [x] Python 3.11.17 via Homebrew; Virtualenv `.venv/`.
- [x] Tài liệu kiến trúc và hướng dẫn cài đặt.

### Phase 1: Nền Tảng Dự Án & Scripts Tự Động (`VERIFIED`)
- [x] `pyproject.toml`, `requirements.txt`, `.gitignore`.
- [x] Scripts: `setup_macos.sh`, `run_macos.sh`, `test.sh`, `build_macos.sh`.
- [x] Cấu hình HighDPI Retina `app/main.py`.

### Phase 2: Domain Core — Quân Bài & Tay Bài (`VERIFIED`)
- [x] `app/core/card.py`: `Rank`, `Suit`, `Card`, `Deck`, `Hand`.
- [x] `tests/test_card.py` (10/10 tests passed).

### Phase 3: Domain Core — Bộ Đánh Giá & Bài Lủng (`VERIFIED`)
- [x] `app/core/evaluator.py`: Chi Đầu (3 lá), Chi Giữa/Cuối (5 lá), kiểm tra `is_foul()`.
- [x] `tests/test_evaluator.py` (14/14 tests passed).

### Phase 4: Domain Core — Thuật Toán Phân Rã Solver (`VERIFIED`)
- [x] `app/core/solver.py`: 36,036 thế bài, lọc bài lủng, sắp xếp heuristic.
- [x] `tests/test_solver.py` (4/4 tests passed).

### Phase 5: Domain Core — Luật Chơi & Tính Điểm (`VERIFIED`)
- [x] `app/core/rules.py`: Điểm thắng/thua, bắt sập, phạt lủng, sảnh rồng, 6 đôi.
- [x] `tests/test_rules.py` (5/5 tests passed).

### Phase 6: Domain Core — Mô Phỏng Monte Carlo & EV (`VERIFIED`)
- [x] `app/core/simulator.py` & `app/core/ev_optimizer.py`: Common Random Numbers.
- [x] `tests/test_simulator.py` (4/4 tests passed).

### Phase 7: Thị Giác Máy Tính & Thư Viện Mẫu (`VERIFIED`)
- [x] `app/vision/screen_capture.py`: Chụp màn hình Retina macOS.
- [x] `app/vision/card_detector.py`: Tách bài xòe, NMS, candidate validation loại avatar.
- [x] `app/vision/card_recognizer.py`: Tách biệt Rank/Suit, phát hiện nghi ngờ.
- [x] `app/vision/card_reference_library.py`: Quản lý mẫu xác nhận trong SQLite.
- [x] `tests/test_vision.py` & `tests/test_card_detection_and_reference.py` (53/53 tests passed).

### Phase 8: Giám Sát Đồng Thời 3 Cửa Sổ Bàn Chơi (`VERIFIED`)
- [x] `app/vision/roi_manager.py`: Quản lý 3 ROI độc lập trên màn hình.
- [x] `app/services/multi_window_service.py`: Chụp 1 frame, crop 3 bàn, tracker bất biến vị trí.
- [x] `app/ui/components/multi_window_widget.py`: Giao diện giám sát 3 bàn.
- [x] `tests/test_multi_window.py` (5/5 tests passed).

### Phase 9: Giao Diện Người Dùng & Công Cụ Chẩn Đoán (`VERIFIED`)
- [x] `app/ui/main_window.py`: Cửa sổ chính 5 tab.
- [x] `app/ui/components/card_edit_dialog.py`: 13 nút Rank, 4 nút Suit, 52 lá bài.
- [x] `app/ui/components/vision_debug_dialog.py`: 4 tab chẩn đoán.
- [x] `app/ui/components/zoomable_viewer.py`: Zoom, Pan, Click Bbox.
- [x] `tests/test_ui.py` (5/5 tests passed).

### Phase 10: Cơ Sở Dữ Liệu & Lưu Trữ Phiên (`VERIFIED`)
- [x] `app/database/db.py` & `app/database/repository.py`: CRUD SQLite.
- [x] `tests/test_database.py` (1/1 test passed).
