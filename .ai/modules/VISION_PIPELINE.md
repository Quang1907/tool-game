# MODULE DOCUMENTATION: VISION PIPELINE (`app/vision/`)

---

## 1. MỤC ĐÍCH & PHẠM VI

Phân hệ Vision Pipeline chịu trách nhiệm toàn bộ quá trình thị giác máy tính không xâm phạm trên macOS:
1. Chụp màn hình bàn chơi độ phân giải cao (Retina 2x support).
2. Tự động phát hiện vị trí các lá bài nằm tự do, xếp xòe, hoặc chồng lấp một phần mà **không dựa vào các ô cố định**.
3. Thực hiện kiểm tra tính hợp lệ của đối tượng (Candidate Validation) để loại bỏ avatar, nút bấm, nền bàn.
4. Nhận diện độc lập Rank và Suit qua Template Matching đa tỷ lệ và thư viện ảnh mẫu tự học.
5. Quản lý nhận diện 3 cửa sổ bàn chơi độc lập cùng lúc.

---

## 2. CÁC TẬP TIN NGUỒN VÀ THÀNH PHẦN CHÍNH

### 2.1. `card_detector.py`
- `CardDetectionStatus`: Tập hợp trạng thái chẩn đoán:
  `VALID_CARD`, `INVALID_CARD`, `INVALID_CARD_CROP`, `NON_CARD_OBJECT`, `MISSING_RANK_REGION`, `MISSING_SUIT_REGION`, `LOW_QUALITY_CARD`, `UNCERTAIN_CARD`.
- `CardCrop`: Đối tượng chứa:
  - `bbox`: Tọa độ `(x, y, w, h)` trên frame gốc.
  - `image`: Ảnh đã nắn chỉnh chuẩn hóa kích thước $120 \times 168\text{ px}$.
  - `raw_patch`: Mảng pixel gốc cắt trực tiếp từ ảnh chụp bàn chơi.
  - `corner_crop`: Vùng góc trái trên chứa ký hiệu bài.
- `detect_card_objects(table_image) -> (List[CardCrop], DetectionDebugInfo)`:
  - **Lọc Avatar & Nút UI:** Kiểm tra độ tròn $> 0.65$ và khối vuông $0.82 \le w/h \le 1.28$ có độ trắng $< 50\%$ $\rightarrow$ gán `NON_CARD_OBJECT`. Kiểm tra độ bão hòa màu $> 115$ $\rightarrow$ loại bỏ nút UI.
  - **Tách bài xòe (Fanned dissection):** Quét biên gradient trên 2 dải biên an toàn $16\%$ trên và dưới của cụm bài bị đè để tìm đỉnh biên cạnh bài, tránh vùng minh họa tướng J, Q, K ở giữa.
  - **Deduplication NMS:** Gộp các bounding box lồng nhau hoặc trùng lặp với ngưỡng IoU 0.48.

### 2.2. `card_recognizer.py`
- `DetectedCard`: Thực thể bài nhận diện chứa `card: Optional[Card]`, `confidence`, `rank_confidence`, `suit_confidence`, `rank_crop`, `suit_crop`, `is_uncertain`, `recognition_status`.
- `recognize_crop(crop: CardCrop) -> DetectedCard`:
  - **Chặn đối tượng không hợp lệ:** Nếu `crop_status` là `NON_CARD_OBJECT` hoặc tỷ lệ trắng góc $< 35\%$, trả về ngay `card=None, confidence=0.0`.
  - **Trích xuất góc động (`extract_dynamic_corner_patches`):** Dùng Connected Components để phân định `rank_crop` và `suit_crop`, không dùng lát cắt cứng để tránh chém mất đầu chữ số cao (như 10, Q, K).
  - **Phân loại màu (Red vs Black):** Phân biệt chất Đỏ (♦, ♥) và chất Đen (♠, ♣) dựa trên sắc tố HSV và tỷ lệ đỏ/xanh.
  - **Nhận diện độc lập:** So khớp Rank độc lập; so khớp Suit độc lập; chỉ kết hợp khi cả hai đều hợp lệ.

### 2.3. `card_reference_library.py`
- Quản lý thư viện ảnh mẫu đã xác nhận của người dùng được lưu trữ trong SQLite (`card_references`).
- Lưu trữ các vector glyph chuẩn của Rank ($24 \times 36$) và Suit ($28 \times 28$).
- **Nguyên tắc an toàn thư viện:** Mẫu từ thư viện chỉ được áp dụng nếu cả Rank và Suit độc lập đều khớp với ảnh mẫu đã lưu ($\ge 70\%$). Không bao giờ để mẫu $9♦$ đổi nhãn của ảnh $Q♦$.

### 2.4. `roi_manager.py` & `window_manager.py`
- `ROIManager`: Quản lý 3 vùng ROI tương ứng với 3 cửa sổ game trên màn hình MacBook Retina. Tự động chuyển đổi giữa tọa độ hiển thị (Points) và tọa độ pixel thực tế (Pixels 2x).
- `WindowManager`: Quản lý danh sách cửa sổ macOS, tính toán tỷ lệ che khuất (Occlusion ratio) giữa các cửa sổ.

---

## 3. CÁC BÀI KIỂM THỬ LIÊN QUAN

- `tests/test_vision.py`: 28 tests kiểm tra tiền xử lý, template matching, phát hiện bài đơn, phát hiện bài xòe, khử viền xanh, 9 mẫu bài thực tế.
- `tests/test_card_detection_and_reference.py`: 25 tests bao gồm:
  - Test A: Loại trừ avatar người chơi, không đoán mò sang `KD`.
  - Test B: Kiểm tra 13 nút Rank.
  - Test C: Kiểm tra 4 nút Suit.
  - Test D: Đồng bộ tọa độ crop với frame gốc.
  - Test E: An toàn khi lưu ảnh mẫu và xác nhận.
- `tests/test_multi_window.py`: 5 tests kiểm tra Retina 2x crop, occlusion, card tracker không tính lại khi bài chỉ di chuyển.
