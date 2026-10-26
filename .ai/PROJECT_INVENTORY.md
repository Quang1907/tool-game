# PROJECT INVENTORY — BINH 13 ANALYZER (macOS)

**Repository:** `/Users/levanquang/tool`  
**Git Branch:** `main` | **Working Tree:** Clean  
**Runtime:** Python 3.11.17 (`.venv/bin/python3`)  
**OS Target:** macOS Sequoia 15.4.1 (Apple Silicon arm64 / Intel x86_64)

---

## 1. CẤU TRÚC THƯ MỤC THỰC TẾ

```text
/Users/levanquang/tool/
├── .venv/                         # Python 3.11 Virtual Environment (Homebrew Python 3.11.17)
├── .ai/                           # Hệ thống Master Engineer & Quản lý tri thức AI
├── app/
│   ├── __init__.py
│   ├── main.py                    # Entry point chính của ứng dụng PySide6
│   ├── core/                      # Phân hệ cốt lõi nghiệp vụ (Zero GUI dependencies)
│   │   ├── __init__.py
│   │   ├── card.py                # Card, Suit, Rank, Deck, Hand models & parsers
│   │   ├── evaluator.py           # Bộ đánh giá Chi Đầu (3 lá), Chi Giữa/Cuối (5 lá), kiểm tra Foul
│   │   ├── rules.py               # Luật tính điểm Mậu Binh, Thắng trắng, Phạt sập
│   │   ├── solver.py              # Thuật toán phân rã 36,036 thế bài & lọc thế bài hợp lệ
│   │   ├── simulator.py           # Bộ mô phỏng Monte Carlo 1-3 đối thủ
│   │   └── ev_optimizer.py        # Tối ưu hóa Expected Value (EV) với Common Random Numbers
│   ├── vision/                    # Phân hệ thị giác máy tính & nhận diện quân bài
│   │   ├── __init__.py
│   │   ├── screen_capture.py      # Chụp màn hình macOS Retina (screencapture & QScreen)
│   │   ├── screen_capture_service.py # Dịch vụ chụp màn hình định kỳ
│   │   ├── image_preprocessor.py  # Tiền xử lý, lọc viền xanh, chuẩn hóa kích thước 120x168
│   │   ├── card_detector.py       # Tự động phát hiện vị trí lá bài, NMS, tách bài xòe, lọc avatar
│   │   ├── card_recognizer.py     # Nhận diện độc lập Rank và Suit, phát hiện trạng thái nghi ngờ
│   │   ├── card_reference_library.py # Quản lý thư viện ảnh mẫu đã xác nhận (SQLite)
│   │   ├── card_state.py          # Quản lý trạng thái và tracking quân bài theo thời gian
│   │   ├── recognition_validator.py # Xác minh đủ 13 lá không trùng lặp
│   │   ├── roi_manager.py         # Quản lý vùng quan sát (ROI) cho 3 cửa sổ bàn chơi
│   │   ├── window_manager.py      # Quản lý danh sách cửa sổ macOS và mức độ che khuất
│   │   └── template_engine.py     # Multi-scale template matching NCC cho Rank và Suit
│   ├── database/                  # Phân hệ lưu trữ cục bộ SQLite
│   │   ├── __init__.py
│   │   ├── db.py                  # Khởi tạo SQLite connection, schema tables & migration
│   │   └── repository.py          # Repository thực hiện CRUD cho Sessions, Arrangements, References
│   ├── services/                  # Phân hệ Application Services điều phối luồng
│   │   ├── __init__.py
│   │   ├── analysis_service.py    # Dịch vụ giải bài kết hợp Solver và Evaluator
│   │   ├── simulation_service.py  # Dịch vụ chạy mô phỏng nền (QThread worker)
│   │   ├── vision_service.py      # Dịch vụ chụp và nhận diện bài đơn cửa sổ
│   │   └── multi_window_service.py # Dịch vụ quản lý nhận diện 3 cửa sổ bàn chơi đồng thời
│   └── ui/                        # Phân hệ giao diện máy tính để bàn (PySide6)
│       ├── __init__.py
│       ├── main_window.py         # Cửa sổ chính với 5 Tab chức năng
│       ├── styles.py              # Hệ thống style dark mode Apple HIG
│       └── components/            # Các widget và dialog tái sử dụng
│           ├── card_widget.py     # Hiển thị lá bài trực quan
│           ├── card_selector.py   # Dialog chọn bài thủ công 52 lá
│           ├── card_edit_dialog.py # Dialog kiểm tra & sửa nhận diện (13 nút Rank, 4 nút Suit)
│           ├── card_reference_manager.py # Dialog quản trị thư viện ảnh mẫu đã xác nhận
│           ├── vision_widget.py   # Widget Tab 1: Vision Single Window
│           ├── zoomable_viewer.py # Widget hiển thị ảnh zoomable, pan, click bbox
│           ├── vision_debug_dialog.py # Dialog chẩn đoán 4 Tab: Ảnh gốc, Overlay, Crop, Reference
│           ├── multi_window_widget.py # Widget Tab 2: Quản lý 3 cửa sổ bàn chơi đồng thời
│           ├── solver_widget.py   # Widget Tab 3: Bảng xếp hạng thế bài tối ưu
│           ├── simulator_widget.py# Widget Tab 4: Điều khiển mô phỏng Monte Carlo & EV
│           └── history_widget.py  # Widget Tab 5: Lịch sử ván bài đã lưu
├── config/
│   └── default_rules.json         # Cấu hình luật tính điểm mặc định
├── docs/                          # Tài liệu kỹ thuật chi tiết
│   ├── ALGORITHM.md
│   ├── MACOS_SETUP.md
│   └── VISION_MODEL.md
├── scripts/                       # Scripts tự động hóa macOS
│   ├── setup_macos.sh
│   ├── run_macos.sh
│   ├── test.sh
│   ├── build_macos.sh
│   └── macos_window_helper.swift
├── tests/                         # Bộ kiểm thử tự động pytest (104 tests)
│   ├── fixtures/real_samples/     # 9 mẫu ảnh bài thực tế (KD, KC, JC, JH, 7D, 6D, 5D, 4H...)
│   ├── test_card.py
│   ├── test_evaluator.py
│   ├── test_rules.py
│   ├── test_solver.py
│   ├── test_simulator.py
│   ├── test_ui.py
│   ├── test_vision.py
│   ├── test_database.py
│   ├── test_integration.py
│   ├── test_multi_window.py
│   └── test_card_detection_and_reference.py
├── pyproject.toml                 # Cấu hình dự án Python, dependencies và pytest
├── requirements.txt               # Danh sách thư viện phụ thuộc
├── Binh13Analyzer.spec            # Cấu hình đóng gói PyInstaller cho macOS
└── README.md                      # Giới thiệu dự án và hướng dẫn sử dụng nhanh
```

---

## 2. THÔNG SỐ DEPENDENCIES ĐÃ CÀI ĐẶT

| Package | Phiên bản cài đặt | Vai trò |
|---|---|---|
| `python` | 3.11.17 | Ngôn ngữ thực thi chính (Homebrew ARM64) |
| `PySide6` | 6.8.0.2 | Framework GUI Qt6 native cho macOS |
| `opencv-python` | 4.10.0.84 | Xử lý ảnh số, template matching, perspective warp |
| `numpy` | 2.2.0 | Tính toán ma trận mảng, thống kê Monte Carlo |
| `Pillow` | 11.0.0 | Hỗ trợ xử lý ảnh bitmap và render font ký hiệu |
| `onnxruntime` | 1.20.1 | Runtime inference cho model học sâu (khi có weights) |
| `pytest` | 9.1.1 | Framework kiểm thử tự động |
| `pyinstaller` | 6.11.1 | Đóng gói bundle `.app` cho macOS |

---

## 3. LỆNH CHẠY DỰ ÁN

- **Khởi chạy ứng dụng GUI:**
  ```bash
  .venv/bin/python -m app.main
  # hoặc
  ./scripts/run_macos.sh
  ```
- **Chạy toàn bộ 104 test:**
  ```bash
  .venv/bin/pytest tests/
  # hoặc
  ./scripts/test.sh
  ```
- **Đóng gói ứng dụng macOS `.app`:**
  ```bash
  ./scripts/build_macos.sh
  ```
