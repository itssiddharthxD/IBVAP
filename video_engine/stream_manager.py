"""Manages multiple concurrent camera streams."""
from __future__ import annotations

from typing import Dict, Optional, List, Callable
import logging

from PySide6.QtCore import QObject, QThread, Signal

from video_engine.video_worker import VideoWorker

logger = logging.getLogger(__name__)


class StreamManager(QObject):
    frame_ready = Signal(str, object, float)
    detection_ready = Signal(str, list, list, list)
    status_changed = Signal(str, str)
    fps_changed = Signal(str, float)
    error = Signal(str, str)
    stream_finished = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._workers: Dict[str, VideoWorker] = {}
        self._threads: Dict[str, QThread] = {}

    def start_camera(
        self,
        camera_id: str,
        source: str | int,
        source_type: str,
        tasks: List[str],
        device: str = "AUTO",
        confidence: float = 0.5,
        frame_interval: int = 2,
    ) -> bool:
        if camera_id in self._workers:
            logger.warning("Camera %s already running", camera_id)
            return False

        worker = VideoWorker(
            camera_id=camera_id,
            source=source,
            source_type=source_type,
            tasks=tasks,
            device=device,
            confidence=confidence,
            frame_interval=frame_interval,
        )
        thread = QThread()
        worker.moveToThread(thread)

        # Connect signals
        worker.frame_ready.connect(self.frame_ready)
        worker.detection_ready.connect(self.detection_ready)
        worker.status_changed.connect(self.status_changed)
        worker.fps_changed.connect(self.fps_changed)
        worker.error.connect(self.error)
        worker.finished.connect(self._on_worker_finished)

        thread.started.connect(worker.start_work)
        thread.start()

        self._workers[camera_id] = worker
        self._threads[camera_id] = thread
        logger.info("Started stream for %s", camera_id)
        return True

    def stop_camera(self, camera_id: str) -> None:
        worker = self._workers.get(camera_id)
        if worker:
            worker.stop()

    def stop_all(self) -> None:
        for cid in list(self._workers.keys()):
            self.stop_camera(cid)

    def is_running(self, camera_id: str) -> bool:
        return camera_id in self._workers

    def running_cameras(self) -> List[str]:
        return list(self._workers.keys())

    def _on_worker_finished(self, camera_id: str) -> None:
        thread = self._threads.pop(camera_id, None)
        self._workers.pop(camera_id, None)
        if thread:
            thread.quit()
            thread.wait(3000)
            thread.deleteLater()
        self.stream_finished.emit(camera_id)
        logger.info("Cleaned up stream for %s", camera_id)
