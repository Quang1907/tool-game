# MODULE MAP & KNOWLEDGE RETRIEVAL GUIDE — BINH 13 ANALYZER

Tài liệu này là bản đồ điều hướng chi tiết giúp AI xác định chính xác file cần đọc, API cần dùng, test cần chạy và những điều cấm kỵ khi thay đổi code.

---

## 1. PHÂN HỆ DOMAIN CORE (`app/core/`)

| Tiêu chí | Chi tiết |
|---|---|
| **Vai trò** | Nghiệp vụ thuần túy: biểu diễn quân bài, luật Mậu Binh, phân rã 36,036 thế bài, mô phỏng Monte Carlo, tối ưu EV. |
| **Files** | `card.py`, `evaluator.py`, `rules.py`, `solver.py`, `simulator.py`, `ev_optimizer.py`. |
| **Dependencies** | Chỉ phụ thuộc thư viện chuẩn Python và `numpy`. **Tuyệt đối cấm phụ thuộc GUI hay CV.** |
| **Public API chính** | - `Card(rank: Rank, suit: Suit)`<br>- `Hand(cards: List[Card])`<br>- `HandEvaluator.evaluate_front(cards: 3)`<br>- `HandEvaluator.evaluate_five(cards: 5)`<br>- `Solver.solve(hand: Hand) -> List[Arrangement]`<br>- `EVOptimizer.optimize(arrangements, unseen_cards)` |
| **Tài liệu liên quan** | `docs/ALGORITHM.md`, `.ai/GAME_RULES.md`, `.ai/modules/CORE_DOMAIN.md`. |
| **Tests liên quan** | `tests/test_card.py`, `tests/test_evaluator.py`, `tests/test_rules.py`, `tests/test_solver.py`, `tests/test_simulator.py`. |
| **Điều cần tránh** | - Không sửa logic so sánh tie-breaker mà không chạy toàn bộ test evaluator.<br>- Không được thay đổi công thức tính 36,036 splits.<br>- Không import `PySide6` hoặc `cv2` vào `app/core/`. |

---

## 2. PHÂN HỆ VISION PIPELINE (`app/vision/`)

| Tiêu chí | Chi tiết |
|---|---|
| **Vai trò** | Chụp màn hình macOS Retina, tiền xử lý ảnh, phát hiện vị trí lá bài ngẫu nhiên/xòe, nhận diện độc lập Rank và Suit, lưu trữ mẫu xác nhận. |
| **Files** | `screen_capture.py`, `image_preprocessor.py`, `card_detector.py`, `card_recognizer.py`, `card_reference_library.py`, `card_state.py`, `recognition_validator.py`, `roi_manager.py`, `window_manager.py`, `template_engine.py`. |
| **Dependencies** | `numpy`, `opencv-python` (`cv2`), `Pillow` (`PIL`), `app.core.card`, `app.database`. |
| **Public API chính** | - `CardDetector.detect_cards(table_image: np.ndarray) -> List[CardCrop]`<br>- `CardDetector.validate_crop(table_image, det) -> (crop_status, reason)`<br>- `CardRecognizer.recognize_crop(crop: CardCrop) -> DetectedCard`<br>- `CardReferenceLibrary.add_reference(image, card, source)`<br>- `CardReferenceLibrary.match_crop(...)`<br>- `RecognitionValidator.validate(detected_cards) -> ValidationReport` |
| **Tài liệu liên quan** | `docs/VISION_MODEL.md`, `.ai/modules/VISION_PIPELINE.md`. |
| **Tests liên quan** | `tests/test_vision.py`, `tests/test_card_detection_and_reference.py`, `tests/test_multi_window.py`. |
| **Điều cần tránh** | - **Tuyệt đối không dùng tọa độ ô cố định** để crop bài.<br>- Không được tự động đoán `KD` khi crop không có cấu trúc góc bài.<br>- Không lưu mẫu vào thư viện nếu chưa có xác nhận từ người dùng.<br>- Không bỏ qua candidate validation (tránh nhận diện avatar thành bài). |

---

## 3. PHÂN HỆ GIAO DIỆN NGƯỜI DÙNG (`app/ui/`)

| Tiêu chí | Chi tiết |
|---|---|
| **Vai trò** | Giao diện đồ họa macOS dark theme: 5 tab chính, hiển thị overlay nhận diện bài, zoom/pan ảnh, dialog sửa bài và quản trị ảnh mẫu. |
| **Files** | `main_window.py`, `styles.py`, `components/card_widget.py`, `components/card_edit_dialog.py`, `components/vision_widget.py`, `components/zoomable_viewer.py`, `components/vision_debug_dialog.py`, `components/multi_window_widget.py`, `components/solver_widget.py`, `components/simulator_widget.py`, `components/card_reference_manager.py`, `components/history_widget.py`. |
| **Dependencies** | `PySide6` (QtCore, QtGui, QtWidgets), `app.core`, `app.vision`, `app.services`, `app.database`. |
| **Public API chính** | - `MainWindow()`<br>- `CardEditDialog(detected_card, reference_library, parent)`<br>- `VisionDebugDialog(table_image, detected_cards, debug_info, reference_library)`<br>- `ZoomableImageViewer.set_image(bgr_image, detected_cards)` |
| **Tài liệu liên quan** | `.ai/modules/UI_PRESENTATION.md`. |
| **Tests liên quan** | `tests/test_ui.py`, `tests/test_card_detection_and_reference.py`. |
| **Điều cần tránh** | - **Tuyệt đối không chạy tính toán nặng (Solver, Monte Carlo, Capture) trên Main GUI Thread.**<br>- Khi tạo nút có kích thước nhỏ, phải ghi đè `padding: 0` để tránh bị clipping mất chữ như lỗi trước đây.<br>- Chọn Rank không được làm đổi Suit; chọn Suit không được làm đổi Rank. |

---

## 4. PHÂN HỆ APPLICATION SERVICES (`app/services/`)

| Tiêu chí | Chi tiết |
|---|---|
| **Vai trò** | Điều phối luồng nghiệp vụ giữa UI và Core/Vision, quản lý worker threads (`QThread`) và multi-window monitor. |
| **Files** | `analysis_service.py`, `simulation_service.py`, `vision_service.py`, `multi_window_service.py`. |
| **Dependencies** | `PySide6.QtCore` (`QThread`, `Signal`, `QObject`), `app.core`, `app.vision`, `app.database`. |
| **Public API chính** | - `AnalysisService.analyze_hand(cards)`<br>- `SimulationWorker(arrangements, unseen_cards, num_simulations, crn_seed)`<br>- `MultiWindowService.update_frame(full_frame)` |
| **Tài liệu liên quan** | `.ai/modules/SERVICES_ORCHESTRATION.md`. |
| **Tests liên quan** | `tests/test_integration.py`, `tests/test_multi_window.py`. |
| **Điều cần tránh** | - Không gọi trực tiếp GUI widget từ bên trong worker thread (chỉ dùng Signal để emit kết quả). |

---

## 5. PHÂN HỆ PERSISTENCE LAYER (`app/database/`)

| Tiêu chí | Chi tiết |
|---|---|
| **Vai trò** | Quản lý kết nối SQLite cục bộ, khởi tạo schema bảng, thực hiện CRUD phiên chơi và ảnh mẫu bài. |
| **Files** | `db.py`, `repository.py`. |
| **Dependencies** | `sqlite3` (chuẩn Python), `pathlib.Path`. |
| **Public API chính** | - `DatabaseManager.get_connection()`<br>- `HistoryRepository.save_session(...)`<br>- `HistoryRepository.get_session_by_id(...)` |
| **Tài liệu liên quan** | `DATABASE.md`, `.ai/modules/DATABASE_PERSISTENCE.md`. |
| **Tests liên quan** | `tests/test_database.py`. |
| **Điều cần tránh** | - Không viết câu lệnh raw SQL trong UI components hay Core domain. Mọi truy vấn phải đi qua repository. |

---

## 6. PHÂN HỆ TỰ ĐỘNG HÓA & QUẢN LÝ CỬ CHỈ (`app/automation/`)

| Tiêu chí | Chi tiết |
|---|---|
| **Vai trò** | Quản lý 13 ô bài ($[0.0, 1.0]$ tương đối), lưu trữ và điều phối cử chỉ kéo thả ($156$ cặp có hướng), bộ chọn mẫu ngẫu nhiên (weighted random), bộ sinh đường cong Cubic Bézier tự nhiên, lập lịch hoán đổi tối thiểu (Min Swaps MovePlanner), ghi macro trực tiếp 60Hz, điều khiển chuột macOS native `CoreGraphics` qua `ctypes` và worker chạy ngầm trên `QThread`. |
| **Files** | `gesture_models.py`, `mouse_controller.py`, `gesture_selector.py`, `move_planner.py`, `macro_recorder.py`, `gesture_manager.py`. |
| **Dependencies** | Thư viện chuẩn Python (`ctypes`, `dataclasses`, `json`, `math`, `random`, `uuid`), `PySide6.QtCore` (`QThread`, `Signal`, `QObject`), `PySide6.QtGui` (`QCursor`), `app.core.card`, `app.database`. |
| **Public API chính** | - `MouseController.drag_and_drop_relative(sample, win_bounds, speed_factor)`<br>- `GestureSelector.select_sample(from_slot, to_slot) -> GestureSample`<br>- `GestureSelector.generate_natural_bezier_sample(...) -> GestureSample`<br>- `MovePlanner.plan_moves(current_cards, target_arrangement) -> MovePlan`<br>- `MacroRecorder.start_recording(...) / stop_recording() -> GestureSample`<br>- `GestureManager.execute_auto_binh(...)`<br>- `AutoBinhWorker(manager, current_cards, solution, win_bounds, config)` |
| **Tài liệu liên quan** | `.ai/state/ACTIVE_TASK.md`, `CHANGELOG.md`. |
| **Tests liên quan** | `tests/test_auto_binh.py`. |
| **Điều cần tránh** | - **Tuyệt đối không chạy kéo chuột hay mô phỏng trên Main GUI Thread** (bắt buộc dùng `AutoBinhWorker(QThread)`).<br>- Không dùng tọa độ pixel tuyệt đối để lưu cử chỉ (phải dùng tọa độ tương đối $[0.0, 1.0]$ theo kích thước cửa sổ game).<br>- Luôn kiểm tra chốt an toàn (failsafe khi chuột chạm góc $(0, 0)$). |

---

## 7. HƯỚNG DẪN TRUY XUẤT THEO NHIỆM VỤ (TASK-BASED NAVIGATION)

| Nếu nhiệm vụ của bạn liên quan đến... | Hãy đọc các file này trước: | Và chạy test này để kiểm tra: |
|---|---|---|
| Sửa lỗi nhận diện quân bài, crop sai, avatar false positive | `app/vision/card_detector.py`<br>`app/vision/card_recognizer.py` | `pytest tests/test_card_detection_and_reference.py -v` |
| Sửa nút bấm, hiển thị dialog sửa bài, visual debug | `app/ui/components/card_edit_dialog.py`<br>`app/ui/components/vision_debug_dialog.py` | `pytest tests/test_ui.py -v` |
| Sửa thư viện ảnh mẫu, nạp/xóa/đối chiếu ảnh mẫu | `app/vision/card_reference_library.py`<br>`app/ui/components/card_reference_manager.py` | `pytest tests/test_card_detection_and_reference.py -v` |
| Sửa nhận diện 3 cửa sổ bàn chơi, ROI, Retina 2x | `app/vision/roi_manager.py`<br>`app/services/multi_window_service.py` | `pytest tests/test_multi_window.py -v` |
| Sửa thuật toán xếp chi, luật Mậu Binh, kiểm tra Foul | `app/core/evaluator.py`<br>`app/core/solver.py`<br>`app/core/rules.py` | `pytest tests/test_evaluator.py tests/test_solver.py -v` |
| Sửa tính toán EV, Monte Carlo, tốc độ mô phỏng | `app/core/simulator.py`<br>`app/core/ev_optimizer.py` | `pytest tests/test_simulator.py -v` |
| Sửa cử chỉ kéo chuột, ghi macro, sinh Bézier, tự động binh bài | `app/automation/gesture_manager.py`<br>`app/automation/move_planner.py`<br>`app/ui/components/gesture_widget.py` | `pytest tests/test_auto_binh.py -v` |

