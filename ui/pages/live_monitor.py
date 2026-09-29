"""Live multi-viewer — production VMS style."""
from __future__ import annotations

from typing import Dict
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QGridLayout,
)
from PySide6.QtCore import Qt

from ui.widgets.video_viewer import VideoViewer
from services.video_service import VideoService
from services.camera_service import CameraService


class LiveMonitorPage(QWidget):
    def __init__(self, video_service: VideoService, parent=None):
        super().__init__(parent)
        self.video_service = video_service
        self.camera_service = CameraService()
        self._viewers: Dict[str, VideoViewer] = {}
        self._grid_mode = "2x2"

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        toolbar = QHBoxLayout()
        title = QLabel("Live Monitor")
        title.setObjectName("pageTitle")
        toolbar.addWidget(title)
        toolbar.addStretch()

        toolbar.addWidget(QLabel("Layout"))
        self.grid_combo = QComboBox()
        self.grid_combo.addItems(["1 × 1", "2 × 2", "3 × 3"])
        self.grid_combo.setCurrentIndex(1)
        self.grid_combo.setFixedWidth(90)
        self.grid_combo.currentIndexChanged.connect(self._change_grid)
        toolbar.addWidget(self.grid_combo)

        self.btn_refresh = QPushButton("Refresh layout")
        self.btn_refresh.setObjectName("toolBtn")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self._rebuild_grid)
        toolbar.addWidget(self.btn_refresh)
        root.addLayout(toolbar)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(4)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.grid_container, 1)
        self._rebuild_grid()

    def _change_grid(self, idx: int) -> None:
        self._grid_mode = ["1x1", "2x2", "3x3"][idx]
        self._rebuild_grid()

    def _rebuild_grid(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        self._viewers.clear()

        cams = self.camera_service.list_cameras()
        n = {"1x1": 1, "2x2": 4, "3x3": 9}[self._grid_mode]
        cols = {"1x1": 1, "2x2": 2, "3x3": 3}[self._grid_mode]

        for i in range(n):
            r, c = divmod(i, cols)
            if i < len(cams):
                cam = cams[i]
                viewer = VideoViewer(camera_id=cam.camera_id)
                self._viewers[cam.camera_id] = viewer
                self.grid_layout.addWidget(viewer, r, c)
            else:
                ph = QLabel("No camera assigned")
                ph.setAlignment(Qt.AlignCenter)
                ph.setStyleSheet(
                    "background:#050505; border:1px solid #2A2A2A; color:#6A6A6A; font-size:11px; border-radius:2px;"
                )
                self.grid_layout.addWidget(ph, r, c)

    def on_frame(self, camera_id: str, frame: np.ndarray, fps: float) -> None:
        viewer = self._viewers.get(camera_id)
        if viewer:
            viewer.update_frame(frame, fps=fps)

    def on_detections(self, camera_id: str, dets, faces, anpr) -> None:
        viewer = self._viewers.get(camera_id)
        if viewer:
            viewer._last_detections = dets
            viewer._last_faces = faces
            viewer._last_anpr = anpr
