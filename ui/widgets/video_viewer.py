"""Single camera video tile."""
from __future__ import annotations

from typing import List, Optional
import cv2
import numpy as np

from PySide6.QtWidgets import QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap

from core.contracts import DetectionResult, FaceResult, ANPRResult
from ui.widgets.detection_overlay import draw_detections


class VideoViewer(QLabel):
    clicked = Signal()

    def __init__(self, camera_id: str = "", parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(200, 140)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            "QLabel { background-color:#050505; border:1px solid #2A2A2A; "
            "border-radius:2px; color:#6A6A6A; font-size:11px; font-weight:500; }"
        )
        self.setText("NO SIGNAL")
        self._last_detections: List[DetectionResult] = []
        self._last_faces: List[FaceResult] = []
        self._last_anpr: List[ANPRResult] = []
        self._zones: List[dict] = []
        self._fps = 0.0

    def set_zones(self, zones: Optional[List[dict]]) -> None:
        """Zone dicts with normalized polygon points for this camera."""
        self._zones = list(zones or [])

    def update_frame(
        self,
        frame: np.ndarray,
        fps: float = 0.0,
        detections: Optional[List[DetectionResult]] = None,
        faces: Optional[List[FaceResult]] = None,
        anpr: Optional[List[ANPRResult]] = None,
        zones: Optional[List[dict]] = None,
    ) -> None:
        if detections is not None:
            self._last_detections = detections
        if faces is not None:
            self._last_faces = faces
        if anpr is not None:
            self._last_anpr = anpr
        if zones is not None:
            self._zones = zones
        self._fps = fps

        display = draw_detections(
            frame,
            self._last_detections,
            self._last_faces,
            self._last_anpr,
            zones=self._zones,
        )
        h, w = display.shape[:2]
        bar_h = 22
        overlay = display.copy()
        cv2.rectangle(overlay, (0, 0), (w, bar_h), (10, 10, 10), -1)
        display = cv2.addWeighted(overlay, 0.7, display, 0.3, 0)
        cv2.putText(
            display,
            f"{self.camera_id}   {fps:.0f} FPS",
            (8, 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (200, 200, 200),
            1,
            cv2.LINE_AA,
        )
        # zone count badge
        if self._zones:
            cv2.putText(
                display,
                f"ZONES {len(self._zones)}",
                (w - 90, 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (80, 80, 220),
                1,
                cv2.LINE_AA,
            )
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        self.setPixmap(
            pix.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def clear_view(self) -> None:
        self.clear()
        self.setText("NO SIGNAL")
        self._last_detections = []
        self._last_faces = []
        self._last_anpr = []
        self._zones = []

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)
