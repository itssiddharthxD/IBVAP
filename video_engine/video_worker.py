"""Qt-safe video capture + AI processing worker."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
import time
import logging

from PySide6.QtCore import QObject, Signal, QMutex, QMutexLocker

import numpy as np

from core.contracts import DetectionResult, FaceResult, ANPRResult
from core.config import get_config
from video_engine.source import VideoSource
from video_engine.frame_buffer import FrameBuffer
from ai_engine.pipeline import AIPipeline
from ai_engine.task_manager import TaskManager

logger = logging.getLogger(__name__)


class VideoWorker(QObject):
    frame_ready = Signal(str, object, float)  # camera_id, frame (np), fps
    detection_ready = Signal(str, list, list, list)  # camera_id, detections, faces, anpr
    status_changed = Signal(str, str)  # camera_id, status
    fps_changed = Signal(str, float)
    error = Signal(str, str)  # camera_id, message
    finished = Signal(str)  # camera_id

    def __init__(
        self,
        camera_id: str,
        source: str | int,
        source_type: str,
        tasks: List[str],
        device: str = "AUTO",
        confidence: float = 0.5,
        frame_interval: int = 2,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.camera_id = camera_id
        self.source = source
        self.source_type = source_type
        self.task_manager = TaskManager(tasks)
        self.device = device
        self.confidence = confidence
        self.frame_interval = frame_interval

        self._running = False
        self._mutex = QMutex()
        self._source: Optional[VideoSource] = None
        self._pipeline: Optional[AIPipeline] = None
        self._buffer = FrameBuffer(maxsize=get_config().get("video", "buffer_size", default=30))
        self._frame_index = 0
        self._last_fps_time = time.time()
        self._fps_counter = 0
        self._current_fps = 0.0

    def start_work(self) -> None:
        with QMutexLocker(self._mutex):
            if self._running:
                return
            self._running = True

        self.status_changed.emit(self.camera_id, "connecting")
        cfg = get_config()
        self._source = VideoSource(
            self.source,
            self.source_type,
            reconnect_attempts=cfg.get("video", "reconnect_attempts", default=5),
            reconnect_delay=cfg.get("video", "reconnect_delay_sec", default=3),
        )

        if not self._source.open():
            self.error.emit(self.camera_id, f"Cannot open source: {self.source}")
            self.status_changed.emit(self.camera_id, "error")
            self._running = False
            self.finished.emit(self.camera_id)
            return

        self._pipeline = AIPipeline(device=self.device)
        status = self._pipeline.status_report()
        logger.info("Worker %s AI status: %s", self.camera_id, status)
        if self.task_manager.has_anpr() if hasattr(self.task_manager, "has_anpr") else False:
            if status.get("ANPR") != "ready":
                logger.error(
                    "ANPR enabled but OCR not ready for %s: %s — run: pip install easyocr",
                    self.camera_id,
                    status.get("ANPR"),
                )
        self.status_changed.emit(self.camera_id, "running")
        logger.info(
            "Worker started for %s tasks=%s",
            self.camera_id,
            self.task_manager.enabled_tasks(),
        )

        try:
            while True:
                with QMutexLocker(self._mutex):
                    if not self._running:
                        break

                ret, frame = self._source.read()
                if not ret or frame is None:
                    self.error.emit(self.camera_id, "Stream ended or read failed")
                    break

                now = datetime.utcnow()
                self._frame_index += 1
                self._fps_counter += 1

                # FPS calculation
                elapsed = time.time() - self._last_fps_time
                if elapsed >= 1.0:
                    self._current_fps = self._fps_counter / elapsed
                    self._fps_counter = 0
                    self._last_fps_time = time.time()
                    self.fps_changed.emit(self.camera_id, self._current_fps)

                # Emit frame for display (copy to avoid race)
                display_frame = frame.copy()
                self.frame_ready.emit(self.camera_id, display_frame, self._current_fps)

                # AI processing — keep more resolution when ANPR is on (plates need detail)
                if self._pipeline and self.task_manager.enabled_tasks():
                    import cv2
                    h, w = frame.shape[:2]
                    scale = 1.0
                    anpr_on = self.task_manager.has_anpr() if hasattr(self.task_manager, "has_anpr") else (
                        self.task_manager.is_enabled("ANPR / OCR")
                        or self.task_manager.is_enabled("License Plate Detection")
                    )
                    max_w = 960 if anpr_on else 640
                    if w > max_w:
                        scale = max_w / float(w)
                        ai_frame = cv2.resize(
                            frame, (max_w, int(h * scale)), interpolation=cv2.INTER_AREA
                        )
                    else:
                        ai_frame = frame
                    results = self._pipeline.process(
                        ai_frame,
                        self.camera_id,
                        now,
                        self.task_manager,
                        conf_threshold=self.confidence,
                        frame_interval=self.frame_interval,
                    )
                    dets = results.get("detections", [])
                    faces = results.get("faces", [])
                    anpr = results.get("anpr", [])
                    # Map boxes back to full-resolution display coordinates
                    if scale < 1.0:
                        inv = 1.0 / scale
                        for d in dets:
                            b = d.bounding_box
                            b.x1 *= inv; b.y1 *= inv; b.x2 *= inv; b.y2 *= inv
                        for f in faces:
                            b = f.bounding_box
                            b.x1 *= inv; b.y1 *= inv; b.x2 *= inv; b.y2 *= inv
                        for a in anpr:
                            if a.bounding_box is not None:
                                b = a.bounding_box
                                b.x1 *= inv; b.y1 *= inv; b.x2 *= inv; b.y2 *= inv
                    if dets or faces or anpr:
                        self.detection_ready.emit(self.camera_id, dets, faces, anpr)

                # Small sleep to yield
                time.sleep(0.001)

        except Exception as e:
            logger.exception("Worker error %s: %s", self.camera_id, e)
            self.error.emit(self.camera_id, str(e))
        finally:
            if self._source:
                self._source.close()
            self.status_changed.emit(self.camera_id, "stopped")
            self.finished.emit(self.camera_id)
            logger.info("Worker finished for %s", self.camera_id)

    def stop(self) -> None:
        with QMutexLocker(self._mutex):
            self._running = False
