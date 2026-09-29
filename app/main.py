"""Application bootstrap."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.logging_config import setup_logging, get_logger
from core.config import get_config
from database.database import init_db
from ui.main_window import MainWindow


def main() -> int:
    setup_logging()
    logger = get_logger("ibvap")
    logger.info("Starting IBVAP...")

    cfg = get_config()
    logger.info("Config loaded. Demo mode: %s", cfg.get("application", "demo_mode"))

    init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("IBVAP")
    app.setOrganizationName("IBVAP")
    app.setStyle("Fusion")

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    logger.info("UI ready")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
