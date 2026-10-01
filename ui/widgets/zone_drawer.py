"""Polygon zone drawer on a still frame / placeholder canvas."""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtWidgets import QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QPolygon, QMouseEvent

import numpy as np


class ZoneDrawer(QLabel):
    """Click to add polygon vertices; right-click or Finish to close.

    Zone is stored as normalized [[x,y], ...] in 0..1 relative to image size.
    """

    zone_changed = Signal(list)  # list of [x,y] normalized

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 270)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            "background:#0D1A2A; border:1px solid #1C2B3C; color:#71859B;"
        )
        self.setText("Load a camera frame or start stream,\nthen click to draw polygon vertices.\nRight-click to undo last point.")
        self.setMouseTracking(True)

        self._image: Optional[QImage] = None
        self._points: List[QPoint] = []  # pixel coords in label image space
        self._img_w = 1
        self._img_h = 1
        self._drawing = True

    def set_frame(self, frame_bgr: np.ndarray) -> None:
        """Accept OpenCV BGR frame."""
        import cv2
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        self._img_w, self._img_h = w, h
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
        self._image = qimg
        self._redraw()

    def set_zone(self, zone: Optional[list]) -> None:
        """Load existing normalized zone."""
        self._points = []
        if zone and self._img_w > 1:
            for p in zone:
                self._points.append(
                    QPoint(int(float(p[0]) * self._img_w), int(float(p[1]) * self._img_h))
                )
        self._redraw()
        self.zone_changed.emit(self.get_zone())

    def get_zone(self) -> list:
        if not self._points or self._img_w < 2:
            return []
        return [
            [round(p.x() / self._img_w, 4), round(p.y() / self._img_h, 4)]
            for p in self._points
        ]

    def clear_zone(self) -> None:
        self._points = []
        self._redraw()
        self.zone_changed.emit([])

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._image is None:
            return
        # Map click from label coords to image coords
        pix = self.pixmap()
        if pix is None:
            return
        lw, lh = self.width(), self.height()
        pw, ph = pix.width(), pix.height()
        ox = (lw - pw) // 2
        oy = (lh - ph) // 2
        x = event.position().x() - ox
        y = event.position().y() - oy
        if x < 0 or y < 0 or x >= pw or y >= ph:
            return
        # scale to original image
        sx = self._img_w / pw
        sy = self._img_h / ph
        pt = QPoint(int(x * sx), int(y * sy))

        if event.button() == Qt.LeftButton:
            self._points.append(pt)
            self._redraw()
            self.zone_changed.emit(self.get_zone())
        elif event.button() == Qt.RightButton:
            if self._points:
                self._points.pop()
                self._redraw()
                self.zone_changed.emit(self.get_zone())

    def _redraw(self) -> None:
        if self._image is None:
            return
        canvas = QImage(self._image)
        painter = QPainter(canvas)
        pen = QPen(QColor("#E05555"), 2)
        painter.setPen(pen)
        brush = QColor(224, 85, 85, 60)
        if len(self._points) >= 3:
            poly = QPolygon(self._points)
            painter.setBrush(brush)
            painter.drawPolygon(poly)
        for i, p in enumerate(self._points):
            painter.setBrush(QColor("#E05555"))
            painter.drawEllipse(p, 4, 4)
            if i > 0:
                painter.drawLine(self._points[i - 1], p)
        if len(self._points) >= 3:
            painter.drawLine(self._points[-1], self._points[0])
        painter.end()
        self.setPixmap(
            QPixmap.fromImage(canvas).scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._redraw()
