"""Main Application Window for Binh 13 Analyzer on macOS."""

from __future__ import annotations
import time
from typing import List, Optional
from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.card import Card
from app.core.rules import RuleConfig
from app.core.solver import HandArrangement
from app.database.repository import AnalysisRepository
from app.services.analysis_service import AnalysisService
from app.services.simulation_service import SimulationWorker
from app.ui.components.card_selector import CardSelectorWidget
from app.ui.components.history_widget import HistoryWidget
from app.ui.components.simulator_widget import SimulatorWidget
from app.ui.components.solver_widget import SolverWidget
from app.ui.components.vision_widget import VisionWidget
from app.ui.components.multi_window_widget import MultiWindowWidget
from app.ui.styles import MACOS_DARK_THEME


class MainWindow(QMainWindow):
    """Primary macOS application window integrating input, vision, solver, simulator, and history."""

    def __init__(self, config_path: str = "config/default_rules.json") -> None:
        super().__init__()
        self.setWindowTitle("Binh 13 Analyzer — macOS Professional Edition")
        self.resize(1080, 760)
        self.setMinimumSize(920, 640)

        # Initialize Services
        self.rules_config = RuleConfig.load_from_file(config_path)
        self.repository = AnalysisRepository()
        self.service = AnalysisService(
            rules_config=self.rules_config,
            repository=self.repository,
        )

        # State
        self.current_cards: List[Card] = []
        self.current_session_id: Optional[str] = None
        self.current_arrangements: List[HandArrangement] = []
        self._sim_thread: Optional[QThread] = None
        self._sim_worker: Optional[SimulationWorker] = None

        self._init_ui()
        self.setStyleSheet(MACOS_DARK_THEME)

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # 1. Manual Input Tab
        self.tab_selector = CardSelectorWidget()
        self.tab_selector.confirmed.connect(self._on_cards_confirmed_manual)
        self.tabs.addTab(self.tab_selector, "1. Nhập bài thủ công")

        # 2. Vision Screen Capture Tab
        self.tab_vision = VisionWidget()
        self.tab_vision.cards_confirmed.connect(self._on_cards_confirmed_vision)
        self.tabs.addTab(self.tab_vision, "2. Quét màn hình CV")

        # 3. Solver Tab
        self.tab_solver = SolverWidget()
        self.tab_solver.strategy_changed.connect(self._on_strategy_changed)
        self.tabs.addTab(self.tab_solver, "3. Xếp bài & Chiến thuật")

        # 4. Simulator Tab
        self.tab_simulator = SimulatorWidget()
        self.tab_simulator.start_simulation.connect(self._start_monte_carlo)
        self.tab_simulator.cancel_simulation.connect(self._cancel_monte_carlo)
        self.tab_simulator.arrangement_selected.connect(self._on_simulation_arrangement_selected)
        self.tabs.addTab(self.tab_simulator, "4. Mô phỏng Monte Carlo & EV")

        # 5. History Tab
        self.tab_history = HistoryWidget(repository=self.repository)
        self.tabs.addTab(self.tab_history, "5. Lịch sử phân tích")

        # 6. Multi-Window Game Bot Tab
        self.tab_multi_bot = MultiWindowWidget(
            detector=self.tab_vision.detector,
            recognizer=self.tab_vision.recognizer,
            reference_library=self.tab_vision.reference_library,
        )
        self.tabs.addTab(self.tab_multi_bot, "6. Bot 3 Cửa Sổ")

        main_layout.addWidget(self.tabs)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Sẵn sàng. Hãy chọn 13 lá bài để bắt đầu.")

    def _on_cards_confirmed_manual(self, cards: List[Card]) -> None:
        self._process_confirmed_cards(cards, input_method="MANUAL")

    def _on_cards_confirmed_vision(self, cards: List[Card]) -> None:
        self._process_confirmed_cards(cards, input_method="SCREEN_CAPTURE")

    def _process_confirmed_cards(self, cards: List[Card], input_method: str = "MANUAL") -> None:
        self.current_cards = cards

        start_time = time.perf_counter()
        try:
            session_id, arrangements = self.service.solve_cards(
                cards=self.current_cards,
                strategy="BALANCED",
                max_results=50,
                input_method=input_method,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            self.current_session_id = session_id
            self.current_arrangements = arrangements

            # Update Solver UI
            self.tab_solver.set_arrangements(arrangements)
            self.tab_history.refresh()

            # Switch to Solver tab
            self.tabs.setCurrentIndex(2)

            self.status_bar.showMessage(
                f"Đã duyệt 36,036 tổ hợp trong {elapsed_ms:.1f}ms • Tìm thấy {len(arrangements)} phương án hợp lệ."
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi phân tích bài", str(e))

    def _on_strategy_changed(self, strategy: str) -> None:
        if not self.current_cards:
            return

        # Re-solve with updated strategy
        arrangements = self.service.solver.solve(self.current_cards, strategy=strategy, max_results=50)
        self.current_arrangements = arrangements
        self.tab_solver.set_arrangements(arrangements)
        self.status_bar.showMessage(f"Đã cập nhật chiến lược xếp bài: {strategy}.")

    def _start_monte_carlo(self, num_candidates: int, num_rounds: int, num_opponents: int) -> None:
        if not self.current_cards:
            QMessageBox.warning(self, "Chưa có bài", "Vui lòng nhập và xác nhận 13 lá bài trước.")
            self.tab_simulator.btn_run.setEnabled(True)
            self.tab_simulator.btn_cancel.setEnabled(False)
            return

        self.status_bar.showMessage(f"Đang chạy mô phỏng {num_rounds} kịch bản đối thủ bằng CRN...")

        # Setup background QThread worker
        self._sim_thread = QThread()
        self._sim_worker = SimulationWorker(
            analysis_service=self.service,
            cards=self.current_cards,
            num_candidates=num_candidates,
            num_scenarios=num_rounds,
            num_opponents=num_opponents,
        )
        self._sim_worker.moveToThread(self._sim_thread)

        self._sim_thread.started.connect(self._sim_worker.run)
        self._sim_worker.progress.connect(self.tab_simulator.update_progress)
        self._sim_worker.finished.connect(self._on_simulation_finished)
        self._sim_worker.error.connect(self._on_simulation_error)

        self._sim_thread.start()

    def _cancel_monte_carlo(self) -> None:
        if self._sim_worker:
            self._sim_worker.cancel()
            self.status_bar.showMessage("Đang dừng mô phỏng...")

    def _on_simulation_finished(self, results: list) -> None:
        if self._sim_thread and self._sim_thread.isRunning():
            self._sim_thread.quit()
            self._sim_thread.wait()

        self.tab_simulator.set_results(results)
        self.status_bar.showMessage("Mô phỏng Monte Carlo hoàn thành!")

        # Record simulation results in database if session exists
        if self.current_session_id and results:
            best = results[0]
            try:
                import json
                self.repository.record_simulation_result(
                    session_id=self.current_session_id,
                    stats=best.stats,
                    num_opponents=3,
                    rules_json=json.dumps(self.rules_config.to_dict()),
                )
                self.tab_history.refresh()
            except Exception as e:
                print(f"[History] Auto-save simulation error: {e}")

    def _on_simulation_error(self, err_msg: str) -> None:
        if self._sim_thread and self._sim_thread.isRunning():
            self._sim_thread.quit()
            self._sim_thread.wait()

        self.tab_simulator.btn_run.setEnabled(True)
        self.tab_simulator.btn_cancel.setEnabled(False)
        QMessageBox.critical(self, "Lỗi mô phỏng", err_msg)
        self.status_bar.showMessage("Lỗi trong quá trình mô phỏng.")

    def _on_simulation_arrangement_selected(self, arrangement: HandArrangement) -> None:
        # Display selected arrangement in SolverWidget
        self.tab_solver.set_arrangements([arrangement])
