"""Analytics foundation page."""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

from services.detection_service import DetectionService


class AnalyticsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = DetectionService()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Analytics")
        title.setStyleSheet("color: #F2F7FB; ")
        root.addWidget(title)

        note = QLabel(
            "Detection counts and trends are derived from the local event database.\n"
            "Charts can be added later without changing the data layer."
        )
        note.setStyleSheet("color: #71859B;")
        root.addWidget(note)

        panel = QFrame()
        panel.setStyleSheet("background:#0D1A2A; border:1px solid #1C2B3C; border-radius:4px;")
        pl = QVBoxLayout(panel)
        self.summary = QLabel()
        self.summary.setStyleSheet("color: #F2F7FB; padding: 12px;")
        pl.addWidget(self.summary)
        root.addWidget(panel)
        root.addStretch()
        self.refresh()

    def refresh(self) -> None:
        det = self.service.count_detections("detection", 24)
        face = self.service.count_detections("face", 24)
        anpr = self.service.count_detections("anpr", 24)
        self.summary.setText(
            f"Last 24 hours\n\n"
            f"• Object detections : {det}\n"
            f"• Face events       : {face}\n"
            f"• ANPR events       : {anpr}\n"
        )
