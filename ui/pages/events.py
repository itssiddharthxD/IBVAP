"""Events page."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt

from services.detection_service import DetectionService


class EventsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = DetectionService()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title = QLabel("Events")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        btn = QPushButton("Refresh")
        btn.setObjectName("toolBtn")
        btn.clicked.connect(self.refresh)
        header.addWidget(btn)
        root.addLayout(header)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Time", "Type", "Camera", "Description", "Track / Plate", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet(
            """
            QTableWidget { background:#0D1A2A; color:#F2F7FB; border:1px solid #1C2B3C; gridline-color:#1C2B3C; }
            QHeaderView::section { background:#0B1726; color:#71859B; border:1px solid #1C2B3C; padding:6px; }
            """
        )
        root.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        events = self.service.recent_events(limit=200)
        self.table.setRowCount(0)
        for e in events:
            row = self.table.rowCount()
            self.table.insertRow(row)
            track_or_plate = e.plate_text or (str(e.track_id) if e.track_id is not None else "—")
            vals = [
                e.timestamp.strftime("%Y-%m-%d %H:%M:%S") if e.timestamp else "—",
                e.event_type,
                e.camera_id,
                e.description or "—",
                track_or_plate,
                e.status,
            ]
            for col, v in enumerate(vals):
                self.table.setItem(row, col, QTableWidgetItem(str(v)))
