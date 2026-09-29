"""Camera management — production table layout."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QDialogButtonBox,
    QCheckBox, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from services.camera_service import CameraService
from services.video_service import VideoService
from ai_engine.profiles import AI_PROFILES, ALL_TASKS, get_profile_tasks


class CameraDialog(QDialog):
    def __init__(self, parent=None, camera=None, running: bool = False):
        super().__init__(parent)
        self.setWindowTitle("Edit camera" if camera else "Add camera")
        self.setMinimumWidth(440)
        self.camera = camera
        self.running = running

        layout = QFormLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        self.camera_id = QLineEdit()
        self.name = QLineEdit()
        self.source_type = QComboBox()
        self.source_type.addItems(["rtsp", "webcam", "file"])
        self.source = QLineEdit()
        self.source.setPlaceholderText("rtsp://...  or  0  or  path/to/video.mp4")
        self.location = QLineEdit()
        self.profile = QComboBox()
        self.profile.addItems(list(AI_PROFILES.keys()))
        self.device = QComboBox()
        self.device.addItems(["AUTO", "CPU", "GPU"])
        self.confidence = QDoubleSpinBox()
        self.confidence.setRange(0.1, 0.99)
        self.confidence.setSingleStep(0.05)
        self.confidence.setValue(0.45)
        self.frame_interval = QSpinBox()
        self.frame_interval.setRange(1, 30)
        self.frame_interval.setValue(3)

        self.task_checks = {}
        task_box = QVBoxLayout()
        task_box.setSpacing(3)
        for t in ALL_TASKS:
            cb = QCheckBox(t)
            self.task_checks[t] = cb
            task_box.addWidget(cb)

        layout.addRow("Camera ID", self.camera_id)
        layout.addRow("Name", self.name)
        layout.addRow("Source type", self.source_type)
        layout.addRow("Source", self.source)
        layout.addRow("Location", self.location)
        layout.addRow("AI profile", self.profile)
        layout.addRow("Device", self.device)
        layout.addRow("Confidence", self.confidence)
        layout.addRow("Frame interval", self.frame_interval)
        layout.addRow("Tasks", QWidget())
        layout.addRow(task_box)

        self.profile.currentTextChanged.connect(self._on_profile_changed)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if camera:
            self.camera_id.setText(camera.camera_id)
            self.camera_id.setEnabled(False)
            self.name.setText(camera.name)
            self.source_type.setCurrentText(camera.source_type)
            self.source.setText(camera.source)
            self.location.setText(camera.location or "")
            self.profile.setCurrentText(camera.ai_profile)
            self.device.setCurrentText(camera.device)
            self.confidence.setValue(camera.confidence)
            self.frame_interval.setValue(camera.frame_interval)

        if running:
            for w in (self.name, self.source_type, self.source, self.location,
                      self.profile, self.device, self.confidence, self.frame_interval):
                w.setEnabled(False)
            for cb in self.task_checks.values():
                cb.setEnabled(False)
            warn = QLabel("Stop the camera before changing configuration.")
            warn.setStyleSheet("color:#C75B5B;")
            layout.insertRow(0, warn)

    def _on_profile_changed(self, name: str) -> None:
        if name == "Custom":
            return
        defaults = set(get_profile_tasks(name))
        for t, cb in self.task_checks.items():
            cb.setChecked(t in defaults)

    def get_data(self) -> dict:
        tasks = [t for t, cb in self.task_checks.items() if cb.isChecked()]
        return {
            "camera_id": self.camera_id.text().strip(),
            "name": self.name.text().strip(),
            "source_type": self.source_type.currentText(),
            "source": self.source.text().strip(),
            "location": self.location.text().strip(),
            "ai_profile": self.profile.currentText(),
            "device": self.device.currentText(),
            "confidence": self.confidence.value(),
            "frame_interval": self.frame_interval.value(),
            "tasks": tasks,
        }


class CamerasPage(QWidget):
    request_start = Signal(str)
    request_stop = Signal(str)

    def __init__(self, video_service: VideoService, parent=None):
        super().__init__(parent)
        self.video_service = video_service
        self.camera_service = CameraService()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Cameras")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        def btn(text, primary=False):
            b = QPushButton(text)
            b.setObjectName("toolBtnPrimary" if primary else "toolBtn")
            b.setCursor(Qt.PointingHandCursor)
            return b

        self.btn_add = btn("Add camera", primary=True)
        self.btn_edit = btn("Edit")
        self.btn_delete = btn("Delete")
        self.btn_start = btn("Start")
        self.btn_stop = btn("Stop")
        self.btn_refresh = btn("Refresh")

        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_start.clicked.connect(self._start)
        self.btn_stop.clicked.connect(self._stop)
        self.btn_refresh.clicked.connect(self.refresh)

        for b in (self.btn_add, self.btn_edit, self.btn_delete,
                  self.btn_start, self.btn_stop, self.btn_refresh):
            header.addWidget(b)
        root.addLayout(header)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Name", "Type", "Location", "Profile", "Tasks", "Status", "FPS"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        root.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        cams = self.camera_service.list_cameras()
        running = set(self.video_service.running_list())
        self.table.setRowCount(0)
        for cam in cams:
            row = self.table.rowCount()
            self.table.insertRow(row)
            tasks = self.camera_service.get_tasks(cam.camera_id)
            task_str = " + ".join(
                t.replace(" Detection", "").replace(" / OCR", "") for t in tasks[:3]
            )
            if len(tasks) > 3:
                task_str += "…"
            status = "ONLINE" if cam.camera_id in running else "OFFLINE"
            vals = [
                cam.camera_id, cam.name, cam.source_type.upper(),
                cam.location or "—", cam.ai_profile, task_str or "—",
                status, "—",
            ]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if col in (6, 7):
                    item.setTextAlignment(Qt.AlignCenter)
                if col == 6:
                    if status == "ONLINE":
                        item.setForeground(QColor("#3D9B8F"))
                    else:
                        item.setForeground(QColor("#6A6A6A"))
                self.table.setItem(row, col, item)
            self.table.setRowHeight(row, 32)

    def _selected_id(self) -> Optional[str]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        return self.table.item(rows[0].row(), 0).text()

    def _add(self) -> None:
        dlg = CameraDialog(self)
        dlg._on_profile_changed(dlg.profile.currentText())
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if not data["camera_id"] or not data["name"] or not data["source"]:
                QMessageBox.warning(self, "Validation", "Camera ID, Name and Source are required.")
                return
            try:
                self.camera_service.add_camera(**data)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _edit(self) -> None:
        cid = self._selected_id()
        if not cid:
            return
        cam = self.camera_service.get_camera(cid)
        if not cam:
            return
        running = self.video_service.is_running(cid)
        dlg = CameraDialog(self, camera=cam, running=running)
        tasks = set(self.camera_service.get_tasks(cid))
        for t, cb in dlg.task_checks.items():
            cb.setChecked(t in tasks)
        if dlg.exec() == QDialog.Accepted:
            if running:
                QMessageBox.information(
                    self, "Info", "Stop the camera before changing configuration."
                )
                return
            data = dlg.get_data()
            data.pop("camera_id", None)
            self.camera_service.update_camera(cid, **data)
            self.refresh()

    def _delete(self) -> None:
        cid = self._selected_id()
        if not cid:
            return
        if self.video_service.is_running(cid):
            QMessageBox.warning(self, "Running", "Stop the camera before deleting.")
            return
        if QMessageBox.question(self, "Confirm", f"Delete camera {cid}?") == QMessageBox.Yes:
            self.camera_service.delete_camera(cid)
            self.refresh()

    def _start(self) -> None:
        cid = self._selected_id()
        if cid:
            self.request_start.emit(cid)

    def _stop(self) -> None:
        cid = self._selected_id()
        if cid:
            self.request_stop.emit(cid)
