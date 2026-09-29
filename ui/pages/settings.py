"""Settings page."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDoubleSpinBox,
    QSpinBox, QCheckBox, QPushButton, QFormLayout, QGroupBox, QMessageBox,
)
from PySide6.QtCore import Qt

from core.config import get_config
from services.system_service import SystemService


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cfg = get_config()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # AI
        ai_box = QGroupBox("AI")
        ai_form = QFormLayout(ai_box)
        ai_form.setContentsMargins(14, 18, 14, 14)
        ai_form.setSpacing(10)
        ai_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        ai_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.device = QComboBox()
        self.device.addItems(["AUTO", "CPU", "GPU"])
        self.device.setCurrentText(self.cfg.get("ai", "device", default="AUTO"))
        self.device.setMinimumHeight(30)

        self.confidence = QDoubleSpinBox()
        self.confidence.setRange(0.1, 0.99)
        self.confidence.setSingleStep(0.05)
        self.confidence.setValue(float(self.cfg.get("ai", "confidence", default=0.5)))
        self.confidence.setMinimumHeight(30)

        self.frame_interval = QSpinBox()
        self.frame_interval.setRange(1, 30)
        self.frame_interval.setValue(int(self.cfg.get("ai", "frame_interval", default=2)))
        self.frame_interval.setMinimumHeight(30)

        lbl_style = "background:transparent; border:none; color:#9A9A9A;"
        for text, widget in [
            ("Device", self.device),
            ("Confidence", self.confidence),
            ("Frame interval", self.frame_interval),
        ]:
            lab = QLabel(text)
            lab.setStyleSheet(lbl_style)
            lab.setMinimumWidth(110)
            ai_form.addRow(lab, widget)
        root.addWidget(ai_box)

        # Application
        app_box = QGroupBox("Application")
        app_form = QFormLayout(app_box)
        app_form.setContentsMargins(14, 18, 14, 14)
        app_form.setSpacing(10)

        self.demo = QCheckBox("Demo mode")
        self.demo.setChecked(bool(self.cfg.get("application", "demo_mode", default=False)))
        self.demo.setStyleSheet("background:transparent; border:none;")

        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level.setCurrentText(
            self.cfg.get("application", "logging_level", default="INFO")
        )
        self.log_level.setMinimumHeight(30)

        app_form.addRow(self.demo)
        lab2 = QLabel("Logging level")
        lab2.setStyleSheet(lbl_style)
        lab2.setMinimumWidth(110)
        app_form.addRow(lab2, self.log_level)
        root.addWidget(app_box)

        info = SystemService.get_system_info()
        sys_lbl = QLabel(
            f"OS: {info['os']}  ·  Python: {info['python']}  ·  AI device: {info['ai_device']}"
        )
        sys_lbl.setObjectName("pageHint")
        sys_lbl.setStyleSheet(
            "background:transparent; border:none; color:#6A6A6A; font-size:11px;"
        )
        root.addWidget(sys_lbl)

        btn = QPushButton("Save settings")
        btn.setObjectName("toolBtnPrimary")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(32)
        btn.clicked.connect(self._save)
        root.addWidget(btn, alignment=Qt.AlignLeft)
        root.addStretch()

    def _save(self) -> None:
        self.cfg.set("ai", "device", value=self.device.currentText())
        self.cfg.set("ai", "confidence", value=self.confidence.value())
        self.cfg.set("ai", "frame_interval", value=self.frame_interval.value())
        self.cfg.set("application", "demo_mode", value=self.demo.isChecked())
        self.cfg.set("application", "logging_level", value=self.log_level.currentText())
        try:
            self.cfg.save_local()
            QMessageBox.information(self, "Saved", "Settings saved to local_config.json")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
