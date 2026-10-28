# ACTIVE TASK — BINH 13 ANALYZER

**Nhiệm vụ hiện tại:** Hợp nhất quy trình và hàm nhận diện lá bài (Unified Card Recognition Pipeline) giữa Tab 2 (Quét màn hình CV) và Tab 6 (Bot 3 Cửa Sổ) để đồng bộ 100% kết quả nhận diện và thư viện ảnh mẫu.  
**Người yêu cầu:** User / Product Owner  
**Trạng thái nhiệm vụ:** `COMPLETED`

---

## 1. MỤC TIÊU NHIỆM VỤ

1. **Thực trạng và nguyên nhân lệch kết quả giữa Tab 2 và Tab 6:**
   - Tab 2 (`VisionWidget`): Khởi tạo `CardReferenceLibrary` riêng, chạy qua `VisionWorker` và áp dụng bộ lọc nghiêm ngặt loại bỏ các đối tượng không phải bài (avatar, nút bấm UI, chip cược) với ngưỡng tin cậy $rank\_conf \ge 0.65$ và $suit\_conf \ge 0.65$.
   - Tab 6 (`MultiWindowWidget` / `MultiWindowWorker`): Khởi tạo `CardRecognizer` độc lập (không chia sẻ thư viện ảnh mẫu đã lưu của Tab 2), gọi trực tiếp `recognize_all(crops)` mà không chạy qua bộ lọc chuẩn hóa nghiêm ngặt. Dẫn đến các nút bấm, vật thể trên bàn chơi bị nhận nhầm thành lá bài giả, gây sai lệch kết quả hoặc không nhận diện đúng.

2. **Giải pháp kiến trúc hợp nhất (Unified Pipeline):**
   - Xây dựng hàm chuẩn hóa `recognize_cards_pipeline(image, detector, recognizer, min_confidence=0.65)` trong `app/services/vision_service.py` đóng gói toàn bộ quy trình:
     1. Quét đối tượng thẻ bài (`detect_card_objects`).
     2. Nhận diện Rank & Suit tách biệt (`recognize_crop`).
     3. Lọc nghiêm ngặt: yêu cầu có đủ rank/suit crop, $rank\_conf \ge 0.65$, $suit\_conf \ge 0.65$, loại trừ vật thể `NON_CARD_OBJECT`.
     4. Khử trùng lặp và xác nhận trạng thái `CONFIRMED`.
   - Cả Tab 2 (`VisionWorker`) và Tab 6 (`MultiWindowWidget._on_window_selected`, `MultiWindowWorker.start_loop`) đều sử dụng chung 1 hàm duy nhất này.
   - Chia sẻ chung instance `CardReferenceLibrary` và `CardRecognizer` từ `MainWindow` truyền xuống `MultiWindowWidget`, đảm bảo bất kỳ ảnh mẫu nào được lưu ở Tab 2 thì Tab 6 nhận được ngay lập tức.
   - Bổ sung nút "📚 Thư viện ảnh mẫu" trên thanh công cụ của Tab 6 để người dùng có thể mở quản lý ảnh mẫu trực tiếp từ Tab 6.

3. **Kết quả xác minh nghiệm thu:**
   - 100% các luồng quét hình ảnh của Tab 2 và Tab 6 đều gọi qua `recognize_cards_pipeline`.
   - Tab 2 và Tab 6 dùng chung 1 instance `CardReferenceLibrary` và `CardRecognizer`.
   - Đã chạy kiểm thử thực tế toàn bộ hệ thống bằng lệnh `.venv/bin/pytest tests/`: **128 / 128 tests PASSED (100%)**.
