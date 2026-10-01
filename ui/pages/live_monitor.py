"""Live multi-viewer — production VMS style with security zone overlays."""
from __future__ import annotations

from typing import Dict, List
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QGridLayout,
)
from PySide6.QtCore import Qt

from ui.widgets.video_viewer import VideoViewer
from services.video_service import VideoService
from services.camera_service import CameraService
from security.rule_manager import RuleManager
from security.rule_types import rule_type_label


class LiveMonitorPage(QWidget):
    def __init__(self, video_service: VideoService, parent=None):
        super().__init__(parent)
        self.video_service = video_service
        self.camera_service = CameraService()
        self._viewers: Dict[str, VideoViewer] = {}
        self._grid_mode = "2x2"
        self._zones_by_camera: Dict[str, List[dict]] = {}

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

        self.btn_zones = QPushButton("Reload zones")
        self.btn_zones.setObjectName("toolBtn")
        self.btn_zones.setCursor(Qt.PointingHandCursor)
        self.btn_zones.setToolTip("Reload security rule zones from database")
        self.btn_zones.clicked.connect(self.reload_zones)
        toolbar.addWidget(self.btn_zones)
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

    def reload_zones(self) -> None:
        """Load enabled rules that have a polygon zone, grouped by camera."""
        self._zones_by_camera = {}
        try:
            mgr = RuleManager.instance()
            mgr.reload()
            for rule in mgr.list_rules(enabled_only=True):
                zone = rule.zone
                line = getattr(rule, "line", None)
                if (not zone or len(zone) < 3) and (not line or len(line) < 2):
                    continue
                pts = zone if zone and len(zone) >= 2 else line
                entry = {
                    "points": pts,
                    "label": rule.name or rule_type_label(rule.rule_type),
                    "rule_type": rule.rule_type,
                    "normalized": True,
                }
                # Apply to specific camera or all
                if rule.camera_id in ("", "*", None):
                    cams = self.camera_service.list_cameras()
                    targets = [c.camera_id for c in cams]
                else:
                    targets = [rule.camera_id]
                for cid in targets:
                    self._zones_by_camera.setdefault(cid, []).append(entry)
        except Exception:
            self._zones_by_camera = {}

        for cid, viewer in self._viewers.items():
            viewer.set_zones(self._zones_by_camera.get(cid, []))

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

        self.reload_zones()

        for i in range(n):
            r, c = divmod(i, cols)
            if i < len(cams):
                cam = cams[i]
                viewer = VideoViewer(camera_id=cam.camera_id)
                viewer.set_zones(self._zones_by_camera.get(cam.camera_id, []))
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
            zones = self._zones_by_camera.get(camera_id, [])
            viewer.update_frame(frame, fps=fps, zones=zones)

    def on_detections(self, camera_id: str, dets, faces, anpr) -> None:
        viewer = self._viewers.get(camera_id)
        if viewer:
            viewer._last_detections = dets
            viewer._last_faces = faces
            viewer._last_anpr = anpr

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.reload_zones()
