"""Main window — black palette, redesigned professional top bar."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Slot

from video_engine.stream_manager import StreamManager
from services.video_service import VideoService
from services.system_service import SystemService
from services.detection_service import DetectionService
from ui.styles import APP_STYLESHEET

from ui.pages.dashboard import DashboardPage
from ui.pages.cameras import CamerasPage
from ui.pages.live_monitor import LiveMonitorPage
from ui.pages.events import EventsPage
from ui.pages.watchlist import WatchlistPage
from ui.pages.analytics import AnalyticsPage
from ui.pages.settings import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IBVAP  —  Intelligent Border Video Analytics Platform")
        self.resize(1440, 900)
        self.setMinimumSize(1180, 720)

        self.stream_manager = StreamManager()
        self.video_service = VideoService(self.stream_manager)

        self._build_ui()
        self._connect_signals()
        self.setStyleSheet(APP_STYLESHEET)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

        device = SystemService.detect_ai_device()
        self.device_pill.setText(f"AI  ·  {device}")

    def _divider(self) -> QFrame:
        d = QFrame()
        d.setObjectName("topbarDivider")
        d.setFixedWidth(1)
        d.setFixedHeight(18)
        return d

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(12, 16, 12, 14)
        sb.setSpacing(2)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_row.setContentsMargins(2, 0, 2, 0)

        mark = QFrame()
        mark.setObjectName("brandMark")
        mark.setFixedSize(30, 30)
        mark_l = QVBoxLayout(mark)
        mark_l.setContentsMargins(0, 0, 0, 0)
        mark_letter = QLabel("IB")
        mark_letter.setObjectName("brandMarkLetter")
        mark_letter.setAlignment(Qt.AlignCenter)
        mark_l.addWidget(mark_letter)
        brand_row.addWidget(mark)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        brand_text.setContentsMargins(0, 2, 0, 2)
        brand = QLabel("IBVAP")
        brand.setObjectName("brandTitle")
        sub = QLabel("EDGE ANALYTICS")
        sub.setObjectName("brandSub")
        brand_text.addWidget(brand)
        brand_text.addWidget(sub)
        brand_row.addLayout(brand_text, 1)
        sb.addLayout(brand_row)
        sb.addSpacing(16)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background:#2A2A2A;")
        sb.addWidget(div)
        sb.addSpacing(10)

        self.nav_buttons = {}
        for key, label in [
            ("dashboard", "Dashboard"),
            ("live", "Live Monitor"),
            ("cameras", "Cameras"),
            ("events", "Events"),
            ("watchlist", "Watchlist"),
            ("analytics", "Analytics"),
            ("settings", "Settings"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(34)
            btn.clicked.connect(lambda checked=False, k=key: self._navigate(k))
            sb.addWidget(btn)
            self.nav_buttons[key] = btn

        sb.addStretch()
        ver = QLabel("v1.0.0")
        ver.setStyleSheet("color:#6A6A6A; font-size:10px;")
        sb.addWidget(ver)
        root.addWidget(sidebar)

        # ── Right column ─────────────────────────────────────
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        # ── TOP BAR ──────────────────────────────────────────
        top = QFrame()
        top.setObjectName("topbar")
        top.setFixedHeight(52)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(12, 0, 12, 0)
        tl.setSpacing(0)

        def _item(inner, min_w: int = 0):
            """Subtle dark surface around a navbar item."""
            box = QFrame()
            box.setObjectName("topItem")
            box.setFixedHeight(32)
            if min_w:
                box.setMinimumWidth(min_w)
            bl = QHBoxLayout(box)
            bl.setContentsMargins(14, 0, 14, 0)
            bl.setSpacing(8)
            if isinstance(inner, QWidget):
                bl.addWidget(inner, 0, Qt.AlignVCenter)
            else:
                bl.addLayout(inner)
            return box

        # Title item
        title_inner = QHBoxLayout()
        title_inner.setContentsMargins(0, 0, 0, 0)
        title_inner.setSpacing(8)
        accent = QFrame()
        accent.setObjectName("topTitleBar")
        accent.setFixedSize(3, 12)
        title_inner.addWidget(accent, 0, Qt.AlignVCenter)
        self.section_label = QLabel("Dashboard")
        self.section_label.setObjectName("topTitle")
        title_inner.addWidget(self.section_label, 0, Qt.AlignVCenter)
        tl.addWidget(_item(title_inner), 0, Qt.AlignVCenter)

        tl.addSpacing(8)
        tl.addWidget(self._divider())
        tl.addSpacing(8)

        # Ready
        self.status_pill = QLabel("●  Ready")
        self.status_pill.setObjectName("topStatusReady")
        tl.addWidget(_item(self.status_pill), 0, Qt.AlignVCenter)

        tl.addSpacing(6)

        # Streams
        self.streams_pill = QLabel("Streams  0")
        self.streams_pill.setObjectName("topStatus")
        tl.addWidget(_item(self.streams_pill), 0, Qt.AlignVCenter)

        tl.addSpacing(6)

        # AI device
        self.device_pill = QLabel("AI  ·  —")
        self.device_pill.setObjectName("topStatus")
        tl.addWidget(_item(self.device_pill), 0, Qt.AlignVCenter)

        # detail (no box unless text present — keep as plain muted)
        tl.addSpacing(8)
        self.detail_label = QLabel("")
        self.detail_label.setObjectName("topStatus")
        tl.addWidget(self.detail_label, 0, Qt.AlignVCenter)

        tl.addStretch()

        # Offline
        self.mode_label = QLabel("●  Offline")
        self.mode_label.setObjectName("topStatus")
        tl.addWidget(_item(self.mode_label), 0, Qt.AlignVCenter)

        tl.addSpacing(6)

        # Clock
        self.clock_label = QLabel("")
        self.clock_label.setObjectName("topClock")
        tl.addWidget(_item(self.clock_label), 0, Qt.AlignVCenter)

        right.addWidget(top)

        # Pages
        self.stack = QStackedWidget()
        self.page_dashboard = DashboardPage(self.video_service)
        self.page_live = LiveMonitorPage(self.video_service)
        self.page_cameras = CamerasPage(self.video_service)
        self.page_events = EventsPage()
        self.page_watchlist = WatchlistPage()
        self.page_analytics = AnalyticsPage()
        self.page_settings = SettingsPage()

        for p in (
            self.page_dashboard, self.page_live, self.page_cameras,
            self.page_events, self.page_watchlist, self.page_analytics,
            self.page_settings,
        ):
            self.stack.addWidget(p)

        right.addWidget(self.stack, 1)
        root.addLayout(right, 1)
        self._navigate("dashboard")

    def _navigate(self, key: str) -> None:
        titles = {
            "dashboard": "Dashboard",
            "live": "Live Monitor",
            "cameras": "Cameras",
            "events": "Events",
            "watchlist": "Watchlist",
            "analytics": "Analytics",
            "settings": "Settings",
        }
        mapping = {
            "dashboard": 0, "live": 1, "cameras": 2, "events": 3,
            "watchlist": 4, "analytics": 5, "settings": 6,
        }
        self.stack.setCurrentIndex(mapping.get(key, 0))
        self.section_label.setText(titles.get(key, "IBVAP"))
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)

    def _connect_signals(self) -> None:
        sm = self.stream_manager
        sm.frame_ready.connect(self.page_live.on_frame)
        sm.detection_ready.connect(self.page_live.on_detections)
        sm.detection_ready.connect(self._on_detections_persist)
        sm.status_changed.connect(self._on_status)
        sm.error.connect(self._on_error)
        sm.stream_finished.connect(self._on_stream_finished)
        self.page_cameras.request_start.connect(self._start_camera)
        self.page_cameras.request_stop.connect(self._stop_camera)

    @Slot(str)
    def _start_camera(self, camera_id: str) -> None:
        if self.video_service.start(camera_id):
            self.page_cameras.refresh()
            self._update_active_count()

    @Slot(str)
    def _stop_camera(self, camera_id: str) -> None:
        self.video_service.stop(camera_id)
        self.page_cameras.refresh()
        self._update_active_count()

    def _on_detections_persist(self, camera_id: str, dets, faces, anpr) -> None:
        try:
            svc = DetectionService()
            for d in dets or []:
                svc.save_detection(d)
            for f in faces or []:
                svc.save_face(f)
            for a in anpr or []:
                svc.save_anpr(a)
        except Exception:
            pass

    def _on_status(self, camera_id: str, status: str) -> None:
        st = status.strip().title()
        if st.lower() in ("running", "ready", "online"):
            self.status_pill.setText(f"●  {st}")
            self.status_pill.setObjectName("topStatusReady")
        elif st.lower() in ("error", "failed"):
            self.status_pill.setText(f"●  {st}")
            self.status_pill.setObjectName("topStatusError")
        else:
            self.status_pill.setText(f"●  {st}")
            self.status_pill.setObjectName("topStatus")
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)
        self.detail_label.setText(camera_id)
        self.page_cameras.refresh()
        self._update_active_count()

    def _on_error(self, camera_id: str, message: str) -> None:
        self.status_pill.setText("●  Error")
        self.status_pill.setObjectName("topStatusError")
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)
        self.detail_label.setText(camera_id)

    def _on_stream_finished(self, camera_id: str) -> None:
        self.page_cameras.refresh()
        self._update_active_count()
        if not self.video_service.running_list():
            self.status_pill.setText("●  Ready")
            self.status_pill.setObjectName("topStatusReady")
            self.status_pill.style().unpolish(self.status_pill)
            self.status_pill.style().polish(self.status_pill)
            self.detail_label.setText("")

    def _update_active_count(self) -> None:
        n = len(self.video_service.running_list())
        self.streams_pill.setText(f"Streams  {n}")

    def _update_clock(self) -> None:
        self.clock_label.setText(datetime.now().strftime("%Y-%m-%d   %H:%M:%S"))

    def closeEvent(self, event) -> None:
        self.video_service.stop_all()
        import time
        time.sleep(0.3)
        event.accept()
