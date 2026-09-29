"""Status badge — light UI."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class StatusBadge(QLabel):
    COLORS = {
        "online": ("#E8F5E9", "#2E7D32"),
        "offline": ("#FFEBEE", "#C62828"),
        "running": ("#E8F5E9", "#2E7D32"),
        "stopped": ("#F5F5F5", "#757575"),
        "error": ("#FFEBEE", "#C62828"),
        "connecting": ("#FFF8E1", "#F9A825"),
        "demo": ("#E3F2FD", "#1565C0"),
    }

    def __init__(self, text: str = "—", status: str = "stopped", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(22)
        self.setMinimumWidth(70)
        font = QFont()
        font.setPointSize(9)
        font.setWeight(QFont.DemiBold)
        self.setFont(font)
        self.set_status(status, text)

    def set_status(self, status: str, text: str | None = None) -> None:
        bg, fg = self.COLORS.get(status.lower(), self.COLORS["stopped"])
        if text is not None:
            self.setText(text.upper())
        self.setStyleSheet(
            f"QLabel {{ background-color:{bg}; color:{fg}; border:1px solid {fg}55;"
            f" border-radius:3px; padding:2px 8px; }}"
        )
