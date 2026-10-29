# ACTIVE TASK — BINH 13 ANALYZER

**Nhiệm vụ hiện tại:** Khắc phục triệt để lỗi một số quân bài đã xác nhận đúng nhưng không thể nhận diện đúng hoàn toàn (ví dụ 3♠, 6♠ không hiện `[Mẫu]` mà điểm đối chiếu mẫu chỉ đạt 44%, hiển thị sai sang 3♣ trong danh sách gợi ý).  
**Người yêu cầu:** User / Product Owner  
**Trạng thái nhiệm vụ:** `COMPLETED / VERIFIED` (130/130 tests PASSED)

---

## 1. PHÂN TÍCH NGUYÊN NHÂN GỐC RỄ (ROOT CAUSE AUDIT)

1. **Sai lệch dịch chuyển vi mô (Zero-Shift Constraint trên khung 1x1):**
   - Cả ảnh truy vấn và ảnh mẫu khi trích xuất glyph chất (suit) đều được resize về kích thước chuẩn cố định $(28, 28)$ (và rank glyph là $24 \times 36$).
   - `cv2.matchTemplate(q_glyph, ref_glyph, cv2.TM_CCOEFF_NORMED)` thực hiện trên 2 ảnh có cùng kích thước tạo ra ma trận kết quả chỉ có kích thước đúng $1 \times 1$ (tương ứng độ lệch $(0, 0)$).
   - Trong thực tế cắt ảnh từ màn hình, do làm tròn bounding box số nguyên hoặc ngưỡng phân ngưỡng Otsu biến thiên 1-2 pixel, hai lá bài giống hệt nhau nhưng bị lệch 1-2 pixel sẽ khiến điểm tương quan chéo chuẩn hóa (NCC) tại $(0,0)$ tụt dốc thảm hại từ $0.99$ xuống chỉ còn $0.57$.

2. **Hiện tượng đứt gãy cuống biểu tượng Bích / Tép (Stem Disconnection):**
   - Trong biểu tượng chất Bích (♠) hoặc Tép (♣), phần cuống bên dưới nối với phần thân trên qua một cổ thắt rất mảnh (chỉ 1-2 pixel).
   - Khi binarize bằng Otsu ở một số vùng ánh sáng, phần cuống bị đứt rời thành 2 Connected Component riêng biệt (Thân: 493 px, Cuống: 20 px).
   - Thuật toán `extract_primary_glyph` trước đây chỉ lấy component có diện tích lớn nhất và loại bỏ cuống. Kết quả là ảnh truy vấn bị mất cuống và bị kéo giãn dọc 20% khi resize về $28 \times 28$, trong khi ảnh mẫu lại có cuống đầy đủ. Sự bất cân xứng này khiến độ tương quan với chính mẫu của nó giảm xuống dưới 0.60.
   - Trớ trêu thay, hình dáng thân bích bị cụt cuống lại có độ tương quan ngẫu nhiên $0.73$ với một mẫu 3 Tép (3♣), dẫn đến việc thuật toán đối chiếu đề xuất 3♣ thay vì 3♠.

3. **Hình phạt hàm mũ bậc 3 (Cubic Gating Penalty) triệt tiêu điểm số:**
   - Trong `CardReferenceLibrary.match_crop`, công thức gating:
     `if score_suit < 0.68: raw_score *= (score_suit / 0.68) ** 3`
   - Khi `score_suit` giảm xuống $0.57$, hệ số phạt $(0.57 / 0.68)^3 \approx 0.59$ dìm điểm số tổng thể từ $0.72$ xuống còn $0.44$ ($44\%$).
   - Điểm số $0.44 < 0.68$ khiến mẫu không được chấp nhận là `is_confident`, `is_reference_match` bị gán `False` (không hiện nhãn `[Mẫu]`), và `3S: 44%` bị đẩy xuống danh sách dự đoán phụ.

---

## 2. GIẢI PHÁP ĐÃ TRIỂN KHAI

1. **Nâng cấp tiền xử lý Glyph bằng Morphological Closing ([card_reference_library.py](file:///Users/levanquang/tool/app/vision/card_reference_library.py)):**
   - Sử dụng kernel ellipse $3 \times 3$ (`cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)`) ngay sau khi binarize bằng Otsu để hàn gắn các vi rãnh 1-2 pixel giữa thân và cuống lá bài.
   - Tự động gom cụm các component cuống nằm ngay dưới thân chất (`target_size == (28, 28)`), bảo toàn 100% hình dạng biểu tượng nguyên bản cho cả ảnh chụp lẫn ảnh mẫu.

2. **Bổ sung biên trượt dung sai tịnh tiến $\pm 2$ pixel (Translational Invariance):**
   - Thêm biên đệm viền 2 pixel (`cv2.copyMakeBorder(query, 2, 2, 2, 2, cv2.BORDER_CONSTANT)`) trước khi gọi `cv2.matchTemplate`.
   - Lấy giá trị cực đại `np.max(res)` trong cửa sổ trượt $5 \times 5$, cho phép mẫu tìm thấy vị trí khớp tuyệt đối ngay cả khi crop bị lệch 1-2 pixel. Điểm số tương quan chất tăng vọt từ $0.57$ lên $\mathbf{0.86}$!

3. **Chuẩn hóa ngưỡng chấp thuận `[Mẫu]` ([card_recognizer.py](file:///Users/levanquang/tool/app/vision/card_recognizer.py)):**
   - Đồng bộ ngưỡng gating tối thiểu giữa `match_crop` và `CardRecognizer` ở mức $\ge 0.68$.
   - Khi Rank và Suit đều khớp mẫu với độ tin cậy $\ge 0.68$ và điểm tổng thể $\ge 0.68$, lá bài lập tức được gắn cờ `is_reference_match = True` và hiển thị nhãn `[Mẫu]` xanh rực rỡ.

---

## 3. KẾT QUẢ XÁC MINH THỰC TẾ

- **Ảnh chụp thực tế ([IMG_1287.PNG](file:///Users/levanquang/Downloads/IMG_1287.PNG)):**
  - **13/13 lá bài (100%)** đều nhận diện chính xác và đạt nhãn `[Mẫu]` (bao gồm cả 3♠ và 6♠).
  - Lá 3♠: Độ tin cậy $0.9680$ `[Mẫu]`, mẫu 3♠ đạt điểm cao nhất thay vì 3♣.
  - Lá 6♠: Độ tin cậy $0.9865$ `[Mẫu]`, mẫu 6♠ đạt điểm cao nhất thay vì 6♣.
- **Kiểm thử tự động:**
  - Bổ sung test mới: `test_subpixel_shift_and_separated_stem_glyph_matching`.
  - Toàn bộ test suite: **130/130 tests PASSED (100%)**.
