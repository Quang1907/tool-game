"""Application entry point for Binh 13 Analyzer on macOS."""

import os
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main() -> int:
    """Main application execution routine."""
    # Enable high-DPI scaling on macOS Retina displays
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("Binh 13 Analyzer")
    app.setOrganizationName("Antigravity")
    app.setApplicationDisplayName("Binh 13 Analyzer — Mậu Binh CV & Monte Carlo")

    # Set High DPI Rounding Policy for Retina displays
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
