# ACTIVE TASK — BINH 13 ANALYZER

**Nhiệm vụ hiện tại:** Khắc phục triệt để lỗi Tab 6 nhận diện 2 Bích (2♠) thành 2 Tép (2♣) và đồng bộ mã nguồn nhận diện lá bài giữa Tab 2 và Tab 6.  
**Người yêu cầu:** User / Product Owner  
**Trạng thái nhiệm vụ:** `COMPLETED / VERIFIED` (129/129 tests PASSED)

---

## 1. PHÂN TÍCH NGUYÊN NHÂN GỐC RỄ (ROOT CAUSE AUDIT)

1. **Lệch kết quả giữa Tab 2 và Tab 6:**
   - **Mã nguồn nhận diện bị phân mảnh:** Tab 6 (`MultiWindowWidget` / `MultiWindowWorker`) tự khởi tạo `CardRecognizer` riêng mà không dùng chung instance với Tab 2 (`VisionWidget`), đồng thời gọi `recognize_all(crops)` trực tiếp mà không qua bộ lọc candidate validation như Tab 2.
   - **Lỗi mẫu tham chiếu bị gán sai nhãn (Corrupt Reference):** Trong thư viện ảnh mẫu người dùng, mẫu `099c710e` vốn là lá **4 Bích (4♠)** nhưng bị lưu nhầm nhãn thành `4C` (4 Tép).
   - **Xung đột độ ưu tiên nhận diện (Priority Inversion):** Khi quét cửa sổ game có lá 2♠:
     - `CardReferenceLibrary.match_crop` tìm thấy mẫu 2♠ với độ tương đồng $0.99$ ($99\%$).
     - Tuy nhiên hàm `match_suit_glyph` đối chiếu glyph chất rời rạc (28x28) lại tìm trúng mẫu `099c710e` (bị gắn nhãn 4C) với điểm số $0.9917$, ép chất thành `Suit.CLUBS`.
     - Điều kiện kiểm tra tham chiếu cũ yêu cầu `ref_match.card.suit == final_suit`, do đó khi `SPADES != CLUBS`, hệ thống loại bỏ luôn kết quả tham chiếu 2♠ $99\%$ và trả về kết quả sai là `2♣` kèm lý do `Ảnh mẫu có trong thư viện nhưng chưa được sử dụng`.

---

## 2. GIẢI PHÁP ĐÃ TRIỂN KHAI

1. **Dọn dẹp mẫu tham chiếu lỗi:** Xóa mẫu `099c710e` bị gán sai nhãn trong cơ sở dữ liệu thư viện ảnh mẫu.
2. **Nâng cấp độ ưu tiên của Full Card Reference ([card_recognizer.py](file:///Users/levanquang/tool/app/vision/card_recognizer.py)):**
   - Khi một lá bài khớp với mẫu tham chiếu đã xác nhận có Rank trùng khớp và độ tin cậy chất $\ge 0.78$ và tổng thể $\ge 0.78$, chất từ mẫu tham chiếu toàn diện được công nhận là chân lý, không bao giờ bị ghi đè bởi một glyph chất rời rạc từ lá bài khác.
3. **Hợp nhất hàm nhận diện chung `recognize_cards_pipeline` ([vision_service.py](file:///Users/levanquang/tool/app/services/vision_service.py)):**
   - Cả Tab 2 và Tab 6 đều gọi qua hàm chuẩn hóa duy nhất này.
   - Chia sẻ chung instance `CardReferenceLibrary`, `CardRecognizer`, `CardDetector` từ `MainWindow`.
4. **Kiểm thử tự động:**
   - Bổ sung test `test_2_spades_never_confused_with_clubs_when_matching_references` trong `tests/test_card_detection_and_reference.py`.
   - Toàn bộ 129/129 tests PASSED (100%).
