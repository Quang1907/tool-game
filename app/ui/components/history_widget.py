"""History view showing past analysis sessions and export options."""

from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Any, Dict, List
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.repository import AnalysisRepository


class HistoryWidget(QWidget):
    """Component displaying saved analysis sessions with CSV/JSON export."""

    session_loaded = Signal(dict)

    def __init__(
        self,
        repository: AnalysisRepository | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository or AnalysisRepository()
        self.sessions: List[Dict[str, Any]] = []
        self._init_ui()
        self.refresh()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Actions
        top_layout = QHBoxLayout()
        lbl_title = QLabel("Lịch sử phân tích:")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 700;")
        top_layout.addWidget(lbl_title)

        top_layout.addStretch()

        btn_refresh = QPushButton("Làm mới", objectName="SecondaryBtn")
        btn_refresh.clicked.connect(self.refresh)
        top_layout.addWidget(btn_refresh)

        btn_export_json = QPushButton("Xuất JSON", objectName="SecondaryBtn")
        btn_export_json.clicked.connect(self._export_json)
        top_layout.addWidget(btn_export_json)

        btn_export_csv = QPushButton("Xuất CSV", objectName="SecondaryBtn")
        btn_export_csv.clicked.connect(self._export_csv)
        top_layout.addWidget(btn_export_csv)

        btn_delete = QPushButton("Xóa mục chọn", objectName="DangerBtn")
        btn_delete.clicked.connect(self._delete_selected)
        top_layout.addWidget(btn_delete)

        main_layout.addLayout(top_layout)

        # Sessions Table
        self.table_sessions = QTableWidget()
        self.table_sessions.setColumnCount(6)
        self.table_sessions.setHorizontalHeaderLabels([
            "ID Phiên", "Thời gian", "Nguồn nhập", "13 Lá bài", "Trạng thái", "EV Cao nhất"
        ])
        self.table_sessions.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_sessions.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_sessions.setSelectionMode(QTableWidget.SingleSelection)
        main_layout.addWidget(self.table_sessions)

    def refresh(self) -> None:
        """Reloads sessions from the database."""
        self.sessions = self.repository.list_recent_sessions(limit=100)
        self.table_sessions.setRowCount(len(self.sessions))

        for row, s in enumerate(self.sessions):
            self.table_sessions.setItem(row, 0, QTableWidgetItem(s["id"][:8] + "..."))
            self.table_sessions.setItem(row, 1, QTableWidgetItem(str(s["created_at"])))
            self.table_sessions.setItem(row, 2, QTableWidgetItem(s["input_method"]))

            # Parse cards JSON for clean display
            try:
                cards_list = json.loads(s["raw_input_cards"])
                cards_str = " ".join(cards_list)
            except Exception:
                cards_str = str(s["raw_input_cards"])
            self.table_sessions.setItem(row, 3, QTableWidgetItem(cards_str))

            self.table_sessions.setItem(row, 4, QTableWidgetItem(s["status"]))

            ev_str = f"{s['top_ev']:+.2f}" if s["top_ev"] is not None else "--"
            ev_item = QTableWidgetItem(ev_str)
            ev_item.setTextAlignment(Qt.AlignCenter)
            self.table_sessions.setItem(row, 5, ev_item)

    def _delete_selected(self) -> None:
        selected_rows = self.table_sessions.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn phiên phân tích cần xóa.")
            return

        row = selected_rows[0].row()
        session_id = self.sessions[row]["id"]

        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            "Bạn có chắc muốn xóa vĩnh viễn phiên phân tích này?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self.repository.delete_session(session_id)
            self.refresh()

    def _export_json(self) -> None:
        if not self.sessions:
            QMessageBox.information(self, "Thông báo", "Không có dữ liệu lịch sử để xuất.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Xuất lịch sử JSON", "history.json", "JSON (*.json)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.sessions, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Thành công", f"Đã xuất dữ liệu ra file:\n{file_path}")

    def _export_csv(self) -> None:
        if not self.sessions:
            QMessageBox.information(self, "Thông báo", "Không có dữ liệu lịch sử để xuất.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Xuất lịch sử CSV", "history.csv", "CSV (*.csv)")
        if file_path:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "created_at", "input_method", "raw_cards", "status", "top_ev"])
                for s in self.sessions:
                    writer.writerow([
                        s["id"], s["created_at"], s["input_method"],
                        s["raw_input_cards"], s["status"], s["top_ev"]
                    ])
            QMessageBox.information(self, "Thành công", f"Đã xuất dữ liệu ra file:\n{file_path}")
