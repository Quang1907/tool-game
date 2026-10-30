"""Tab 7 UI: 156-Pair Gesture Mapper, Guided Macro Recorder Wizard, and Auto-Binh Manager."""

from __future__ import annotations
import json
import time
from typing import Callable, Dict, List, Optional, Tuple

import cv2

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.automation.gesture_manager import GestureManager
from app.automation.gesture_models import CardSlot, GestureConfig, GesturePoint, GestureSample
from app.automation.macro_recorder import MacroRecorder
from app.automation.mouse_controller import MouseController
from app.vision.screen_capture import ScreenCapture
from app.vision.window_manager import WindowItem, WindowManager


class CardSlotBox(QFrame):
    """Visual card widget representing one of the 13 poker card slots."""
    clicked = Signal(int)

    def __init__(self, slot_number: int, name: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.slot_number = slot_number
        self.slot_name = name
        self.rel_coords = (0.5, 0.5)
        self.recorded_count = 0
        self.is_source = False
        self.is_target = False

        self.setFixedSize(110, 115)
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()
        self.update_style()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        # Slot number badge
        self.lbl_num = QLabel(str(self.slot_number))
        self.lbl_num.setAlignment(Qt.AlignCenter)
        self.lbl_num.setStyleSheet("font-size: 24px; font-weight: 900; color: #FFFFFF;")
        layout.addWidget(self.lbl_num)

        # Slot name (Chi Đầu 1, etc.)
        self.lbl_name = QLabel(self.slot_name)
        self.lbl_name.setAlignment(Qt.AlignCenter)
        self.lbl_name.setStyleSheet("font-size: 11px; font-weight: bold; color: #8E8E93;")
        layout.addWidget(self.lbl_name)

        # Coordinates info
        self.lbl_coords = QLabel("50%, 50%")
        self.lbl_coords.setAlignment(Qt.AlignCenter)
        self.lbl_coords.setStyleSheet("font-size: 10px; color: #636366;")
        layout.addWidget(self.lbl_coords)

        # Status Badge (e.g. 12/12 ✅ or 📍 NGUỒN or 🎯 ĐÍCH)
        self.lbl_status = QLabel("0/12 mẫu")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet(
            "font-size: 10px; font-weight: bold; padding: 2px 4px; border-radius: 4px; background: #2C2C2E; color: #AEAEB2;"
        )
        layout.addWidget(self.lbl_status)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.slot_number)
        super().mousePressEvent(event)

    def set_data(self, name: str, rx: float, ry: float, recorded_count: int) -> None:
        self.slot_name = name
        self.rel_coords = (rx, ry)
        self.recorded_count = recorded_count
        self.lbl_name.setText(name)
        self.lbl_coords.setText(f"{int(rx * 100)}%, {int(ry * 100)}%")
        self.update_style()

    def set_role(self, is_source: bool, is_target: bool) -> None:
        self.is_source = is_source
        self.is_target = is_target
        self.update_style()

    def update_style(self) -> None:
        if self.is_source:
            self.setStyleSheet(
                """
                QFrame {
                    background-color: #382A05;
                    border: 2px solid #FF9F0A;
                    border-radius: 10px;
                }
                """
            )
            self.lbl_num.setStyleSheet("font-size: 24px; font-weight: 900; color: #FFD60A;")
            self.lbl_status.setText("📍 NGUỒN (GIỮ)")
            self.lbl_status.setStyleSheet(
                "font-size: 10px; font-weight: bold; padding: 2px 4px; border-radius: 4px; background: #FF9F0A; color: #000000;"
            )
        elif self.is_target:
            self.setStyleSheet(
                """
                QFrame {
                    background-color: #0A3315;
                    border: 2px solid #30D158;
                    border-radius: 10px;
                }
                """
            )
            self.lbl_num.setStyleSheet("font-size: 24px; font-weight: 900; color: #30D158;")
            self.lbl_status.setText("🎯 ĐÍCH (THẢ)")
            self.lbl_status.setStyleSheet(
                "font-size: 10px; font-weight: bold; padding: 2px 4px; border-radius: 4px; background: #30D158; color: #000000;"
            )
        else:
            self.setStyleSheet(
                """
                QFrame {
                    background-color: #1C1C1E;
                    border: 1px solid #3A3A3C;
                    border-radius: 10px;
                }
                QFrame:hover {
                    border: 1px solid #0A84FF;
                    background-color: #252528;
                }
                """
            )
            self.lbl_num.setStyleSheet("font-size: 24px; font-weight: 900; color: #FFFFFF;")
            if self.recorded_count >= 12:
                self.lbl_status.setText("12/12 ✅")
                self.lbl_status.setStyleSheet(
                    "font-size: 10px; font-weight: bold; padding: 2px 4px; border-radius: 4px; background: rgba(48, 209, 88, 0.2); color: #30D158;"
                )
            elif self.recorded_count > 0:
                self.lbl_status.setText(f"{self.recorded_count}/12")
                self.lbl_status.setStyleSheet(
                    "font-size: 10px; font-weight: bold; padding: 2px 4px; border-radius: 4px; background: rgba(100, 210, 255, 0.2); color: #64D2FF;"
                )
            else:
                self.lbl_status.setText("0/12")
                self.lbl_status.setStyleSheet(
                    "font-size: 10px; padding: 2px 4px; border-radius: 4px; background: #2C2C2E; color: #8E8E93;"
                )


class GestureWidget(QWidget):
    """Tab 7: 156-Pair Gesture Mapper, Guided Macro Recorder Wizard, and Auto-Binh Console."""

    def __init__(self, gesture_manager: Optional[GestureManager] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.manager = gesture_manager or GestureManager()
        self.recorder = MacroRecorder(self)
        self.window_manager = WindowManager()

        self.selected_pair: Tuple[int, int] = (1, 2)
        self.active_source: int = 1
        self.active_target_idx: int = 0  # 0 to 11
        self.active_win_bounds: Tuple[int, int, int, int] = (100, 100, 1000, 700)
        self.active_window_id: Optional[int] = None
        self.discovered_windows: List[WindowItem] = []

        self.slot_boxes: Dict[int, CardSlotBox] = {}
        self.target_chip_buttons: List[QPushButton] = []
        self.source_buttons: List[QPushButton] = []

        self._init_ui()
        self._connect_signals()
        self._refresh_window_list()
        self.refresh_all()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # =====================================================================
        # 1. TOP BAR: WINDOW / TAB SELECTOR FOR MACRO RECORDING
        # =====================================================================
        win_frame = QFrame()
        win_frame.setObjectName("WinSelectorFrame")
        win_frame.setStyleSheet(
            """
            #WinSelectorFrame {
                background: #1C1C1E;
                border: 1px solid #2C2C2E;
                border-radius: 8px;
                padding: 6px;
            }
            """
        )
        win_layout = QHBoxLayout(win_frame)
        win_layout.setContentsMargins(8, 4, 8, 4)
        win_layout.setSpacing(10)

        lbl_win = QLabel("🎯 Cửa sổ game để ghi:")
        lbl_win.setStyleSheet("font-weight: bold; color: #0A84FF; font-size: 12px;")
        win_layout.addWidget(lbl_win)

        self.combo_windows = QComboBox()
        self.combo_windows.setMinimumWidth(280)
        self.combo_windows.setStyleSheet("background: #2C2C2E; color: white; padding: 4px; font-size: 12px;")
        win_layout.addWidget(self.combo_windows)

        self.btn_refresh_windows = QPushButton("🔄 Quét cửa sổ")
        self.btn_refresh_windows.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        win_layout.addWidget(self.btn_refresh_windows)

        self.btn_preview_window = QPushButton("📸 Xem trước & 13 Ô bài")
        self.btn_preview_window.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        win_layout.addWidget(self.btn_preview_window)

        self.chk_auto_activate = QCheckBox("⚡ Tự động mở cửa sổ khi chọn/ghi")
        self.chk_auto_activate.setChecked(True)
        self.chk_auto_activate.setStyleSheet("color: #30D158; font-size: 11px; font-weight: bold;")
        self.chk_auto_activate.setToolTip(
            "Khi chọn trình duyệt/cửa sổ hoặc khi ghi/test macro, hệ thống sẽ tự động kích hoạt và mở cửa sổ/tab đó lên phía trước"
        )
        win_layout.addWidget(self.chk_auto_activate)

        self.lbl_win_info = QLabel("Chưa chọn cửa sổ")
        self.lbl_win_info.setStyleSheet("color: #8E8E93; font-size: 11px;")
        win_layout.addWidget(self.lbl_win_info)

        self.btn_auto_detect_slots = QPushButton("🔍 Tự động nhận diện 13 ô bài", objectName="PrimaryBtn")
        self.btn_auto_detect_slots.setStyleSheet(
            "background-color: #30D158; color: black; font-weight: bold; padding: 4px 10px; border-radius: 6px;"
        )
        self.btn_auto_detect_slots.setToolTip(
            "Chụp frame game hiện tại, phát hiện 13 lá bài và tự động căn chỉnh tọa độ 13 ô bài theo đúng kích thước khung hình (toàn màn hình hoặc thu nhỏ)"
        )
        win_layout.addWidget(self.btn_auto_detect_slots)

        self.btn_edit_slots = QPushButton("🎯 Định vị 13 Ô bài")
        self.btn_edit_slots.setToolTip("Chỉnh sửa tọa độ tương đối (%) của 13 vị trí quân bài trên bàn chơi")
        win_layout.addWidget(self.btn_edit_slots)

        self.btn_auto_fill_all = QPushButton("⚡ Tạo 156 Mẫu Chuẩn")
        self.btn_auto_fill_all.setStyleSheet(
            "background-color: #5E5CE6; color: white; font-weight: bold; padding: 4px 10px; border-radius: 6px;"
        )
        self.btn_auto_fill_all.setToolTip("Tự động sinh các đường cong Bézier tự nhiên cho toàn bộ 156 cặp vị trí")
        win_layout.addWidget(self.btn_auto_fill_all)

        self.btn_export = QPushButton("💾 Xuất JSON")
        win_layout.addWidget(self.btn_export)

        self.btn_import = QPushButton("📂 Nhập JSON")
        win_layout.addWidget(self.btn_import)

        main_layout.addWidget(win_frame)

        # =====================================================================
        # 2. CONFIG BAR
        # =====================================================================
        cfg_frame = QFrame()
        cfg_frame.setStyleSheet("background: #252528; border-radius: 6px; padding: 2px;")
        cfg_layout = QHBoxLayout(cfg_frame)
        cfg_layout.setContentsMargins(8, 2, 8, 2)

        self.lbl_stats = QLabel("Đang tải dữ liệu...")
        self.lbl_stats.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFFFFF;")
        cfg_layout.addWidget(self.lbl_stats)

        cfg_layout.addStretch()

        self.chk_random = QCheckBox("🎲 Chọn ngẫu nhiên mẫu")
        self.chk_random.setChecked(True)
        cfg_layout.addWidget(self.chk_random)

        self.chk_verified_only = QCheckBox("🛡️ Chỉ dùng mẫu đã test")
        self.chk_verified_only.setChecked(False)
        cfg_layout.addWidget(self.chk_verified_only)

        self.chk_avoid_repeats = QCheckBox("🔄 Tránh lặp liên tiếp")
        self.chk_avoid_repeats.setChecked(True)
        cfg_layout.addWidget(self.chk_avoid_repeats)

        cfg_layout.addSpacing(10)
        cfg_layout.addWidget(QLabel("Tốc độ:"))
        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(5, 20)
        self.slider_speed.setValue(10)
        self.slider_speed.setFixedWidth(80)
        cfg_layout.addWidget(self.slider_speed)
        self.lbl_speed_val = QLabel("1.0x")
        self.lbl_speed_val.setStyleSheet("color: #64D2FF; font-weight: bold;")
        cfg_layout.addWidget(self.lbl_speed_val)

        cfg_layout.addSpacing(10)
        cfg_layout.addWidget(QLabel("Nghỉ giữa lượt:"))
        self.spin_delay = QSpinBox()
        self.spin_delay.setRange(100, 1500)
        self.spin_delay.setValue(350)
        self.spin_delay.setSuffix(" ms")
        cfg_layout.addWidget(self.spin_delay)

        main_layout.addWidget(cfg_frame)

        # =====================================================================
        # 3. MAIN TABBED CONTAINER: (TAB 1: TRỢ LÝ TRỰC QUAN | TAB 2: MA TRẬN 13x13)
        # =====================================================================
        self.tabs_view = QTabWidget()
        self.tabs_view.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #2C2C2E;
                background: #18181A;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #252528;
                color: #8E8E93;
                font-weight: bold;
                padding: 6px 14px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #0A84FF;
                color: white;
            }
            """
        )

        # --- TAB 1: VISUAL CARD BOARD & SEQUENTIAL WIZARD ---
        visual_tab = QWidget()
        v_tab_layout = QVBoxLayout(visual_tab)
        v_tab_layout.setContentsMargins(8, 8, 8, 8)
        v_tab_layout.setSpacing(8)

        # Visual 13 Card Board (Row 1: 1-2-3 | Row 2: 4-5-6-7-8 | Row 3: 9-10-11-12-13)
        board_group = QGroupBox("BÀN BÀI 13 Ô (ĐÁNH SỐ TỪ TRÊN XUỐNG DƯỚI, TỪ TRÁI SANG PHẢI)")
        board_group.setStyleSheet("QGroupBox { font-weight: bold; color: #64D2FF; font-size: 12px; }")
        board_layout = QVBoxLayout(board_group)
        board_layout.setContentsMargins(6, 6, 6, 6)
        board_layout.setSpacing(6)

        # Row 1: Chi Đầu (1, 2, 3)
        row1_wrap = QHBoxLayout()
        row1_wrap.setAlignment(Qt.AlignCenter)
        lbl_r1 = QLabel("Chi Đầu (3 lá):")
        lbl_r1.setFixedWidth(100)
        lbl_r1.setStyleSheet("color: #AEAEB2; font-weight: bold;")
        row1_wrap.addWidget(lbl_r1)
        for i in (1, 2, 3):
            box = CardSlotBox(slot_number=i, name=f"Chi Đầu {i}", parent=self)
            box.clicked.connect(self._on_slot_box_clicked)
            self.slot_boxes[i] = box
            row1_wrap.addWidget(box)
            row1_wrap.addSpacing(8)
        board_layout.addLayout(row1_wrap)

        # Row 2: Chi Giữa (4, 5, 6, 7, 8)
        row2_wrap = QHBoxLayout()
        row2_wrap.setAlignment(Qt.AlignCenter)
        lbl_r2 = QLabel("Chi Giữa (5 lá):")
        lbl_r2.setFixedWidth(100)
        lbl_r2.setStyleSheet("color: #AEAEB2; font-weight: bold;")
        row2_wrap.addWidget(lbl_r2)
        for i in (4, 5, 6, 7, 8):
            box = CardSlotBox(slot_number=i, name=f"Chi Giữa {i - 3}", parent=self)
            box.clicked.connect(self._on_slot_box_clicked)
            self.slot_boxes[i] = box
            row2_wrap.addWidget(box)
            row2_wrap.addSpacing(6)
        board_layout.addLayout(row2_wrap)

        # Row 3: Chi Cuối (9, 10, 11, 12, 13)
        row3_wrap = QHBoxLayout()
        row3_wrap.setAlignment(Qt.AlignCenter)
        lbl_r3 = QLabel("Chi Cuối (5 lá):")
        lbl_r3.setFixedWidth(100)
        lbl_r3.setStyleSheet("color: #AEAEB2; font-weight: bold;")
        row3_wrap.addWidget(lbl_r3)
        for i in (9, 10, 11, 12, 13):
            box = CardSlotBox(slot_number=i, name=f"Chi Cuối {i - 8}", parent=self)
            box.clicked.connect(self._on_slot_box_clicked)
            self.slot_boxes[i] = box
            row3_wrap.addWidget(box)
            row3_wrap.addSpacing(6)
        board_layout.addLayout(row3_wrap)

        v_tab_layout.addWidget(board_group)

        # Sequential Recording Wizard Box
        wiz_group = QGroupBox("TRỢ LÝ GHI MACRO TUẦN TỰ (NHẤN GIỮ ➔ KÉO ➔ THẢ LẦN LƯỢT 12 VỊ TRÍ)")
        wiz_group.setStyleSheet("QGroupBox { font-weight: bold; color: #30D158; font-size: 12px; }")
        wiz_layout = QVBoxLayout(wiz_group)
        wiz_layout.setContentsMargins(8, 8, 8, 8)
        wiz_layout.setSpacing(6)

        # Source Slot Fast Selector Row
        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("Chọn Vị trí Nguồn:"))
        self.src_scroll = QScrollArea()
        self.src_scroll.setFixedHeight(38)
        self.src_scroll.setWidgetResizable(True)
        self.src_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.src_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        src_container = QWidget()
        src_btn_layout = QHBoxLayout(src_container)
        src_btn_layout.setContentsMargins(0, 0, 0, 0)
        src_btn_layout.setSpacing(4)
        for s in range(1, 14):
            btn = QPushButton(f"Ô {s}")
            btn.setCheckable(True)
            btn.setStyleSheet(
                """
                QPushButton {
                    background: #252528; color: #AEAEB2; font-weight: bold; padding: 4px 8px; border-radius: 4px;
                }
                QPushButton:checked {
                    background: #FF9F0A; color: black;
                }
                """
            )
            btn.clicked.connect(lambda checked=False, slot=s: self._on_source_button_clicked(slot))
            self.source_buttons.append(btn)
            src_btn_layout.addWidget(btn)
        self.src_scroll.setWidget(src_container)
        src_row.addWidget(self.src_scroll)
        wiz_layout.addLayout(src_row)

        # Large Step Instruction Card
        self.instruction_frame = QFrame()
        self.instruction_frame.setStyleSheet(
            """
            QFrame {
                background: #1C1C1E;
                border: 2px solid #0A84FF;
                border-radius: 8px;
                padding: 6px;
            }
            """
        )
        ins_layout = QVBoxLayout(self.instruction_frame)
        ins_layout.setSpacing(3)

        self.lbl_wiz_step_title = QLabel("👉 BƯỚC 1/12: KÉO TỪ [ Ô 1 ] ➔ [ Ô 2 ]")
        self.lbl_wiz_step_title.setStyleSheet("font-size: 15px; font-weight: 900; color: #64D2FF;")
        ins_layout.addWidget(self.lbl_wiz_step_title)

        self.lbl_wiz_step_desc = QLabel(
            "Thao tác: Qua cửa sổ game, NHẤN GIỮ chuột tại Ô 1 (Chi Đầu 1), KÉO và THẢ vào Ô 2 (Chi Đầu 2)."
        )
        self.lbl_wiz_step_desc.setStyleSheet("font-size: 12px; color: #FFFFFF;")
        ins_layout.addWidget(self.lbl_wiz_step_desc)

        self.lbl_wiz_status = QLabel("⏳ Sẵn sàng. Nhấn nút 'Bắt đầu ghi' hoặc đã tự động chờ chuột.")
        self.lbl_wiz_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #AEAEB2;")
        ins_layout.addWidget(self.lbl_wiz_status)

        self.progress_wiz = QProgressBar()
        self.progress_wiz.setFixedHeight(6)
        self.progress_wiz.setTextVisible(False)
        self.progress_wiz.setValue(0)
        ins_layout.addWidget(self.progress_wiz)

        wiz_layout.addWidget(self.instruction_frame)

        # Target chips row (12 targets)
        target_chips_row = QHBoxLayout()
        target_chips_row.addWidget(QLabel("12 Vị trí đích:"))
        for idx in range(12):
            chip = QPushButton("Ô ?")
            chip.setStyleSheet(
                """
                QPushButton {
                    background: #252528; color: #AEAEB2; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px;
                }
                QPushButton:hover {
                    background: #3A3A3C; color: white;
                }
                """
            )
            chip.clicked.connect(lambda checked=False, i=idx: self._on_target_chip_clicked(i))
            self.target_chip_buttons.append(chip)
            target_chips_row.addWidget(chip)
        wiz_layout.addLayout(target_chips_row)

        # Wizard action buttons
        wiz_actions = QHBoxLayout()

        self.btn_wiz_record = QPushButton("🔴 Bắt đầu ghi bước này", objectName="AccentBtn")
        self.btn_wiz_record.setStyleSheet(
            "background-color: #FF453A; color: white; font-weight: bold; padding: 6px 14px; font-size: 12px; border-radius: 6px;"
        )
        wiz_actions.addWidget(self.btn_wiz_record)

        self.btn_wiz_rerecord = QPushButton("🔄 Ghi lại bước này")
        self.btn_wiz_rerecord.setStyleSheet("padding: 6px 10px; font-size: 11px;")
        wiz_actions.addWidget(self.btn_wiz_rerecord)

        self.btn_wiz_prev = QPushButton("⏮️ Bước trước")
        wiz_actions.addWidget(self.btn_wiz_prev)

        self.btn_wiz_next = QPushButton("⏭️ Bỏ qua bước này")
        wiz_actions.addWidget(self.btn_wiz_next)

        self.btn_wiz_test = QPushButton("▶️ Test thử")
        self.btn_wiz_test.setToolTip("Phát lại thao tác kéo thả vừa ghi trên màn hình")
        wiz_actions.addWidget(self.btn_wiz_test)

        self.btn_wiz_bezier = QPushButton("✨ Tạo Bézier bước này")
        wiz_actions.addWidget(self.btn_wiz_bezier)

        wiz_actions.addStretch()

        self.chk_auto_advance = QCheckBox("☑️ Tự động chuyển bước tiếp theo khi thả chuột")
        self.chk_auto_advance.setChecked(True)
        self.chk_auto_advance.setStyleSheet("font-weight: bold; color: #30D158;")
        wiz_actions.addWidget(self.chk_auto_advance)

        wiz_layout.addLayout(wiz_actions)

        v_tab_layout.addWidget(wiz_group)
        self.tabs_view.addTab(visual_tab, "🎮 Trợ Lý Ghi Macro Trực Quan (1-2-3 / 4-5-6-7-8 / 9-10-11-12-13)")

        # --- TAB 2: ADVANCED 13x13 MATRIX ---
        adv_tab = QWidget()
        adv_tab_layout = QHBoxLayout(adv_tab)
        adv_tab_layout.setContentsMargins(6, 6, 6, 6)

        adv_splitter = QSplitter(Qt.Horizontal)

        # Left: 13x13 Matrix
        left_matrix_box = QWidget()
        left_layout = QVBoxLayout(left_matrix_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        title_matrix = QLabel("BẢNG 13 × 13 CÁC CẶP KÉO THẢ CÓ HƯỚNG (Nguồn ➔ Đích)")
        title_matrix.setStyleSheet("font-size: 11px; font-weight: bold; color: #8E8E93;")
        left_layout.addWidget(title_matrix)

        self.table_matrix = QTableWidget(13, 13)
        self.table_matrix.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_matrix.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_matrix.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_matrix.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        headers = [f"Ô {i}" for i in range(1, 14)]
        self.table_matrix.setHorizontalHeaderLabels(headers)
        self.table_matrix.setVerticalHeaderLabels(headers)
        self.table_matrix.setStyleSheet(
            """
            QTableWidget {
                background: #1C1C1E;
                gridline-color: #2C2C2E;
                border: 1px solid #3A3A3C;
                font-size: 11px;
            }
            QHeaderView::section {
                background: #2C2C2E;
                color: #AEAEB2;
                font-weight: bold;
                padding: 2px;
                border: 1px solid #1C1C1E;
            }
            QTableWidget::item:selected {
                background-color: #0A84FF;
                color: white;
                font-weight: bold;
            }
            """
        )
        self.table_matrix.cellClicked.connect(self._on_matrix_cell_clicked)
        left_layout.addWidget(self.table_matrix)
        adv_splitter.addWidget(left_matrix_box)

        # Right: Pair Inspector & Samples Table
        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(6)

        self.grp_pair = QGroupBox("Chi tiết cặp: Ô 1 ➔ Ô 2")
        self.grp_pair.setStyleSheet("QGroupBox { font-weight: bold; color: #0A84FF; }")
        grp_layout = QVBoxLayout(self.grp_pair)
        grp_layout.setSpacing(4)

        self.lbl_pair_desc = QLabel("Đang chọn: Nguồn Ô 1 ➔ Đích Ô 2")
        self.lbl_pair_desc.setStyleSheet("font-size: 11px; color: #AEAEB2;")
        grp_layout.addWidget(self.lbl_pair_desc)

        self.table_samples = QTableWidget(0, 5)
        self.table_samples.setHorizontalHeaderLabels(["Tên mẫu", "Thời gian", "Điểm", "Đã test", "Trọng số"])
        self.table_samples.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_samples.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_samples.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_samples.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_samples.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_samples.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_samples.setStyleSheet("background: #1C1C1E; border: 1px solid #2C2C2E; font-size: 11px;")
        grp_layout.addWidget(self.table_samples)

        btn_bar = QHBoxLayout()
        self.btn_test_sample = QPushButton("▶️ Test thử")
        btn_bar.addWidget(self.btn_test_sample)

        self.btn_toggle_verified = QPushButton("🛡️ Đổi Đã test")
        btn_bar.addWidget(self.btn_toggle_verified)

        self.btn_edit_sample = QPushButton("✏️ Sửa")
        btn_bar.addWidget(self.btn_edit_sample)

        self.btn_delete_sample = QPushButton("🗑️ Xóa", objectName="DangerBtn")
        btn_bar.addWidget(self.btn_delete_sample)
        grp_layout.addLayout(btn_bar)

        right_layout.addWidget(self.grp_pair)

        # Single Record Macro / Bezier in Matrix tab
        grp_record = QGroupBox("Thao tác riêng lẻ cặp này")
        rec_layout = QVBoxLayout(grp_record)
        rec_btn_layout = QHBoxLayout()
        self.btn_record_macro = QPushButton("🔴 Ghi Macro", objectName="AccentBtn")
        self.btn_record_macro.setStyleSheet("background-color: #FF453A; color: white; font-weight: bold; padding: 4px;")
        rec_btn_layout.addWidget(self.btn_record_macro)

        self.btn_gen_bezier = QPushButton("✨ Tạo Bézier")
        rec_btn_layout.addWidget(self.btn_gen_bezier)
        rec_layout.addLayout(rec_btn_layout)

        self.lbl_record_status = QLabel("Sẵn sàng.")
        self.lbl_record_status.setStyleSheet("font-size: 10px; color: #8E8E93;")
        rec_layout.addWidget(self.lbl_record_status)
        right_layout.addWidget(grp_record)

        adv_splitter.addWidget(right_box)
        adv_splitter.setStretchFactor(0, 6)
        adv_splitter.setStretchFactor(1, 4)
        adv_tab_layout.addWidget(adv_splitter)

        self.tabs_view.addTab(adv_tab, "📊 Bảng Ma Trận 13 × 13 (Nâng Cao)")
        main_layout.addWidget(self.tabs_view)

    def _connect_signals(self) -> None:
        self.combo_windows.currentIndexChanged.connect(self._on_window_selected)
        self.btn_refresh_windows.clicked.connect(self._refresh_window_list)
        self.btn_preview_window.clicked.connect(self._on_preview_window_clicked)

        self.btn_auto_detect_slots.clicked.connect(self._on_auto_detect_slots_clicked)
        self.btn_edit_slots.clicked.connect(self._on_edit_slots_clicked)
        self.btn_auto_fill_all.clicked.connect(self._on_auto_fill_all_clicked)
        self.btn_export.clicked.connect(self._on_export_clicked)
        self.btn_import.clicked.connect(self._on_import_clicked)

        self.chk_random.toggled.connect(self._on_config_changed)
        self.chk_verified_only.toggled.connect(self._on_config_changed)
        self.chk_avoid_repeats.toggled.connect(self._on_config_changed)
        self.slider_speed.valueChanged.connect(self._on_speed_changed)
        self.spin_delay.valueChanged.connect(self._on_config_changed)

        # Wizard Buttons
        self.btn_wiz_record.clicked.connect(self._on_wiz_record_clicked)
        self.btn_wiz_rerecord.clicked.connect(self._on_wiz_rerecord_clicked)
        self.btn_wiz_prev.clicked.connect(self._on_wiz_prev_clicked)
        self.btn_wiz_next.clicked.connect(self._on_wiz_next_clicked)
        self.btn_wiz_test.clicked.connect(self._on_wiz_test_clicked)
        self.btn_wiz_bezier.clicked.connect(self._on_wiz_bezier_clicked)

        # Matrix Buttons
        self.btn_test_sample.clicked.connect(self._on_test_sample_clicked)
        self.btn_toggle_verified.clicked.connect(self._on_toggle_verified_clicked)
        self.btn_edit_sample.clicked.connect(self._on_edit_sample_clicked)
        self.btn_delete_sample.clicked.connect(self._on_delete_sample_clicked)
        self.btn_record_macro.clicked.connect(self._on_record_macro_clicked)
        self.btn_gen_bezier.clicked.connect(self._on_gen_bezier_clicked)

        # Macro Recorder Signals
        self.recorder.recording_started.connect(self._on_recorder_started)
        self.recorder.recording_progress.connect(self._on_recorder_progress)
        self.recorder.recording_finished.connect(self._on_recorder_finished)
        self.recorder.recording_cancelled.connect(self._on_recorder_cancelled)

    # =========================================================================
    # WINDOW SELECTION & PREVIEW
    # =========================================================================

    def _refresh_window_list(self) -> None:
        """Finds on-screen windows and populates the window selector combo box."""
        self.discovered_windows = self.window_manager.list_windows()
        self.combo_windows.blockSignals(True)
        self.combo_windows.clear()
        self.combo_windows.addItem("-- Chọn cửa sổ game để ghi --", None)

        for win in self.discovered_windows:
            self.combo_windows.addItem(win.display_label, win.window_id)

        self.combo_windows.blockSignals(False)

        # Auto-select first game-like window if available
        if self.discovered_windows:
            for idx, w in enumerate(self.discovered_windows, start=1):
                t_lower = (w.title or "").lower() + " " + (w.owner_name or "").lower()
                if any(k in t_lower for k in ["binh", "game", "poker", "play", "table", "safari", "chrome"]):
                    self.combo_windows.setCurrentIndex(idx)
                    break

    def _on_window_selected(self, idx: int) -> None:
        wid = self.combo_windows.currentData()
        if not wid:
            self.active_window_id = None
            self.lbl_win_info.setText("Chưa chọn cửa sổ")
            return

        match = next((w for w in self.discovered_windows if w.window_id == wid), None)
        if match:
            self.active_window_id = match.window_id
            self.set_active_window_bounds(match.bounds)

            # Auto-activate window and bring browser tab to front
            if hasattr(self, "chk_auto_activate") and self.chk_auto_activate.isChecked():
                self.window_manager.activate_window(match)

            # Check if 13 card slots can be confirmed right away on this window (whether full screen or shrunk)
            live_coords = self.get_live_card_slot_coords(match.window_id)
            if live_coords and len(live_coords) == 13:
                slots = self.manager.get_slots()
                for slot_num, (rx, ry) in live_coords.items():
                    slot_name = slots[slot_num].name if slot_num in slots else f"Ô {slot_num}"
                    group = "front" if slot_num <= 3 else ("middle" if slot_num <= 8 else "back")
                    self.manager.save_slot(CardSlot(slot_number=slot_num, name=slot_name, rel_x=rx, rel_y=ry, group_name=group))
                self.refresh_all()
                self.lbl_win_info.setText(
                    f"✅ Đã mở tab & xác nhận đúng 13 vị trí quân bài: {match.owner_name} ({match.bounds[2]}x{match.bounds[3]})"
                )
                self.lbl_win_info.setStyleSheet("color: #30D158; font-weight: bold; font-size: 11px;")
            else:
                self.lbl_win_info.setText(
                    f"Đã mở: {match.owner_name} ({match.bounds[2]}x{match.bounds[3]}) tại ({match.bounds[0]}, {match.bounds[1]})"
                )
                self.lbl_win_info.setStyleSheet("color: #64D2FF; font-weight: bold; font-size: 11px;")

    def get_live_card_slot_coords(self, window_id: Optional[int] = None) -> Optional[Dict[int, Tuple[float, float]]]:
        """Captures window frame and detects the 13 card slot positions in real-time,
        returning relative coordinates [0.0, 1.0] accurate to the current window size (fullscreen or shrunk).
        """
        wid = window_id or self.active_window_id
        if not wid:
            return None
        img = ScreenCapture.capture_window_by_id(wid)
        if img is None or img.size == 0:
            return None

        from app.vision.card_detector import CardDetector
        detector = CardDetector()
        crops = detector.detect_cards(img)
        if len(crops) < 13:
            return None

        sorted_crops = sorted(crops, key=lambda c: c.bbox[1])
        front = sorted(sorted_crops[0:3], key=lambda c: c.bbox[0])
        mid = sorted(sorted_crops[3:8], key=lambda c: c.bbox[0])
        back = sorted(sorted_crops[8:13], key=lambda c: c.bbox[0])
        all_13 = front + mid + back
        frame_h, frame_w = img.shape[:2]

        coords: Dict[int, Tuple[float, float]] = {}
        for i, crop in enumerate(all_13, start=1):
            cx = crop.bbox[0] + crop.bbox[2] / 2.0
            cy = crop.bbox[1] + crop.bbox[3] / 2.0
            coords[i] = (round(cx / float(frame_w), 4), round(cy / float(frame_h), 4))
        return coords

    def _on_preview_window_clicked(self) -> None:
        if not self.active_window_id:
            QMessageBox.warning(self, "Chưa chọn cửa sổ", "Vui lòng chọn một cửa sổ game từ danh sách để xem trước!")
            return

        # Auto-activate target window
        if hasattr(self, "chk_auto_activate") and self.chk_auto_activate.isChecked():
            self.window_manager.activate_window(self.active_window_id)

        live_bounds = self.window_manager.get_window_bounds(self.active_window_id)
        if live_bounds:
            self.set_active_window_bounds(live_bounds)

        img = ScreenCapture.capture_window_by_id(self.active_window_id)
        if img is None:
            QMessageBox.critical(self, "Lỗi chụp ảnh", "Không thể chụp frame ảnh từ cửa sổ đã chọn.")
            return

        annotated = img.copy()
        h, w = annotated.shape[:2]

        from app.vision.card_detector import CardDetector
        detector = CardDetector()
        crops = detector.detect_cards(annotated)

        slots = self.manager.get_slots()
        has_13 = len(crops) >= 13

        if has_13:
            sorted_crops = sorted(crops, key=lambda c: c.bbox[1])
            front = sorted(sorted_crops[0:3], key=lambda c: c.bbox[0])
            mid = sorted(sorted_crops[3:8], key=lambda c: c.bbox[0])
            back = sorted(sorted_crops[8:13], key=lambda c: c.bbox[0])
            all_13 = front + mid + back
            for i, crop in enumerate(all_13, start=1):
                bx, by, bw, bh = crop.bbox
                color = (10, 214, 255) if i <= 3 else ((255, 210, 100) if i <= 8 else (88, 209, 48))
                cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), color, 3)
                label = f"#{i}"
                cv2.putText(annotated, label, (bx + 4, by + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
                cv2.putText(annotated, label, (bx + 4, by + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
        else:
            for i, slot in slots.items():
                cx = int(slot.rel_x * w)
                cy = int(slot.rel_y * h)
                color = (10, 214, 255) if i <= 3 else ((255, 210, 100) if i <= 8 else (88, 209, 48))
                cv2.circle(annotated, (cx, cy), 18, color, -1)
                cv2.circle(annotated, (cx, cy), 18, (0, 0, 0), 2)
                cv2.putText(annotated, str(i), (cx - 7, cy + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"🎯 Khung Giao Diện & Vị Trí 13 Ô Bài (#{self.active_window_id} - {w}x{h})")
        dlg.resize(850, 620)
        lay = QVBoxLayout(dlg)

        status_text = (
            f"✅ Đã xác nhận đúng vị trí 13 con bài khớp khung giao diện ({w}x{h})! "
            "Ô 1-3 (Chi Đầu: Vàng) | Ô 4-8 (Chi Giữa: Xanh lam) | Ô 9-13 (Chi Cuối: Xanh lục)"
            if has_13 else
            f"⚠️ Chỉ tìm thấy {len(crops)}/13 lá bài. Đang hiển thị 13 ô bài theo tọa độ đã hiệu chỉnh ({w}x{h})."
        )
        lbl_status = QLabel(status_text)
        lbl_status.setStyleSheet("color: #30D158; font-weight: bold; font-size: 11px;" if has_13 else "color: #FF9F0A; font-weight: bold; font-size: 11px;")
        lay.addWidget(lbl_status)

        lbl_img = QLabel()
        lbl_img.setAlignment(Qt.AlignCenter)
        qimg = QImage(annotated.data, w, h, 3 * w, QImage.Format_BGR888)
        pix = QPixmap.fromImage(qimg).scaled(820, 560, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        lbl_img.setPixmap(pix)
        lay.addWidget(lbl_img)
        dlg.exec()

    def set_active_window_bounds(self, bounds: Tuple[int, int, int, int]) -> None:
        """Sets active game window bounds (x, y, w, h) for screen translation."""
        self.active_win_bounds = bounds

    # =========================================================================
    # REFRESH ALL DATA & UI VIEWS
    # =========================================================================

    def refresh_all(self) -> None:
        """Refreshes matrix, visual board, stats label, and sample inspector."""
        self.manager.reload_data()
        stats = self.manager.get_pair_stats_matrix()
        total_pairs = 156
        covered_pairs = sum(1 for (c, _) in stats.values() if c > 0)
        verified_pairs = sum(1 for (_, v) in stats.values() if v)
        total_samples = len(self.manager.get_all_samples())

        self.lbl_stats.setText(
            f"📊 Thư viện: {covered_pairs}/{total_pairs} cặp đã có ({total_samples} mẫu lưu trữ) • {verified_pairs} cặp đã test ✅"
        )

        # 1. Update Visual Board (13 Card Slots)
        slots = self.manager.get_slots()
        outgoing_counts: Dict[int, int] = {i: 0 for i in range(1, 14)}
        for (s, d), (c, _) in stats.items():
            if c > 0:
                outgoing_counts[s] = outgoing_counts.get(s, 0) + 1

        for s_num, box in self.slot_boxes.items():
            slot_obj = slots.get(s_num)
            name = slot_obj.name if slot_obj else f"Ô {s_num}"
            rx = slot_obj.rel_x if slot_obj else 0.5
            ry = slot_obj.rel_y if slot_obj else 0.5
            box.set_data(name, rx, ry, outgoing_counts.get(s_num, 0))

        # 2. Update Source Buttons badges
        for idx, btn in enumerate(self.source_buttons, start=1):
            btn.setChecked(idx == self.active_source)
            cnt = outgoing_counts.get(idx, 0)
            if cnt >= 12:
                btn.setText(f"Ô {idx} (12/12 ✅)")
            else:
                btn.setText(f"Ô {idx} ({cnt}/12)")

        # 3. Update 13x13 Matrix
        for s in range(1, 14):
            for d in range(1, 14):
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignCenter)
                if s == d:
                    item.setText("—")
                    item.setForeground(QColor("#48484A"))
                    item.setBackground(QColor("#18181A"))
                    item.setFlags(Qt.NoItemFlags)
                else:
                    count, has_ver = stats.get((s, d), (0, False))
                    if count > 0:
                        item.setText(str(count))
                        if has_ver:
                            item.setForeground(QColor("#30D158"))
                            item.setBackground(QColor(48, 209, 88, 30))
                        else:
                            item.setForeground(QColor("#64D2FF"))
                            item.setBackground(QColor(100, 210, 255, 30))
                    else:
                        item.setText("0")
                        item.setForeground(QColor("#8E8E93"))
                        item.setBackground(QColor("#2C2C2E"))
                self.table_matrix.setItem(s - 1, d - 1, item)

        # Highlight current selected cell in matrix
        s, d = self.selected_pair
        self.table_matrix.setCurrentCell(s - 1, d - 1)
        self._load_selected_pair_samples()
        self._update_wizard_view()

    # =========================================================================
    # GUIDED SEQUENTIAL MACRO RECORDER LOGIC
    # =========================================================================

    def _get_active_target_slot(self) -> int:
        """Returns the current target slot number (1..13 excluding active_source)."""
        targets = [i for i in range(1, 14) if i != self.active_source]
        safe_idx = max(0, min(self.active_target_idx, len(targets) - 1))
        return targets[safe_idx]

    def _on_slot_box_clicked(self, slot_num: int) -> None:
        """User clicks a card slot box on the board to set it as source slot."""
        self.active_source = slot_num
        self.active_target_idx = 0
        self.selected_pair = (self.active_source, self._get_active_target_slot())
        self.refresh_all()

    def _on_source_button_clicked(self, slot_num: int) -> None:
        self.active_source = slot_num
        self.active_target_idx = 0
        self.selected_pair = (self.active_source, self._get_active_target_slot())
        self.refresh_all()

    def _on_target_chip_clicked(self, target_idx: int) -> None:
        self.active_target_idx = target_idx
        self.selected_pair = (self.active_source, self._get_active_target_slot())
        self._update_wizard_view()
        self._load_selected_pair_samples()

    def _update_wizard_view(self) -> None:
        s = self.active_source
        targets = [i for i in range(1, 14) if i != s]
        self.active_target_idx = max(0, min(self.active_target_idx, len(targets) - 1))
        d = targets[self.active_target_idx]
        self.selected_pair = (s, d)

        slots = self.manager.get_slots()
        name_s = slots[s].name if s in slots else f"Ô {s}"
        name_d = slots[d].name if d in slots else f"Ô {d}"

        # Update Visual Board Highlighting
        for s_num, box in self.slot_boxes.items():
            box.set_role(is_source=(s_num == s), is_target=(s_num == d))

        # Update Step Title and Instructions
        step_num = self.active_target_idx + 1
        self.lbl_wiz_step_title.setText(f"👉 BƯỚC {step_num}/12: KÉO TỪ [ Ô {s} ] ➔ [ Ô {d} ]")
        self.lbl_wiz_step_desc.setText(
            f"Thao tác: Qua cửa sổ game, NHẤN GIỮ chuột tại Ô {s} ({name_s}), KÉO và THẢ vào Ô {d} ({name_d})."
        )

        samples = self.manager.get_samples_for_pair(s, d)
        if samples:
            self.lbl_wiz_status.setText(
                f"✅ Đã có {len(samples)} mẫu cho cặp này (Mẫu gần nhất: {samples[-1].total_duration_ms} ms). Sẵn sàng ghi đè hoặc test."
            )
            self.lbl_wiz_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #30D158;")
        else:
            self.lbl_wiz_status.setText("⏳ Chưa có mẫu. Hãy nhấn 'Bắt đầu ghi' rồi kéo thả trên bàn chơi game.")
            self.lbl_wiz_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #FF9F0A;")

        # Update Target Chip Buttons
        stats = self.manager.get_pair_stats_matrix()
        for idx, chip in enumerate(self.target_chip_buttons):
            t_num = targets[idx]
            cnt, is_ver = stats.get((s, t_num), (0, False))
            is_current = (idx == self.active_target_idx)

            if is_current:
                chip.setText(f"👉 Ô {t_num}")
                chip.setStyleSheet(
                    "background: #30D158; color: black; font-weight: 900; font-size: 11px; padding: 3px 6px; border-radius: 4px;"
                )
            elif cnt > 0:
                chip.setText(f"Ô {t_num} ✓")
                chip.setStyleSheet(
                    "background: rgba(48, 209, 88, 0.2); color: #30D158; font-size: 10px; font-weight: bold; padding: 2px 5px; border-radius: 4px;"
                )
            else:
                chip.setText(f"Ô {t_num}")
                chip.setStyleSheet(
                    "background: #252528; color: #8E8E93; font-size: 10px; padding: 2px 5px; border-radius: 4px;"
                )

        self.progress_wiz.setValue(0)

    def _on_auto_detect_slots_clicked(self) -> None:
        """Captures active game window, detects the 13 cards, and automatically sets
        the coordinates of all 13 slots according to the actual game layout (fullscreen or shrunk).
        """
        if not self.active_window_id:
            QMessageBox.warning(self, "Chưa chọn cửa sổ", "Vui lòng chọn cửa sổ game từ danh sách trước!")
            return

        # Auto-activate target window
        if hasattr(self, "chk_auto_activate") and self.chk_auto_activate.isChecked():
            self.window_manager.activate_window(self.active_window_id)

        live_bounds = self.window_manager.get_window_bounds(self.active_window_id)
        if live_bounds:
            self.set_active_window_bounds(live_bounds)

        img = ScreenCapture.capture_window_by_id(self.active_window_id)
        if img is None or img.size == 0:
            QMessageBox.critical(self, "Lỗi chụp ảnh", "Không thể chụp frame ảnh từ cửa sổ game.")
            return

        from app.vision.card_detector import CardDetector
        detector = CardDetector()
        crops = detector.detect_cards(img)

        if len(crops) < 13:
            QMessageBox.warning(
                self,
                "Chưa thấy đủ bài",
                f"Chỉ tìm thấy {len(crops)}/13 lá bài trên bàn chơi.\n\nHãy đảm bảo bàn chơi đã chia đủ 13 lá và không bị che khuất.",
            )
            return

        # Sort crops vertically into front (top 3), middle (mid 5), back (bottom 5)
        sorted_crops = sorted(crops, key=lambda c: c.bbox[1])
        front_crops = sorted(sorted_crops[0:3], key=lambda c: c.bbox[0])
        mid_crops = sorted(sorted_crops[3:8], key=lambda c: c.bbox[0])
        back_crops = sorted(sorted_crops[8:13], key=lambda c: c.bbox[0])

        all_ordered = front_crops + mid_crops + back_crops
        frame_h, frame_w = img.shape[0], img.shape[1]

        slots = self.manager.get_slots()
        for i, crop in enumerate(all_ordered, start=1):
            cx = crop.bbox[0] + crop.bbox[2] / 2.0
            cy = crop.bbox[1] + crop.bbox[3] / 2.0
            rx = round(cx / float(frame_w), 4)
            ry = round(cy / float(frame_h), 4)
            group = "front" if i <= 3 else ("middle" if i <= 8 else "back")
            slot_name = slots[i].name if i in slots else f"Ô {i}"
            updated_slot = CardSlot(slot_number=i, name=slot_name, rel_x=rx, rel_y=ry, group_name=group)
            self.manager.save_slot(updated_slot)

        self.refresh_all()
        # Open visual verification preview so user can immediately verify the confirmed positions
        self._on_preview_window_clicked()

    def _on_wiz_record_clicked(self) -> None:
        """Starts recording for the active step in the wizard."""
        # Ensure window is frontmost and live bounds are updated in real-time
        if self.active_window_id:
            if hasattr(self, "chk_auto_activate") and self.chk_auto_activate.isChecked():
                self.window_manager.activate_window(self.active_window_id)
            live_bounds = self.window_manager.get_window_bounds(self.active_window_id)
            if live_bounds:
                self.set_active_window_bounds(live_bounds)

        s, d = self.selected_pair
        slots = self.manager.get_slots()
        name_s = slots[s].name if s in slots else f"Ô {s}"
        name_d = slots[d].name if d in slots else f"Ô {d}"

        self.btn_wiz_record.setEnabled(False)
        self.btn_wiz_record.setText("⏳ ĐANG CHỜ NHẤN GIỮ CHUỘT...")
        self.lbl_wiz_status.setText(
            f"Đã mở cửa sổ: Hãy NHẤN GIỮ tại {name_s}, KÉO sang {name_d} rồi THẢ..."
        )
        self.lbl_wiz_status.setStyleSheet("color: #FF9F0A; font-weight: bold;")
        self.progress_wiz.setValue(0)

        self.recorder.start_recording(
            source_slot=s,
            target_slot=d,
            sample_name=f"Macro {s}➔{d}",
            win_bounds=self.active_win_bounds,
            timeout_seconds=60.0,
            bounds_getter=lambda: self.window_manager.get_window_bounds(self.active_window_id) if self.active_window_id else None,
        )

    def _on_wiz_rerecord_clicked(self) -> None:
        self._on_wiz_record_clicked()

    def _on_wiz_prev_clicked(self) -> None:
        if self.active_target_idx > 0:
            self.active_target_idx -= 1
        elif self.active_source > 1:
            self.active_source -= 1
            self.active_target_idx = 11
        self._update_wizard_view()
        self._load_selected_pair_samples()

    def _on_wiz_next_clicked(self) -> None:
        if self.active_target_idx < 11:
            self.active_target_idx += 1
        elif self.active_source < 13:
            self.active_source += 1
            self.active_target_idx = 0
        self._update_wizard_view()
        self._load_selected_pair_samples()

    def _on_wiz_test_clicked(self) -> None:
        s, d = self.selected_pair
        samples = self.manager.get_samples_for_pair(s, d)
        if not samples:
            QMessageBox.warning(self, "Chưa có mẫu", f"Cặp Ô {s} ➔ Ô {d} chưa có mẫu nào để test!")
            return
        sample = samples[-1]
        self._execute_test_sample(sample)

    def _on_wiz_bezier_clicked(self) -> None:
        s, d = self.selected_pair
        slots = self.manager.get_slots()
        s_slot = slots.get(s)
        d_slot = slots.get(d)
        s_coords = (s_slot.rel_x, s_slot.rel_y) if s_slot else (0.3, 0.3)
        d_coords = (d_slot.rel_x, d_slot.rel_y) if d_slot else (0.7, 0.7)

        sample = self.manager.selector.generate_natural_bezier_sample(
            source_slot=s,
            target_slot=d,
            start_coord=s_coords,
            end_coord=d_coords,
            is_verified=True,
        )
        self.manager.save_sample(sample)
        self.refresh_all()

    # =========================================================================
    # MACRO RECORDER EVENT HANDLERS
    # =========================================================================

    def _on_recorder_started(self) -> None:
        self.lbl_wiz_status.setText("🔴 ĐANG GHI: Chuột đang nhấn giữ, hãy kéo thả đến đích...")
        self.lbl_wiz_status.setStyleSheet("color: #FF453A; font-weight: bold;")
        self.btn_wiz_record.setText("🔴 ĐANG KÉO CHUỘT...")

    def _on_recorder_progress(self, pts_count: int) -> None:
        self.progress_wiz.setValue(min(100, pts_count * 3))

    def _on_recorder_finished(self, sample: GestureSample) -> None:
        self.manager.save_sample(sample)
        self.btn_wiz_record.setEnabled(True)
        self.btn_wiz_record.setText("🔴 Bắt đầu ghi bước này")
        self.progress_wiz.setValue(100)

        s, d = sample.source_slot, sample.target_slot
        self.lbl_wiz_status.setText(
            f"🎉 ĐÃ LƯU THÀNH CÔNG: Ô {s} ➔ Ô {d} ({len(sample.points)} điểm, {sample.total_duration_ms} ms)!"
        )
        self.lbl_wiz_status.setStyleSheet("color: #30D158; font-weight: bold;")

        self.refresh_all()

        # Auto-advance to next step if enabled
        if self.chk_auto_advance.isChecked():
            QTimer.singleShot(800, self._auto_advance_next_step)

    def _auto_advance_next_step(self) -> None:
        if self.active_target_idx < 11:
            self.active_target_idx += 1
            self._update_wizard_view()
            self._load_selected_pair_samples()
            # Automatically arm next step
            self._on_wiz_record_clicked()
        elif self.active_source < 13:
            reply = QMessageBox.information(
                self,
                "Hoàn thành vị trí!",
                f"🎉 Tuyệt vời! Bạn đã hoàn thành toàn bộ 12 cử chỉ kéo thả từ Ô {self.active_source}!\n\nTiếp tục ghi cho Vị trí Ô {self.active_source + 1}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                self.active_source += 1
                self.active_target_idx = 0
                self.refresh_all()
                self._on_wiz_record_clicked()

    def _on_recorder_cancelled(self, reason: str) -> None:
        self.btn_wiz_record.setEnabled(True)
        self.btn_wiz_record.setText("🔴 Bắt đầu ghi bước này")
        self.lbl_wiz_status.setText(f"⚠️ {reason}")
        self.lbl_wiz_status.setStyleSheet("color: #FF9F0A;")
        self.progress_wiz.setValue(0)

    # =========================================================================
    # ADVANCED 13x13 MATRIX HANDLERS
    # =========================================================================

    def _on_matrix_cell_clicked(self, row: int, col: int) -> None:
        s = row + 1
        d = col + 1
        if s == d:
            return
        self.selected_pair = (s, d)
        self.active_source = s
        targets = [i for i in range(1, 14) if i != s]
        if d in targets:
            self.active_target_idx = targets.index(d)
        self._load_selected_pair_samples()
        self._update_wizard_view()

    def _load_selected_pair_samples(self) -> None:
        s, d = self.selected_pair
        slots = self.manager.get_slots()
        name_s = slots[s].name if s in slots else f"Ô {s}"
        name_d = slots[d].name if d in slots else f"Ô {d}"

        self.grp_pair.setTitle(f"Chi tiết cặp: Ô {s} ➔ Ô {d}")
        self.lbl_pair_desc.setText(f"Đang chọn: Nguồn Ô {s} ({name_s}) ➔ Đích Ô {d} ({name_d})")

        samples = self.manager.get_samples_for_pair(s, d)
        self.table_samples.setRowCount(len(samples))

        for r, smp in enumerate(samples):
            item_name = QTableWidgetItem(smp.name)
            item_dur = QTableWidgetItem(f"{smp.total_duration_ms} ms")
            item_pts = QTableWidgetItem(f"{len(smp.points)} pts")
            item_ver = QTableWidgetItem("✅ Đã test" if smp.is_verified else "⏳ Chưa")
            item_ver.setForeground(QColor("#30D158") if smp.is_verified else QColor("#FF9F0A"))
            item_wt = QTableWidgetItem(f"{smp.weight:.1f}")

            self.table_samples.setItem(r, 0, item_name)
            self.table_samples.setItem(r, 1, item_dur)
            self.table_samples.setItem(r, 2, item_pts)
            self.table_samples.setItem(r, 3, item_ver)
            self.table_samples.setItem(r, 4, item_wt)
            self.table_samples.item(r, 0).setData(Qt.UserRole, smp.id)

        if samples:
            self.table_samples.selectRow(0)

    def _get_current_selected_sample(self) -> Optional[GestureSample]:
        sel = self.table_samples.selectedItems()
        if not sel:
            return None
        row = sel[0].row()
        smp_id = self.table_samples.item(row, 0).data(Qt.UserRole)
        all_s = self.manager.get_all_samples()
        matches = [s for s in all_s if s.id == smp_id]
        return matches[0] if matches else None

    def _on_speed_changed(self, val: int) -> None:
        factor = val / 10.0
        self.lbl_speed_val.setText(f"{factor:.1f}x")
        self.manager.config.speed_factor = factor

    def _on_config_changed(self) -> None:
        self.manager.config.random_enabled = self.chk_random.isChecked()
        self.manager.config.verified_only = self.chk_verified_only.isChecked()
        self.manager.config.avoid_consecutive_repeats = self.chk_avoid_repeats.isChecked()
        self.manager.config.inter_move_delay_ms = self.spin_delay.value()

    def _on_edit_slots_clicked(self) -> None:
        dlg = SlotEditorDialog(self.manager, parent=self)
        if dlg.exec():
            self.refresh_all()

    def _on_auto_fill_all_clicked(self) -> None:
        reply = QMessageBox.question(
            self,
            "Tự động tạo 156 mẫu chuẩn",
            "Bạn có muốn tự động tạo đường cong Bézier tự nhiên cho toàn bộ 156 cặp vị trí bài chưa có mẫu không?\n\n(Các mẫu đã ghi macro thực tế sẽ được giữ nguyên).",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            created = self.manager.generate_missing_bezier_samples(overwrite_all=False)
            QMessageBox.information(
                self,
                "Hoàn thành",
                f"Đã tạo thành công {created} mẫu đường cong Bézier chuẩn cho các cặp vị trí!",
            )
            self.refresh_all()

    def _on_export_clicked(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Xuất cấu hình cử chỉ JSON", "binh13_gestures.json", "JSON (*.json)"
        )
        if path:
            json_str = self.manager.repository.export_gestures_json()
            with open(path, "w", encoding="utf-8") as f:
                f.write(json_str)
            QMessageBox.information(self, "Xuất thành công", f"Đã lưu cấu hình vào: {path}")

    def _on_import_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Nhập cấu hình cử chỉ JSON", "", "JSON (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                imported = self.manager.repository.import_gestures_json(content)
                QMessageBox.information(self, "Nhập thành công", f"Đã nạp thành công {imported} mẫu cử chỉ!")
                self.refresh_all()
            except Exception as e:
                QMessageBox.critical(self, "Lỗi nhập file", f"Không thể đọc file JSON:\n{e}")

    def _on_test_sample_clicked(self) -> None:
        sample = self._get_current_selected_sample()
        if not sample:
            QMessageBox.warning(self, "Chưa chọn mẫu", "Vui lòng chọn một mẫu cử chỉ trong bảng để phát thử!")
            return
        self._execute_test_sample(sample)

    def _execute_test_sample(self, sample: GestureSample) -> None:
        try:
            if self.active_window_id:
                if hasattr(self, "chk_auto_activate") and self.chk_auto_activate.isChecked():
                    self.window_manager.activate_window(self.active_window_id)
                    time.sleep(0.12)
                live_bounds = self.window_manager.get_window_bounds(self.active_window_id)
                if live_bounds:
                    self.set_active_window_bounds(live_bounds)

            # Query live slot coords on current active window (handles shrunk/resized window)
            live_coords = self.get_live_card_slot_coords(self.active_window_id)
            slots = self.manager.get_slots()

            if live_coords and sample.source_slot in live_coords and sample.target_slot in live_coords:
                s_coords = live_coords[sample.source_slot]
                d_coords = live_coords[sample.target_slot]
            else:
                s_slot = slots.get(sample.source_slot)
                d_slot = slots.get(sample.target_slot)
                s_coords = (s_slot.rel_x, s_slot.rel_y) if s_slot else (0.3, 0.3)
                d_coords = (d_slot.rel_x, d_slot.rel_y) if d_slot else (0.7, 0.7)

            adapted_points = self.manager.adapt_trajectory_to_endpoints(sample.points, s_coords, d_coords)

            self.manager.mouse.play_trajectory(
                points=adapted_points,
                mouse_down_delay_ms=sample.mouse_down_delay_ms,
                mouse_up_delay_ms=sample.mouse_up_delay_ms,
                win_bounds=self.active_win_bounds,
                speed_factor=self.manager.config.speed_factor,
            )
        except Exception as e:
            QMessageBox.warning(self, "Lỗi thực thi", f"Không thể phát cử chỉ chuột:\n{e}")

    def _on_toggle_verified_clicked(self) -> None:
        sample = self._get_current_selected_sample()
        if not sample:
            return
        sample.is_verified = not sample.is_verified
        self.manager.save_sample(sample)
        self.refresh_all()

    def _on_edit_sample_clicked(self) -> None:
        sample = self._get_current_selected_sample()
        if not sample:
            return
        dlg = EditSampleDialog(sample, parent=self)
        if dlg.exec():
            self.manager.save_sample(sample)
            self.refresh_all()

    def _on_delete_sample_clicked(self) -> None:
        sample = self._get_current_selected_sample()
        if not sample:
            return
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa mẫu '{sample.name}' không?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.manager.delete_sample(sample.id)
            self.refresh_all()

    def _on_gen_bezier_clicked(self) -> None:
        self._on_wiz_bezier_clicked()

    def _on_record_macro_clicked(self) -> None:
        self._on_wiz_record_clicked()


class SlotEditorDialog(QDialog):
    """Dialog to calibrate and edit coordinates of the 13 card slots."""

    def __init__(self, manager: GestureManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("🎯 Hiệu Chỉnh 13 Vị Trí Ô Bài")
        self.setFixedSize(540, 480)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        lbl_info = QLabel("Cấu hình tọa độ tương đối [0.00 đến 1.00] của 13 ô bài theo cửa sổ game:")
        lbl_info.setStyleSheet("color: #8E8E93; font-size: 11px;")
        layout.addWidget(lbl_info)

        self.table = QTableWidget(13, 4)
        self.table.setHorizontalHeaderLabels(["Ô", "Tên vị trí", "Tọa độ X (%)", "Tọa độ Y (%)"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        slots = self.manager.get_slots()
        for i in range(1, 14):
            slot = slots.get(i)
            name = slot.name if slot else f"Ô {i}"
            rx = slot.rel_x if slot else 0.5
            ry = slot.rel_y if slot else 0.5

            item_num = QTableWidgetItem(str(i))
            item_num.setFlags(Qt.ItemIsEnabled)
            item_name = QTableWidgetItem(name)
            item_x = QTableWidgetItem(f"{rx:.4f}")
            item_y = QTableWidgetItem(f"{ry:.4f}")

            self.table.setItem(i - 1, 0, item_num)
            self.table.setItem(i - 1, 1, item_name)
            self.table.setItem(i - 1, 2, item_x)
            self.table.setItem(i - 1, 3, item_y)

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_reset = QPushButton("Khôi phục mặc định")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(btn_reset)

        btn_layout.addStretch()
        btn_save = QPushButton("Lưu cấu hình", objectName="PrimaryBtn")
        btn_save.clicked.connect(self._save_and_close)
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _reset_defaults(self) -> None:
        self.manager.repository.init_default_card_slots()
        self.manager.reload_data()
        slots = self.manager.get_slots()
        for i in range(1, 14):
            slot = slots[i]
            self.table.item(i - 1, 1).setText(slot.name)
            self.table.item(i - 1, 2).setText(f"{slot.rel_x:.4f}")
            self.table.item(i - 1, 3).setText(f"{slot.rel_y:.4f}")

    def _save_and_close(self) -> None:
        for i in range(1, 14):
            try:
                name = self.table.item(i - 1, 1).text()
                rx = float(self.table.item(i - 1, 2).text())
                ry = float(self.table.item(i - 1, 3).text())
                group = "front" if i <= 3 else ("middle" if i <= 8 else "back")
                slot = CardSlot(slot_number=i, name=name, rel_x=rx, rel_y=ry, group_name=group)
                self.manager.save_slot(slot)
            except Exception:
                pass
        self.accept()


class EditSampleDialog(QDialog):
    """Dialog to edit sample name and weight."""

    def __init__(self, sample: GestureSample, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.sample = sample
        self.setWindowTitle("Chỉnh sửa mẫu cử chỉ")
        self.setFixedSize(360, 220)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_name = QLineEdit(sample.name)
        form.addRow("Tên mẫu:", self.txt_name)

        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(0.1, 10.0)
        self.spin_weight.setSingleStep(0.5)
        self.spin_weight.setValue(sample.weight)
        form.addRow("Trọng số (Weight):", self.spin_weight)

        self.chk_verified = QCheckBox("Đã kiểm tra hoạt động tốt (Verified)")
        self.chk_verified.setChecked(sample.is_verified)
        form.addRow("Trạng thái:", self.chk_verified)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_save = QPushButton("Lưu", objectName="PrimaryBtn")
        btn_save.clicked.connect(self._save)
        btn_box.addWidget(btn_save)

        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        layout.addLayout(btn_box)

    def _save(self) -> None:
        self.sample.name = self.txt_name.text().strip() or self.sample.name
        self.sample.weight = self.spin_weight.value()
        self.sample.is_verified = self.chk_verified.isChecked()
        self.accept()
