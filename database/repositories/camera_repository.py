"""Camera repository."""
from __future__ import annotations

from typing import List, Optional, Sequence
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from database.models import Camera, CameraTask


class CameraRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> List[Camera]:
        return list(self.session.scalars(select(Camera).order_by(Camera.camera_id)).all())

    def get_by_camera_id(self, camera_id: str) -> Optional[Camera]:
        return self.session.scalar(select(Camera).where(Camera.camera_id == camera_id))

    def create(
        self,
        camera_id: str,
        name: str,
        source_type: str,
        source: str,
        location: str = "",
        enabled: bool = True,
        ai_profile: str = "General Detection",
        device: str = "AUTO",
        confidence: float = 0.50,
        frame_interval: int = 2,
        tasks: Optional[Sequence[str]] = None,
    ) -> Camera:
        cam = Camera(
            camera_id=camera_id,
            name=name,
            source_type=source_type,
            source=source,
            location=location or None,
            enabled=enabled,
            ai_profile=ai_profile,
            device=device,
            confidence=confidence,
            frame_interval=frame_interval,
        )
        self.session.add(cam)
        self.session.flush()

        if tasks:
            for t in tasks:
                self.session.add(CameraTask(camera_id=camera_id, task_name=t, enabled=True))

        self.session.flush()
        return cam

    def update(self, camera: Camera, **kwargs) -> Camera:
        for k, v in kwargs.items():
            if hasattr(camera, k) and k not in ("id", "camera_id", "created_at"):
                setattr(camera, k, v)
        camera.updated_at = datetime.utcnow()
        self.session.flush()
        return camera

    def set_tasks(self, camera_id: str, task_names: Sequence[str]) -> None:
        # Remove existing
        self.session.execute(delete(CameraTask).where(CameraTask.camera_id == camera_id))
        for name in task_names:
            self.session.add(CameraTask(camera_id=camera_id, task_name=name, enabled=True))
        self.session.flush()

    def delete(self, camera_id: str) -> bool:
        cam = self.get_by_camera_id(camera_id)
        if not cam:
            return False
        self.session.delete(cam)
        self.session.flush()
        return True

    def get_enabled_tasks(self, camera_id: str) -> List[str]:
        rows = self.session.scalars(
            select(CameraTask).where(
                CameraTask.camera_id == camera_id, CameraTask.enabled == True  # noqa: E712
            )
        ).all()
        return [r.task_name for r in rows]
