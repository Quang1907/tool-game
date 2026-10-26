# MODULE DOCUMENTATION: PERSISTENCE LAYER (`app/database/`)

---

## 1. MỤC ĐÍCH & PHẠM VI

Phân hệ Database Persistence chịu trách nhiệm lưu trữ dữ liệu cục bộ an toàn, tin cậy cho ứng dụng bằng SQLite 3:
1. Lưu trữ phiên phân tích bài (`sessions`): thời gian, chế độ, 13 lá bài đầu vào, thế bài người dùng lựa chọn.
2. Lưu trữ bảng xếp hạng các thế bài (`arrangements`) và kết quả mô phỏng Monte Carlo (`simulation_results`).
3. Lưu trữ thư viện ảnh mẫu đã xác nhận (`card_references`): mã bài, chất, hạng, đường dẫn ảnh crop, trạng thái xác nhận.

---

## 2. CÁC TẬP TIN NGUỒN VÀ CLASS CHÍNH

### 2.1. `db.py`
- `DatabaseManager`: Quản lý kết nối cơ sở dữ liệu SQLite.
  - Hỗ trợ chế độ file database cục bộ (`~/.binh13_analyzer/data.db`) hoặc in-memory (`:memory:`) cho testing.
  - Tự động kích hoạt Foreign Keys (`PRAGMA foreign_keys = ON;`) và WAL mode (`PRAGMA journal_mode = WAL;`) để tối ưu tốc độ đọc ghi đồng thời trên macOS.
  - Tự động chạy migration tạo các bảng nếu chưa tồn tại.

### 2.2. `repository.py`
- `HistoryRepository`: Triển khai Repository Pattern để tách biệt hoàn toàn tầng dữ liệu khỏi UI và Core.
  - `save_session(hand, arrangements, selected_idx, ev_result) -> int`: Lưu trọn vẹn một phiên phân tích bài kèm kết quả EV.
  - `get_recent_sessions(limit=50) -> List[SessionRecord]`: Truy vấn danh sách các ván bài gần nhất.
  - `get_session_details(session_id) -> Optional[SessionDetails]`: Lấy chi tiết toàn bộ thế bài và kết quả mô phỏng của một phiên.
  - `delete_session(session_id) -> bool`: Xóa phiên và dữ liệu liên quan qua cascade foreign keys.

---

## 3. CƠ SỞ DỮ LIỆU SCHEMA

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hand_input TEXT NOT NULL,
    selected_arrangement_id INTEGER,
    game_mode TEXT DEFAULT 'STANDARD',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS arrangements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    front_hand TEXT NOT NULL,
    middle_hand TEXT NOT NULL,
    back_hand TEXT NOT NULL,
    heuristic_score REAL DEFAULT 0.0,
    is_foul BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS simulation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arrangement_id INTEGER NOT NULL REFERENCES arrangements(id) ON DELETE CASCADE,
    num_simulations INTEGER NOT NULL,
    num_opponents INTEGER NOT NULL,
    expected_value REAL NOT NULL,
    std_dev REAL NOT NULL,
    win_rate REAL NOT NULL,
    tie_rate REAL NOT NULL,
    loss_rate REAL NOT NULL,
    scoop_rate REAL NOT NULL,
    ci_lower REAL NOT NULL,
    ci_upper REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS card_references (
    id TEXT PRIMARY KEY,
    card_code TEXT NOT NULL,
    rank TEXT NOT NULL,
    suit TEXT NOT NULL,
    image_path TEXT NOT NULL,
    source TEXT DEFAULT 'user_confirmed',
    confirmed INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. QUY TẮC CẦN TUÂN THỦ

1. **Tuyệt đối cấm viết câu lệnh SQL trực tiếp trong UI hay Core Domain.**
2. **Không sửa đổi schema làm mất dữ liệu cũ:** Bất kỳ sự thay đổi schema nào đều phải cung cấp câu lệnh `ALTER TABLE` hoặc migration an toàn.
