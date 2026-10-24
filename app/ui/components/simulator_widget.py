"""Monte Carlo Simulation & EV Optimization UI Component."""

from __future__ import annotations
from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.ev_optimizer import OptimizedArrangement
from app.core.simulator import SimulationStats
from app.core.solver import HandArrangement


class SimulatorWidget(QWidget):
    """Monte Carlo execution panel with real-time progress and detailed statistics."""

    start_simulation = Signal(int, int, int)  # candidates, rounds, opponents
    cancel_simulation = Signal()
    arrangement_selected = Signal(object)     # When user selects row in results table

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.optimized_results: List[OptimizedArrangement] = []
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Simulation Configuration Box
        box_config = QGroupBox("Cấu hình mô phỏng Monte Carlo")
        layout_cfg = QGridLayout(box_config)

        layout_cfg.addWidget(QLabel("Số đối thủ:"), 0, 0)
        self.spin_opponents = QSpinBox()
        self.spin_opponents.setRange(1, 3)
        self.spin_opponents.setValue(3)
        layout_cfg.addWidget(self.spin_opponents, 0, 1)

        layout_cfg.addWidget(QLabel("Số kịch bản đối thủ:"), 0, 2)
        self.combo_rounds = QComboBox()
        self.combo_rounds.addItems(["100", "300", "500", "1,000", "5,000"])
        self.combo_rounds.setCurrentIndex(1)  # 300 by default for speed & accuracy
        layout_cfg.addWidget(self.combo_rounds, 0, 3)

        layout_cfg.addWidget(QLabel("Số phương án tối ưu:"), 1, 0)
        self.spin_candidates = QSpinBox()
        self.spin_candidates.setRange(3, 30)
        self.spin_candidates.setValue(10)
        layout_cfg.addWidget(self.spin_candidates, 1, 1)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Chạy tối ưu EV (Monte Carlo)")
        self.btn_run.setFixedHeight(36)
        self.btn_run.clicked.connect(self._on_run_clicked)
        btn_layout.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("Dừng", objectName="DangerBtn")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        btn_layout.addWidget(self.btn_cancel)

        layout_cfg.addLayout(btn_layout, 1, 2, 1, 2)
        main_layout.addWidget(box_config)

        # Progress Section
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        self.lbl_progress_status = QLabel("Sẵn sàng chạy mô phỏng.")
        self.lbl_progress_status.setStyleSheet("color: #8E8E93;")
        main_layout.addWidget(self.lbl_progress_status)

        # KPI Metrics Cards
        kpi_layout = QHBoxLayout()
        self.lbl_ev_metric = QLabel("EV: --")
        self.lbl_ev_metric.setStyleSheet(
            "background-color: #2C2C2E; padding: 12px; border-radius: 8px; "
            "font-size: 20px; font-weight: 700; color: #30D158;"
        )
        self.lbl_ev_metric.setAlignment(Qt.AlignCenter)
        kpi_layout.addWidget(self.lbl_ev_metric)

        self.lbl_win_metric = QLabel("Tỷ lệ thắng: --")
        self.lbl_win_metric.setStyleSheet(
            "background-color: #2C2C2E; padding: 12px; border-radius: 8px; "
            "font-size: 16px; font-weight: 600; color: #0A84FF;"
        )
        self.lbl_win_metric.setAlignment(Qt.AlignCenter)
        kpi_layout.addWidget(self.lbl_win_metric)

        self.lbl_ci_metric = QLabel("Khoảng tin cậy 95%: --")
        self.lbl_ci_metric.setStyleSheet(
            "background-color: #2C2C2E; padding: 12px; border-radius: 8px; "
            "font-size: 14px; font-weight: 500; color: #FF9F0A;"
        )
        self.lbl_ci_metric.setAlignment(Qt.AlignCenter)
        kpi_layout.addWidget(self.lbl_ci_metric)

        main_layout.addLayout(kpi_layout)

        # Results Table
        lbl_table_header = QLabel("Bảng xếp hạng phương án theo Expected Value (EV):")
        lbl_table_header.setStyleSheet("font-weight: 700; margin-top: 6px;")
        main_layout.addWidget(lbl_table_header)

        self.table_results = QTableWidget()
        self.table_results.setColumnCount(8)
        self.table_results.setHorizontalHeaderLabels([
            "Hạng", "Chi Đầu", "Chi Giữa", "Chi Cuối", "EV Điểm", "Thắng %", "Hòa %", "Thua %"
        ])
        self.table_results.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_results.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_results.setSelectionMode(QTableWidget.SingleSelection)
        self.table_results.itemSelectionChanged.connect(self._on_table_selection_changed)
        main_layout.addWidget(self.table_results)

    def _on_run_clicked(self) -> None:
        rounds_str = self.combo_rounds.currentText().replace(",", "")
        num_rounds = int(rounds_str)
        num_opponents = self.spin_opponents.value()
        num_candidates = self.spin_candidates.value()

        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.lbl_progress_status.setText("Bắt đầu mô phỏng...")

        self.start_simulation.emit(num_candidates, num_rounds, num_opponents)

    def _on_cancel_clicked(self) -> None:
        self.cancel_simulation.emit()
        self.lbl_progress_status.setText("Đang dừng mô phỏng...")
        self.btn_cancel.setEnabled(False)

    def update_progress(self, current: int, total: int, message: str) -> None:
        self.progress_bar.setValue(current)
        self.lbl_progress_status.setText(message)

    def set_results(self, results: List[OptimizedArrangement]) -> None:
        self.optimized_results = results
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setValue(100)
        self.lbl_progress_status.setText(f"Đã hoàn thành tối ưu {len(results)} phương án.")

        if not results:
            self.table_results.setRowCount(0)
            self.lbl_ev_metric.setText("EV: --")
            self.lbl_win_metric.setText("Tỷ lệ thắng: --")
            self.lbl_ci_metric.setText("Khoảng tin cậy 95%: --")
            return

        # Update top KPI badge
        best = results[0]
        ev_val = best.stats.expected_value
        ev_color = "#30D158" if ev_val >= 0 else "#FF453A"
        self.lbl_ev_metric.setText(f"EV: {ev_val:+.2f} điểm/ván")
        self.lbl_ev_metric.setStyleSheet(
            f"background-color: #2C2C2E; padding: 12px; border-radius: 8px; "
            f"font-size: 20px; font-weight: 700; color: {ev_color};"
        )
        self.lbl_win_metric.setText(f"Tỷ lệ thắng: {best.stats.win_rate*100:.1f}%")
        self.lbl_ci_metric.setText(
            f"95% CI: [{best.stats.ci_95_lower:+.2f}, {best.stats.ci_95_upper:+.2f}]"
        )

        # Populate Table
        self.table_results.setRowCount(len(results))
        for row, opt in enumerate(results):
            arr = opt.arrangement
            stats = opt.stats

            self.table_results.setItem(row, 0, QTableWidgetItem(f"#{opt.rank}"))
            self.table_results.setItem(row, 1, QTableWidgetItem(arr.front_eval.description))
            self.table_results.setItem(row, 2, QTableWidgetItem(arr.middle_eval.description))
            self.table_results.setItem(row, 3, QTableWidgetItem(arr.back_eval.description))

            ev_item = QTableWidgetItem(f"{stats.expected_value:+.2f}")
            ev_item.setTextAlignment(Qt.AlignCenter)
            self.table_results.setItem(row, 4, ev_item)

            win_item = QTableWidgetItem(f"{stats.win_rate*100:.1f}%")
            win_item.setTextAlignment(Qt.AlignCenter)
            self.table_results.setItem(row, 5, win_item)

            tie_item = QTableWidgetItem(f"{stats.tie_rate*100:.1f}%")
            tie_item.setTextAlignment(Qt.AlignCenter)
            self.table_results.setItem(row, 6, tie_item)

            loss_item = QTableWidgetItem(f"{stats.loss_rate*100:.1f}%")
            loss_item.setTextAlignment(Qt.AlignCenter)
            self.table_results.setItem(row, 7, loss_item)

        self.table_results.selectRow(0)

    def _on_table_selection_changed(self) -> None:
        selected_rows = self.table_results.selectionModel().selectedRows()
        if selected_rows and self.optimized_results:
            row = selected_rows[0].row()
            if 0 <= row < len(self.optimized_results):
                opt = self.optimized_results[row]
                self.arrangement_selected.emit(opt.arrangement)
