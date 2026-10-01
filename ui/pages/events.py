"""Events page — category filter dropdown + CSV export."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox,
    QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from services.detection_service import DetectionService
from services.export_service import ExportService


CATEGORIES = [
    ("All events", None),
    ("Person Detection", ["person"]),
    ("Vehicle Detection", ["vehicle"]),
    ("Object Detection", ["detection"]),
    ("Face Detection (all)", ["face", "face_matched", "face_unknown"]),
    ("Face — Matched", ["face_matched"]),
    ("Face — Unknown", ["face_unknown"]),
    ("ANPR / Plate", ["anpr"]),
    ("Suspicious Activity", ["suspicious"]),
]

TYPE_COLORS = {
    "person": "#5B9BD5",
    "vehicle": "#70AD47",
    "detection": "#A0A0A0",
    "face": "#C77DFF",
    "face_matched": "#3D9B8F",
    "face_unknown": "#E05555",
    "anpr": "#D4A017",
    "suspicious": "#E07A3D",
}

TYPE_LABELS = {
    "person": "Person",
    "vehicle": "Vehicle",
    "detection": "Object",
    "face": "Face",
    "face_matched": "Face Matched",
    "face_unknown": "Unknown Face",
    "anpr": "ANPR",
    "suspicious": "Suspicious",
}


class EventsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = DetectionService()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Events")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel("Category"))
        self.category = QComboBox()
        self.category.setMinimumWidth(200)
        self.category.setMinimumHeight(28)
        for label, _ in CATEGORIES:
            self.category.addItem(label)
        self.category.currentIndexChanged.connect(self.refresh)
        header.addWidget(self.category)

        btn = QPushButton("Refresh")
        btn.setObjectName("toolBtn")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.refresh)
        header.addWidget(btn)

        btn_ex = QPushButton("Export CSV")
        btn_ex.setObjectName("toolBtn")
        btn_ex.setCursor(Qt.PointingHandCursor)
        btn_ex.clicked.connect(self._export)
        header.addWidget(btn_ex)
        root.addLayout(header)

        hint = QLabel(
            "Filter by category: Person · Vehicle · Face · Unknown Face · ANPR · Suspicious"
        )
        hint.setObjectName("pageHint")
        hint.setStyleSheet(
            "background:transparent; border:none; color:#6A6A6A; font-size:11px;"
        )
        root.addWidget(hint)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Time", "Category", "Camera", "Description", "Track / Plate / Person", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setStyleSheet(
            """
            QTableWidget { background:#0D1A2A; color:#F2F7FB; border:1px solid #1C2B3C; gridline-color:#1C2B3C; }
            QHeaderView::section { background:#0B1726; color:#71859B; border:1px solid #1C2B3C; padding:6px; }
            """
        )
        root.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        idx = self.category.currentIndex()
        types = CATEGORIES[idx][1] if 0 <= idx < len(CATEGORIES) else None
        try:
            events = self.service.recent_events(limit=300, event_types=types)
        except Exception:
            events = []
        self.table.setRowCount(0)
        for e in events:
            row = self.table.rowCount()
            self.table.insertRow(row)
            track_or = (
                e.plate_text
                or e.person_id
                or (str(e.track_id) if e.track_id is not None else "—")
            )
            cat_label = TYPE_LABELS.get(e.event_type, e.event_type)
            vals = [
                e.timestamp.strftime("%Y-%m-%d %H:%M:%S") if e.timestamp else "—",
                cat_label,
                e.camera_id,
                e.description or "—",
                track_or,
                e.status,
            ]
            color = TYPE_COLORS.get(e.event_type, "#EAEAEA")
            for col, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if col == 1:
                    item.setForeground(QColor(color))
                if e.event_type in ("face_unknown", "suspicious"):
                    item.setForeground(QColor(TYPE_COLORS.get(e.event_type, color)))
                self.table.setItem(row, col, item)

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export events", "events.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            out = ExportService.export_events(path)
            QMessageBox.information(self, "Exported", f"Saved:\n{out}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
