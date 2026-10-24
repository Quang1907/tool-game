# Binh 13 Analyzer — macOS Professional Edition
> **Công cụ nhận diện bài bằng Computer Vision, Solver tổ hợp 3-5-5, mô phỏng Monte Carlo và tối ưu hóa Expected Value (EV) cho game Binh 13 (Mậu Binh) trên macOS.**

[![macOS](https://img.shields.io/badge/Platform-macOS%20Sequoia%20%7C%20Sonoma%20%7C%20Ventura-black?logo=apple)](https://apple.com)
[![Apple Silicon](https://img.shields.io/badge/Architecture-Apple%20Silicon%20(ARM64)%20%2F%20Intel-blue)](https://apple.com)
[![Python](https://img.shields.io/badge/Python-3.11+-brightgreen?logo=python)](https://python.org)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20(Qt%20for%20Python)-green?logo=qt)](https://qt.io)
[![Tests](https://img.shields.io/badge/Tests-55%20passed%20(100%25)-success?logo=pytest)](https://pytest.org)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## 1. Giới thiệu tổng quan

**Binh 13 Analyzer** là ứng dụng desktop native dành riêng cho macOS, hỗ trợ người chơi và nhà nghiên cứu chiến thuật phân tích các thế bài Binh 13 (Mậu Binh / Chinese Poker).

Ứng dụng tuân thủ nguyên tắc **an toàn, bảo mật và minh bạch**:
- **Không xâm nhập tiến trình game:** Hoạt động hoàn toàn độc lập thông qua hình ảnh màn hình do người dùng chọn hoặc bài nhập thủ công.
- **Không can thiệp mạng:** 100% offline, không gửi dữ liệu ra bên ngoài.
- **Không tự động thao tác game:** Chỉ cung cấp thông tin thống kê xác suất và gợi ý chiến thuật cho người dùng.

---

## 2. Tính năng nổi bật

### 2.1. Nhận diện bài bằng Computer Vision & Chụp màn hình macOS
- **Chụp màn hình linh hoạt:**
  - Hỗ trợ chọn màn hình bất kỳ trong cấu hình nhiều màn hình (Multi-monitor).
  - Hỗ trợ chọn cửa sổ ứng dụng (Chrome, Safari, Edge, Game, hoặc ứng dụng desktop khác) qua phím Space / click chuột.
  - Hỗ trợ chọn vùng tùy ý bằng cách kéo chuột (`screencapture -i -s -r`).
  - Tự động phát hiện và hướng dẫn cấp quyền macOS Screen Recording (không âm thầm trả về ảnh đen).
- **Bộ xem ảnh Zoomable & Kéo Pan Retina:**
  - Giữ nguyên độ phân giải vật lý Retina gốc, không bóp méo tỷ lệ.
  - Zoom in/out bằng con lăn chuột hoặc nút bấm, nút 1:1 và Fit to View, kéo di chuyển vùng nhìn mượt mà.
- **Quy trình nhận diện bài mạnh mẽ:**
  - 3 chiến lược tách bài: Tự động tìm Contour, Cắt thanh ngang 13 lá (`Horizontal Strip 13`), và Cắt lưới 3 hàng 3-5-5 (`Grid 3 Rows`).
  - Tiền xử lý tương phản thích ứng CLAHE, khử nhiễu song phương.
  - Nhận diện rank (A, 2-10, J, Q, K) bằng template matching đa tỷ lệ với font hệ thống macOS.
  - Phân loại chất bài (♠ ♣ ♦ ♥) bằng phân tích màu HSV kết hợp so khớp mẫu.
- **Xác minh & Sửa bài thông minh:**
  - Hiển thị badge độ tin cậy trực quan cho từng lá.
  - Hộp thoại sửa bài 1 chạm cho phép sửa ngay rank/suit nếu có lá bị che khuất hoặc nhận diện nhầm trước khi giải.

### 2.2. Bộ đánh giá bài (Evaluator) & Xử lý luật Binh
- Đánh giá **Chi Đầu (3 lá)**: Mậu thầu, Một đôi, Sám cô với đầy đủ kicker.
- Đánh giá **Chi Giữa & Chi Cuối (5 lá)**: Mậu thầu, Một đôi, Hai đôi, Sám cô, Sảnh (hỗ trợ cả sảnh A-2-3-4-5 theo luật chọn), Thùng, Cù lũ, Tứ quý, Thùng phá sảnh.
- Phát hiện và loại bỏ tuyệt đối **Bài Lủng** ($\text{Chi Cuối} \ge \text{Chi Giữa} \ge \text{Chi Đầu}$).
- Hỗ trợ phát hiện Mậu Binh Thắng Trắng (Sảnh Rồng, Lục Phé Bôn, v.v.).

### 2.3. Solver tổ hợp siêu tốc (Combinatorial Solver)
- Duyệt trọn vẹn không gian tổ hợp $\binom{13}{3} \times \frac{\binom{10}{5}}{2} = 36,036$ cách chia bài.
- Sử dụng bộ nhớ đệm ma trận con (**1,573 phép đánh giá** thay vì $108,108$) giúp giải toàn bộ bài trong **dưới 90 mili-giây** trên MacBook Apple Silicon.
- Đề xuất các phương án theo 4 chiến lược: *Cân bằng (Balanced)*, *Ưu tiên Chi Đầu (Front-heavy)*, *Ưu tiên Chi Cuối (Back-heavy)*, *Ưu tiên Chi Giữa (Middle-heavy)*.

### 2.4. Mô phỏng Monte Carlo & Tối ưu hóa EV (Expected Value)
- Rút 39 lá bài chưa thấy còn lại trong bộ bài 52 lá để chia cho 1–3 đối thủ (hoàn toàn không trùng bài).
- Sử dụng phương pháp **Common Random Numbers (CRN)**: Đánh giá các phương án xếp bài trên cùng tập kịch bản bài đối thủ để giảm thiểu phương sai khi so sánh.
- Thống kê chi tiết: Điểm EV trung bình, Tỷ lệ thắng/hòa/thua toàn bàn, Tỷ lệ thắng từng chi, Tỷ lệ Sập 3 chi (Scoop), Độ lệch chuẩn và **Khoảng tin cậy 95% (95% CI)**.

### 2.5. Giao diện macOS hiện đại (PySide6)
- Chuẩn phong cách Apple Cupertino với Dark Mode sang trọng, icon chất bài rõ nét (♠ ♣ ♦ ♥).
- Xử lý đa luồng ngầm qua `QThread` đảm bảo giao diện không bao giờ bị đơ (freeze) khi giải thuật toán.
- Lưu lịch sử phiên phân tích vào SQLite cục bộ (`~/.binh13_analyzer/data.db`), hỗ trợ xuất file CSV và JSON.

---

## 3. Cài đặt và Khởi chạy

### Yêu cầu hệ thống
- MacBook chạy vi xử lý **Apple Silicon (M1, M2, M3, M4)** hoặc Intel x86_64.
- macOS Ventura (13.0), Sonoma (14.0) hoặc Sequoia (15.0+).
- Python 3.11+ (khuyên dùng qua Homebrew).

### Cài đặt nhanh bằng Script
```bash
# 1. Clone hoặc tải mã nguồn
cd /Users/levanquang/tool

# 2. Cài đặt môi trường ảo và thư viện
./scripts/setup_macos.sh

# 3. Chạy toàn bộ kiểm thử xác nhận
./scripts/test.sh

# 4. Khởi chạy ứng dụng
./scripts/run_macos.sh
```

---

## 4. Cấu trúc thư mục

```text
tool/
├── app/
│   ├── main.py                     # Điểm khởi chạy ứng dụng
│   ├── core/                       # Domain Core (Thuần Python & NumPy, độc lập UI)
│   │   ├── card.py                 # Card, Rank, Suit, Deck, Hand, Parser, Validator
│   │   ├── evaluator.py            # Đánh giá Chi Đầu, Giữa, Cuối & Kiểm tra bài lủng
│   │   ├── rules.py                # Cấu hình luật tính điểm & so sánh tay đôi
│   │   ├── solver.py               # Giải tổ hợp 36,036 cách chia bài (84ms)
│   │   ├── simulator.py            # Mô phỏng Monte Carlo đối thủ từ 39 lá còn lại
│   │   └── ev_optimizer.py         # Tối ưu EV bằng Common Random Numbers (CRN)
│   ├── vision/                     # Computer Vision & macOS Screen Capture
│   │   ├── screen_capture.py       # Chụp vùng màn hình macOS
│   │   ├── image_preprocessor.py   # Lọc cạnh, nâng độ tương phản CLAHE
│   │   ├── card_detector.py        # Trích xuất khung viền từng lá bài
│   │   ├── card_recognizer.py      # Nhận diện ONNX / Khớp mẫu
│   │   └── recognition_validator.py# Kiểm tra đủ 13 lá, bài trùng
│   ├── database/                   # SQLite Persistence
│   │   ├── db.py                   # Kết nối SQLite & Migration bảng
│   │   └── repository.py           # CRUD lưu phiên phân tích, lịch sử
│   ├── services/                   # Application Services
│   │   ├── analysis_service.py     # Điều phối luồng nghiệp vụ
│   │   └── simulation_service.py   # Worker QThread chạy nền
│   └── ui/                         # PySide6 Presentation Layer
│       ├── main_window.py          # Cửa sổ chính, tab, status bar
│       ├── styles.py               # Theme macOS Dark Mode
│       └── components/             # Widget tái sử dụng (CardWidget, Selector, Solver, etc.)
├── config/
│   └── default_rules.json          # File cấu hình luật điểm JSON
├── docs/                           # Tài liệu chuyên sâu kiến trúc & thuật toán
├── scripts/                        # Scripts tự động hóa macOS
│   ├── setup_macos.sh
│   ├── run_macos.sh
│   ├── test.sh
│   └── build_macos.sh
├── tests/                          # 49 Unit & Integration Tests (pytest)
├── pyproject.toml
└── requirements.txt
```

---

## 5. Kết quả kiểm thử (Test Matrix)

Chạy `./scripts/test.sh`:
```text
============================= test session starts ==============================
collected 49 items

tests/test_card.py (14 tests) ............. PASSED
tests/test_database.py (1 test) ........... PASSED
tests/test_evaluator.py (13 tests) ........ PASSED
tests/test_integration.py (1 test) ........ PASSED
tests/test_rules.py (5 tests) ............. PASSED
tests/test_simulator.py (4 tests) ......... PASSED
tests/test_solver.py (4 tests) ............ PASSED
tests/test_ui.py (2 tests) ................ PASSED
tests/test_vision.py (5 tests) ............ PASSED

============================= 49 passed in 21s ==============================
```

---

## 6. Đóng gói ứng dụng macOS (`.app`)

Để tạo file ứng dụng macOS độc lập chạy qua Finder:
```bash
./scripts/build_macos.sh
```
File ứng dụng sẽ nằm tại: `dist/Binh13Analyzer.app`.

### Cấp quyền chụp màn hình (Screen Recording) trên macOS:
Nếu sử dụng tính năng chụp vùng màn hình trực tiếp:
1. Vào **System Settings** (Cài đặt hệ thống) -> **Privacy & Security** (Quyền riêng tư & Bảo mật).
2. Chọn **Screen Recording** (Ghi màn hình).
3. Bật quyền cho Terminal / Binh13Analyzer.
