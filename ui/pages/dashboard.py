"""Dashboard — operational overview with metrics + recent activity."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor

from services.camera_service import CameraService
from services.detection_service import DetectionService
from services.video_service import VideoService
from core.config import get_config


class MetricPanel(QFrame):
    def __init__(self, title: str, value: str = "0", accent: str = "#3D9B8F", parent=None):
        super().__init__(parent)
        self.setObjectName("metricPanel")
        self.setMinimumHeight(88)
        self.setStyleSheet(
            f"#metricPanel {{"
            f"  background-color: #161616;"
            f"  border: 1px solid #2A2A2A;"
            f"  border-left: 3px solid {accent};"
            f"  border-radius: 4px;"
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setStyleSheet(
            "background: transparent; border: none; "
            "color: #9A9A9A; font-size: 10px; font-weight: 600; letter-spacing: 0.7px;"
        )
        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(
            "background: transparent; border: none; "
            "color: #EAEAEA; font-size: 26px; font-weight: 600;"
        )
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.value_lbl)
        layout.addStretch()

    def set_value(self, value: str) -> None:
        self.value_lbl.setText(value)


class DashboardPage(QWidget):
    def __init__(self, video_service: VideoService, parent=None):
        super().__init__(parent)
        self.video_service = video_service
        self.camera_service = CameraService()
        self.detection_service = DetectionService()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        head = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        head.addWidget(title)
        head.addStretch()
        self.hint = QLabel("Live local metrics")
        self.hint.setObjectName("pageHint")
        head.addWidget(self.hint)
        root.addLayout(head)

        if get_config().get("application", "demo_mode", default=False):
            demo = QLabel("  DEMO MODE  ")
            demo.setStyleSheet(
                "background:#1A2030; color:#8BB8D0; font-size:10px; "
                "font-weight:700; padding:4px 10px; border:1px solid #2A3A4A; border-radius:3px;"
            )
            root.addWidget(demo)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.metrics = {
            "cameras": MetricPanel("Cameras", accent="#3D9B8F"),
            "online": MetricPanel("Online", accent="#3D9B8F"),
            "offline": MetricPanel("Offline", accent="#6A6A6A"),
            "streams": MetricPanel("Active streams", accent="#3D9B8F"),
            "persons": MetricPanel("Person 24h", accent="#5B8DEF"),
            "anpr": MetricPanel("ANPR 24h", accent="#D4A017"),
            "faces": MetricPanel("Unknown face", accent="#E05555"),
            "events": MetricPanel("Suspicious new", accent="#E07A3D"),
        }
        for r, c, k in [
            (0, 0, "cameras"), (0, 1, "online"), (0, 2, "offline"), (0, 3, "streams"),
            (1, 0, "persons"), (1, 1, "anpr"), (1, 2, "faces"), (1, 3, "events"),
        ]:
            grid.addWidget(self.metrics[k], r, c)
        root.addLayout(grid)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        left = QFrame()
        left.setObjectName("panel")
        left.setMinimumWidth(260)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(14, 12, 14, 12)
        ll.setSpacing(8)
        lt = QLabel("ACTIVE STREAMS")
        lt.setStyleSheet(
            "background:transparent; border:none; color:#9A9A9A; "
            "font-size:10px; font-weight:600; letter-spacing:0.6px;"
        )
        ll.addWidget(lt)
        self.streams_list = QLabel("None")
        self.streams_list.setStyleSheet(
            "background:transparent; border:none; color:#6A6A6A; font-size:12.5px;"
        )
        self.streams_list.setWordWrap(True)
        ll.addWidget(self.streams_list)
        ll.addStretch()
        bottom.addWidget(left, 1)

        right = QFrame()
        right.setObjectName("panel")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(14, 12, 14, 12)
        rl.setSpacing(8)
        rt = QLabel("RECENT EVENTS")
        rt.setStyleSheet(
            "background:transparent; border:none; color:#9A9A9A; "
            "font-size:10px; font-weight:600; letter-spacing:0.6px;"
        )
        rl.addWidget(rt)

        self.events_table = QTableWidget(0, 4)
        self.events_table.setHorizontalHeaderLabels(["Time", "Type", "Camera", "Detail"])
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.events_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.events_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.events_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.events_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.events_table.setFocusPolicy(Qt.NoFocus)
        self.events_table.verticalHeader().setVisible(False)
        self.events_table.setShowGrid(False)
        self.events_table.setAlternatingRowColors(True)
        self.events_table.setMaximumHeight(220)
        rl.addWidget(self.events_table)
        bottom.addWidget(right, 2)

        root.addLayout(bottom)
        root.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(2000)
        self.refresh()

    def refresh(self) -> None:
        cams = self.camera_service.list_cameras()
        running = set(self.video_service.running_list())
        total = len(cams)
        online = len([c for c in cams if c.camera_id in running])

        person = self.detection_service.count_detections("person")
        anpr = self.detection_service.count_detections("anpr")
        face_u = self.detection_service.count_detections("face_unknown")
        try:
            from security.alert_manager import AlertManager
            sus_new = AlertManager().count_new()
        except Exception:
            sus_new = 0

        self.metrics["cameras"].set_value(str(total))
        self.metrics["online"].set_value(str(online))
        self.metrics["offline"].set_value(str(total - online))
        self.metrics["streams"].set_value(str(len(running)))
        self.metrics["persons"].set_value(str(person))
        self.metrics["anpr"].set_value(str(anpr))
        self.metrics["faces"].set_value(str(face_u))
        self.metrics["events"].set_value(str(sus_new))

        if running:
            lines = []
            for cid in sorted(running):
                cam = next((c for c in cams if c.camera_id == cid), None)
                name = cam.name if cam else cid
                lines.append(f"●  {cid}  —  {name}")
            self.streams_list.setText("\n".join(lines))
            self.streams_list.setStyleSheet(
                "background:transparent; border:none; color:#3D9B8F; font-size:12.5px;"
            )
        else:
            self.streams_list.setText("No active streams\nStart a camera from Cameras page")
            self.streams_list.setStyleSheet(
                "background:transparent; border:none; color:#6A6A6A; font-size:12.5px;"
            )

        try:
            events = self.detection_service.recent_events(limit=8)
        except Exception:
            events = []
        self.events_table.setRowCount(0)
        for e in events:
            row = self.events_table.rowCount()
            self.events_table.insertRow(row)
            ts = e.timestamp.strftime("%H:%M:%S") if e.timestamp else "—"
            detail = e.plate_text or e.description or "—"
            if len(detail) > 40:
                detail = detail[:40] + "…"
            vals = [ts, e.event_type, e.camera_id, detail]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if e.event_type == "anpr":
                    item.setForeground(QColor("#D4A017"))
                elif e.event_type in ("face_unknown", "suspicious"):
                    item.setForeground(QColor("#E05555"))
                self.events_table.setItem(row, col, item)
            self.events_table.setRowHeight(row, 28)
