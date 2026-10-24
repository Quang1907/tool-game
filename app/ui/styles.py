"""macOS Cupertino-inspired visual theme and stylesheet definitions."""

MACOS_DARK_THEME = """
QWidget {
    background-color: #1E1E1E;
    color: #F0F0F0;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: #181818;
}

QTabWidget::pane {
    border: 1px solid #2D2D2D;
    background-color: #1E1E1E;
    border-radius: 8px;
}

QTabBar::tab {
    background: #252525;
    color: #A0A0A0;
    padding: 8px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background: #0A84FF;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton {
    background-color: #0A84FF;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #0071E3;
}

QPushButton:pressed {
    background-color: #0058B6;
}

QPushButton:disabled {
    background-color: #333333;
    color: #666666;
}

QPushButton#SecondaryBtn {
    background-color: #2C2C2E;
    color: #E5E5EA;
    border: 1px solid #3A3A3C;
}

QPushButton#SecondaryBtn:hover {
    background-color: #3A3A3C;
}

QPushButton#DangerBtn {
    background-color: #FF453A;
    color: #FFFFFF;
}

QPushButton#DangerBtn:hover {
    background-color: #D70015;
}

QGroupBox {
    border: 1px solid #2C2C2E;
    border-radius: 8px;
    margin-top: 18px;
    padding-top: 14px;
    font-weight: 600;
    color: #0A84FF;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
}

QTableWidget {
    background-color: #1C1C1E;
    border: 1px solid #2C2C2E;
    border-radius: 8px;
    gridline-color: #2C2C2E;
    selection-background-color: #0A84FF;
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #252528;
    color: #8E8E93;
    padding: 6px;
    border: none;
    font-weight: 600;
    font-size: 12px;
}

QProgressBar {
    border: 1px solid #2C2C2E;
    border-radius: 6px;
    text-align: center;
    background-color: #1C1C1E;
    color: #FFFFFF;
    font-weight: 600;
}

QProgressBar::chunk {
    background-color: #30D158;
    border-radius: 5px;
}

QStatusBar {
    background-color: #181818;
    color: #8E8E93;
    border-top: 1px solid #2C2C2E;
}

QLineEdit, QSpinBox, QComboBox {
    background-color: #2C2C2E;
    color: #FFFFFF;
    border: 1px solid #3A3A3C;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #0A84FF;
}
"""
