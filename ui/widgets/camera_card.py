"""Compact camera summary card (used sparingly)."""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt

from ui.widgets.status_badge import StatusBadge


class CameraCard(QFrame):
    def __init__(self, camera_id: str, name: str, status: str = "stopped", parent=None):
        super().__init__(parent)
        self.setObjectName("cameraCard")
        self.setStyleSheet(
            """
            #cameraCard {
                background-color: #0D1A2A;
                border: 1px solid #1C2B3C;
                border-radius: 4px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        top = QHBoxLayout()
        self.id_label = QLabel(camera_id)
        self.id_label.setStyleSheet("color: #62D8CF; font-weight: 600; font-size: 12px;")
        top.addWidget(self.id_label)
        top.addStretch()
        self.badge = StatusBadge(status=status, text=status)
        top.addWidget(self.badge)
        layout.addLayout(top)

        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("color: #F2F7FB; font-size: 13px;")
        layout.addWidget(self.name_label)
