"""High-level video stream control."""
from __future__ import annotations

from typing import List, Optional
import logging

from video_engine.stream_manager import StreamManager
from services.camera_service import CameraService

logger = logging.getLogger(__name__)


class VideoService:
    def __init__(self, stream_manager: StreamManager):
        self.stream_manager = stream_manager
        self.camera_service = CameraService()

    def start(self, camera_id: str) -> bool:
        cam = self.camera_service.get_camera(camera_id)
        if not cam:
            logger.error("Camera not found: %s", camera_id)
            return False
        if not cam.enabled:
            logger.warning("Camera disabled: %s", camera_id)
            return False
        if self.stream_manager.is_running(camera_id):
            return True

        tasks = self.camera_service.get_tasks(camera_id)
        return self.stream_manager.start_camera(
            camera_id=cam.camera_id,
            source=cam.source,
            source_type=cam.source_type,
            tasks=tasks,
            device=cam.device,
            confidence=cam.confidence,
            frame_interval=cam.frame_interval,
        )

    def stop(self, camera_id: str) -> None:
        self.stream_manager.stop_camera(camera_id)

    def stop_all(self) -> None:
        self.stream_manager.stop_all()

    def is_running(self, camera_id: str) -> bool:
        return self.stream_manager.is_running(camera_id)

    def running_list(self) -> List[str]:
        return self.stream_manager.running_cameras()
