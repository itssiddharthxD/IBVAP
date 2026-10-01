"""Analytics — simple density heatmap + export."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap

import numpy as np

from services.detection_service import DetectionService
from services.export_service import ExportService
from database.database import get_session
from database.models import Event
from sqlalchemy import select


class AnalyticsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = DetectionService()
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        hdr = QHBoxLayout()
        title = QLabel("Analytics")
        title.setObjectName("pageTitle")
        hdr.addWidget(title)
        hdr.addStretch()

        btn_hm = QPushButton("Refresh heatmap")
        btn_hm.setObjectName("toolBtn")
        btn_hm.clicked.connect(self._build_heatmap)
        hdr.addWidget(btn_hm)

        btn_ev = QPushButton("Export events CSV")
        btn_ev.setObjectName("toolBtn")
        btn_ev.clicked.connect(self._export_events)
        hdr.addWidget(btn_ev)

        btn_su = QPushButton("Export suspicious CSV")
        btn_su.setObjectName("toolBtn")
        btn_su.clicked.connect(self._export_suspicious)
        hdr.addWidget(btn_su)
        root.addLayout(hdr)

        hint = QLabel(
            "Heatmap uses last 24h person detection centers from event payloads (approximate)."
        )
        hint.setObjectName("pageHint")
        root.addWidget(hint)

        self.heat_label = QLabel("No heatmap data yet")
        self.heat_label.setMinimumHeight(280)
        self.heat_label.setAlignment(Qt.AlignCenter)
        self.heat_label.setStyleSheet(
            "background:#0D1A2A; border:1px solid #1C2B3C; color:#6A6A6A;"
        )
        root.addWidget(self.heat_label)

        self.stats = QTableWidget(0, 2)
        self.stats.setHorizontalHeaderLabels(["Metric", "Value"])
        self.stats.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats.setMaximumHeight(200)
        root.addWidget(self.stats)
        self._build_heatmap()

    def _build_heatmap(self) -> None:
        grid = np.zeros((24, 32), dtype=np.float32)
        counts = {"person": 0, "vehicle": 0, "face_unknown": 0, "suspicious": 0, "anpr": 0}
        try:
            with get_session() as session:
                since = datetime.utcnow() - timedelta(hours=24)
                rows = list(session.scalars(
                    select(Event).where(Event.timestamp >= since).limit(2000)
                ).all())
            for e in rows:
                et = e.event_type or ""
                if et in counts:
                    counts[et] += 1
                payload = e.payload or {}
                bb = payload.get("bounding_box")
                if bb and len(bb) >= 4 and et in ("person", "detection"):
                    cx = (float(bb[0]) + float(bb[2])) / 2
                    cy = (float(bb[1]) + float(bb[3])) / 2
                    # assume normalized or scale if large
                    if cx > 1.5 or cy > 1.5:
                        cx, cy = cx / 1280.0, cy / 720.0
                    xi = int(min(31, max(0, cx * 32)))
                    yi = int(min(23, max(0, cy * 24)))
                    grid[yi, xi] += 1
        except Exception:
            pass

        if grid.max() > 0:
            grid = grid / grid.max()
            # colorize
            img = np.zeros((24, 32, 3), dtype=np.uint8)
            for y in range(24):
                for x in range(32):
                    v = grid[y, x]
                    img[y, x] = (int(40 + 180 * v), int(20 + 80 * v), int(30 + 200 * v))
            # upscale
            import cv2
            img = cv2.resize(img, (640, 360), interpolation=cv2.INTER_NEAREST)
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, 640, 360, rgb.strides[0], QImage.Format_RGB888).copy()
            self.heat_label.setPixmap(QPixmap.fromImage(qimg))
        else:
            self.heat_label.setText("No person detection points in last 24h")

        self.stats.setRowCount(0)
        for k, v in counts.items():
            r = self.stats.rowCount()
            self.stats.insertRow(r)
            self.stats.setItem(r, 0, QTableWidgetItem(k))
            self.stats.setItem(r, 1, QTableWidgetItem(str(v)))

    def _export_events(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export events", "events.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            out = ExportService.export_events(path)
            QMessageBox.information(self, "Exported", f"Saved:\n{out}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _export_suspicious(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export suspicious", "suspicious.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            out = ExportService.export_suspicious(path)
            QMessageBox.information(self, "Exported", f"Saved:\n{out}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
