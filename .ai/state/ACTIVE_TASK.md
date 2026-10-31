# ACTIVE TASK — BINH 13 ANALYZER

**Nhiệm vụ hiện tại:** Nâng cấp cơ chế điều khiển chuột mượt mà (smooth glide), nhấp chọn bài kích hoạt focus canvas, luân phiên tự động binh bài cả 3 bàn (Tab 6), và triệt tiêu popup thông báo gây gián đoạn.  
**Người yêu cầu:** User / Product Owner  
**Trạng thái nhiệm vụ:** `COMPLETED` (Đã hoàn thiện 100%, 146/146 tests PASSED)

---

## 1. CÁC NÂNG CẤP ĐÃ HOÀN TẤT
1. **Di chuyển chuột mượt mà (`smooth_move_to`):** Lấy vị trí con trỏ chuột hiện tại từ `QCursor.pos()`, nội suy mượt mà qua hàm cubic ease-in-out ($3t^2 - 2t^3$) từ vị trí trỏ chuột đến tâm quân bài đầu tiên, không nhảy tọa độ đột ngột.
2. **Nhấp chọn bài & focus canvas (`click_to_select`):** Thực hiện một cú click ngắn (45ms) tại tâm lá bài trước khi nhấn giữ kéo thả, vừa kích hoạt focus cửa sổ game vừa chọn bài, triệt tiêu lỗi trượt chuột trên HTML5 Canvas.
3. **Luân phiên tự động xếp cả 3 bàn:** Bổ sung nút `"⚡ Binh bài cả 3 bàn (Luân phiên)"` trên Tab 6. Tự động kiểm tra các bàn sẵn sàng, xếp lần lượt Bàn 1 $\rightarrow$ nghỉ 400ms $\rightarrow$ Bàn 2 $\rightarrow$ nghỉ 400ms $\rightarrow$ Bàn 3.
4. **Triệt tiêu thông báo Popup (`QMessageBox`):** Không còn hiển thị popup "Hoàn tất qua bao nhiêu bước", chuyển toàn bộ trạng thái trực tiếp lên nhãn `lbl_status` của từng bàn chơi.
5. **Đảm bảo khung giao diện thu nhỏ & mở tab:** Liên tục cập nhật kích thước cửa sổ game thời gian thực qua WindowServer và tự động đưa tab trình duyệt lên frontmost khi kích hoạt.
6. **Kiểm thử tự động:** Đạt 146/146 tests PASSED (100%) trong 30 giây.

