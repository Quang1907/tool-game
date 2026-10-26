# GAME RULES & SCORING SPECIFICATION — BINH 13 (MẬU BINH)

Tài liệu này chuẩn hóa toàn bộ luật chơi, phân cấp bài, cách tính điểm, quy tắc Binh Lủng và Mậu Binh Thắng Trắng được cài đặt trong `app/core/rules.py` và `app/core/evaluator.py`.

---

## 1. CẤU TRÚC BÀI VÀ CÁC CHI

Mỗi người chơi được chia **13 lá bài** từ bộ bài chuẩn 52 lá. Người chơi phải xếp thành 3 chi:
- **Chi Đầu (Front Hand):** 3 lá bài.
- **Chi Giữa (Middle Hand):** 5 lá bài.
- **Chi Cuối (Back Hand):** 5 lá bài.

### Quy Tắc Chống Binh Lủng (Foul Invariant)
Bắt buộc theo nguyên tắc sức mạnh giảm dần:
$$\text{Chi Cuối (Back)} \ge \text{Chi Giữa (Middle)} \ge \text{Chi Đầu (Front)}$$

- Nếu vi phạm điều kiện này (ví dụ Chi Giữa mạnh hơn Chi Cuối, hoặc Chi Đầu mạnh hơn Chi Giữa), thế bài bị coi là **Binh Lủng (Foul Hand)**.
- Người chơi bị xử Binh Lủng sẽ bị phạt thua sập tất cả các chi trước mọi đối thủ trên bàn (`foul_penalty_points = -12.0`).

---

## 2. THỨ BẬC TAY BÀI (HAND HIERARCHY)

### 2.1. Đối Với Chi 5 Lá (Chi Cuối và Chi Giữa)
Thứ bậc từ mạnh nhất đến yếu nhất:
1. **Thùng Phá Sảnh (Straight Flush):** 5 lá liên tiếp cùng chất (A-K-Q-J-10 cùng chất là Royal Flush).
2. **Tứ Quý (Four of a Kind):** 4 lá cùng giá trị + 1 lá rác.
3. **Cù Lũ (Full House):** 1 bộ ba + 1 đôi.
4. **Thùng (Flush):** 5 lá cùng chất (không liên tiếp).
5. **Sảnh (Straight):** 5 lá liên tiếp (không cùng chất). Cấu hình `LOWEST`: A-2-3-4-5 là sảnh nhỏ nhất (5-high).
6. **Sám Cô (Three of a Kind / Trips):** 3 lá cùng giá trị + 2 lá rác.
7. **Thú (Two Pair):** 2 đôi + 1 lá rác.
8. **Một Đôi (One Pair):** 1 đôi + 3 lá rác.
9. **Mậu Thầu (High Card):** Không có liên kết, so theo giá trị lá cao nhất.

### 2.2. Đối Với Chi 3 Lá (Chi Đầu)
Chi Đầu chỉ có 3 lá bài, do đó **không có Sảnh hoặc Thùng**:
1. **Sám Cô (Three of a Kind):** 3 lá cùng giá trị (Sám A là lớn nhất).
2. **Một Đôi (One Pair):** 1 đôi + 1 lá rác.
3. **Mậu Thầu (High Card):** 3 lá rác không đôi, so sánh từ lá lớn nhất đến lá nhỏ nhất.

---

## 3. CƠ CHẾ SO BÀI VÀ TÍNH ĐIỂM (HEAD-TO-HEAD SCORING)

Mỗi người chơi so sánh độc lập với từng đối thủ tại bàn chơi (từ 2 đến 4 người chơi):

| Tình huống so sánh | Điểm cơ bản | Điểm thưởng / phạt |
|---|---|---|
| Thắng 1 chi | $+1$ điểm | - |
| Hòa 1 chi | $0$ điểm | - |
| Thua 1 chi | $-1$ điểm | - |
| **Bắt sập 1 đối thủ (Scoop 3 chi)** | $+3$ điểm | Thưởng thêm $+3$ điểm (Tổng $+6$) |
| **Bị sập 1 đối thủ (Scooped 3 chi)** | $-3$ điểm | Bị phạt thêm $-3$ điểm (Tổng $-6$) |
| **Bắt sập làng (Scoop All Players)** | Nhân đôi điểm | Thưởng sập làng $+6$ điểm |
| **Binh lủng (Foul Hand)** | $-3 \times \text{Số đối thủ}$ | Phạt tối thiểu $-12$ điểm |

---

## 4. MẬU BINH THẮNG TRẮNG (SPECIAL INSTANT-WIN HANDS)

Nếu 13 lá bài rơi vào các trường hợp đặc biệt sau, người chơi tới trắng ngay lập tức mà không cần so từng chi:

| Tay bài đặc biệt | Tên tiếng Việt | Điều kiện nhận diện | Điểm thưởng |
|---|---|---|---|
| **DRAGON** | Sảnh Rồng | 13 lá liên tiếp từ 2 đến A (`2-3-4-5-6-7-8-9-10-J-Q-K-A`) | $+26$ điểm |
| **SAME_COLOR** | Đồng Hoa (Toàn đỏ / Toàn đen) | 13 lá toàn bộ màu Đỏ (♦♥) hoặc toàn bộ màu Đen (♠♣) | $+20$ điểm |
| **SIX_PAIRS** | Lục Phé Bôn | 13 lá có đúng 6 đôi + 1 lá lẻ | $+12$ điểm |
| **THREE_STRAIGHTS** | Ba Sảnh | Cả 3 chi đều tạo thành Sảnh hợp lệ | $+12$ điểm |
| **THREE_FLUSHES** | Ba Thùng | Cả 3 chi đều tạo thành Thùng hợp lệ | $+12$ điểm |
