# ACTIVE TASK — BINH 13 ANALYZER

**Nhiệm vụ hiện tại:** Suy luận chính xác 13 lá bài của nhà đối thủ (#4) từ 3 cửa sổ game (39 lá bài) và tính toán thế bài phản công tối ưu cho 3 bộ bài để đánh thắng đối thủ.  
**Người yêu cầu:** User / Product Owner  
**Trạng thái nhiệm vụ:** `COMPLETED / VERIFIED` (124/124 tests PASSED)

---

## 1. MỤC TIÊU NHIỆM VỤ

1. **Khóa chặt 13 lá bài của nhà đối thủ (Nhà thứ 4):**
   Trong ván Mậu Binh 4 người (bộ bài chuẩn 52 lá không tính Joker), khi nhận diện đủ 39 lá bài từ 3 cửa sổ ($3 \times 13 = 39$), thực hiện phép trừ tập hợp $52 - 39 = 13$ để suy luận chính xác 100% 13 lá bài mà nhà đối thủ còn lại đang nắm giữ.
2. **Giải thế bài tối ưu nhất của đối thủ:**
   Sử dụng `Solver` để giải thế bài 3 chi (Đầu, Giữa, Cuối) tối ưu nhất mà đối thủ có thể xếp.
3. **Chiến lược phản công cho 3 cửa sổ đánh thắng đối thủ:**
   Thay vì chỉ xếp bài độc lập, hệ thống so sánh đối đầu trực tiếp (`compare_head_to_head`) tất cả các thế bài hợp lệ của từng cửa sổ với thế bài của đối thủ, tự động chọn thế bài giúp **Bắt sập 3 chi (+6 điểm)** hoặc tối đa hóa điểm thắng chi trước đối thủ.
4. **Hiển thị trực quan trên giao diện:**
   Bổ sung bảng điều khiển đối thủ `OpponentDeductionPanel` hiển thị 13 lá bài đối thủ, cách xếp bài đối thủ, và huy hiệu kết quả đối đầu trên từng cửa sổ người chơi.

---

## 2. TIẾN ĐỘ THỰC HIỆN

- [x] Tạo `CollaborativeTableAnalyzer` trong `app/core/collaborative_analyzer.py` với logic loại trừ bài 52 cây và tối ưu hóa phản công.
- [x] Tích hợp `OpponentDeductionPanel` và huy hiệu đối đầu `box_vs_opp` vào `MultiWindowWidget`.
- [x] Bổ sung caching card-hash để tránh tính toán lại không cần thiết (đảm bảo Zero UI Lag).
- [x] Viết unit test suite `tests/test_collaborative_analyzer.py` (4 tests).
- [x] Viết test UI integration trong `tests/test_multi_window.py`.
- [x] Chạy toàn bộ test suite dự án: 124/124 PASSED (100%).
- [x] Đồng bộ trạng thái và tài liệu `.ai/`.
