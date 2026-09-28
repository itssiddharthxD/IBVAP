import sys
from PySide6.QtWidgets import QApplication
from core.config import load_config
from database.db import create_db, make_session
from database.repository import EventRepository
from ui.main_window import MainWindow

def run():
    cfg = load_config()
    engine = create_db(cfg["database"])
    session = make_session(engine)
    repo = EventRepository(session)

    app = QApplication(sys.argv)
    app.setApplicationName(cfg["app_name"])
    window = MainWindow(cfg, repo)
    window.show()
    sys.exit(app.exec())
