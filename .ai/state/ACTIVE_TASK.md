# ACTIVE TASK — BINH 13 ANALYZER

**Nhiệm vụ hiện tại:** Xây dựng Tab số 7 ("7. Tự động binh bài & Cử chỉ"): Lưu trữ và quản lý toàn bộ thao tác kéo thả giữa 13 vị trí quân bài ($13 \times 12 = 156$ cặp có hướng), hỗ trợ ghi macro thực tế, tạo đường cong Bézier tự nhiên, bộ chọn mẫu ngẫu nhiên có trọng số, và tự động thực thi xếp bài trên cửa sổ game theo giải thuật tối ưu của Tab 6.  
**Người yêu cầu:** User / Product Owner  
**Trạng thái nhiệm vụ:** `COMPLETED` (Đã hoàn thành toàn diện Tab 7, tích hợp nút Auto-Binh trên Tab 6, kiểm thử 138/138 tests PASSED 100%)

---

## 1. MỤC TIÊU CỐT LÕI
1. **Quản lý 13 vị trí bài:** Lưu tọa độ tương đối $[0.0, 1.0]$ theo cửa sổ game cho 3 Chi (3 Chi Đầu, 5 Chi Giữa, 5 Chi Cuối).
2. **Quản lý 156 cặp vị trí có hướng ($13 \times 12$):** Mỗi cặp lưu nhiều mẫu thao tác (`GestureSample`) gồm đường đi trung gian, thời gian giữ/thả, trọng số, cờ đã kiểm tra (`is_verified`).
3. **Bộ chọn mẫu ngẫu nhiên (`GestureSelector`):** Chọn ngẫu nhiên có trọng số, tránh lặp liên tiếp, hỗ trợ sinh đường cong Bézier tự nhiên mượt mà nếu chưa có mẫu ghi macro.
4. **Lập lịch di chuyển bài tối ưu (`MovePlanner`):** Phân tích 13 quân bài hiện tại trên các ô và bộ bài tối ưu cần xếp $\rightarrow$ sinh chuỗi hoán đổi tối thiểu (Min Swaps).
5. **Điều khiển chuột tự động macOS (`MouseController`):** Sử dụng `CoreGraphics` qua `ctypes` native, chuyển đổi tọa độ tương đối sang màn hình thực, có chốt an toàn (failsafe).
6. **Giao diện Tab 7 (`GestureWidget`):** Ma trận 13x13 trực quan, thanh công cụ ghi macro, chỉnh sửa/nhân bản/xóa/test thử mẫu, sao lưu xuất/nhập JSON.
7. **Tích hợp Tab 6:** Nút "⚡ Tự Động Binh Bài" kích hoạt chạy ngầm trên `QThread` đảm bảo Zero UI Lag.
8. **Kiểm thử tự động:** Viết suite test đầy đủ trong `tests/test_auto_binh.py`.
