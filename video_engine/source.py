"""Video source abstraction (RTSP, webcam, file)."""
from __future__ import annotations

from typing import Optional, Tuple, Any
import logging
import time

import cv2
import numpy as np

from core.exceptions import CameraError

logger = logging.getLogger(__name__)


class VideoSource:
    def __init__(
        self,
        source: str | int,
        source_type: str,
        reconnect_attempts: int = 5,
        reconnect_delay: float = 3.0,
    ):
        self.source = source
        self.source_type = source_type.lower()
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self._cap: Optional[cv2.VideoCapture] = None
        self._opened = False

    def open(self) -> bool:
        self.close()
        try:
            if self.source_type == "webcam":
                idx = int(self.source)
                self._cap = cv2.VideoCapture(idx)
            elif self.source_type == "rtsp":
                self._cap = cv2.VideoCapture(str(self.source), cv2.CAP_FFMPEG)
                # Prefer TCP for RTSP stability
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
            elif self.source_type == "file":
                self._cap = cv2.VideoCapture(str(self.source))
            else:
                raise CameraError(f"Unsupported source type: {self.source_type}")

            if not self._cap or not self._cap.isOpened():
                raise CameraError(f"Cannot open source: {self.source}")

            self._opened = True
            logger.info("Opened %s source: %s", self.source_type, self.source)
            return True
        except Exception as e:
            logger.error("Failed to open source %s: %s", self.source, e)
            self._opened = False
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self._cap or not self._opened:
            return False, None
        ret, frame = self._cap.read()
        if not ret or frame is None:
            # Try reconnect for live sources
            if self.source_type in ("rtsp", "webcam"):
                for attempt in range(self.reconnect_attempts):
                    logger.warning(
                        "Frame read failed, reconnect attempt %d/%d",
                        attempt + 1,
                        self.reconnect_attempts,
                    )
                    time.sleep(self.reconnect_delay)
                    if self.open():
                        ret, frame = self._cap.read()
                        if ret and frame is not None:
                            return True, frame
            return False, None
        return True, frame

    def get_fps(self) -> float:
        if self._cap and self._opened:
            fps = self._cap.get(cv2.CAP_PROP_FPS)
            return float(fps) if fps and fps > 0 else 25.0
        return 0.0

    def get_resolution(self) -> Tuple[int, int]:
        if self._cap and self._opened:
            w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return w, h
        return 0, 0

    def close(self) -> None:
        if self._cap:
            self._cap.release()
            self._cap = None
        self._opened = False

    @property
    def is_opened(self) -> bool:
        return self._opened
