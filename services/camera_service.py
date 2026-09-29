"""Camera CRUD and configuration service."""
from __future__ import annotations

from typing import List, Optional, Sequence
import logging

from sqlalchemy.orm import make_transient

from database.database import get_session
from database.repositories.camera_repository import CameraRepository
from database.models import Camera
from ai_engine.profiles import get_profile_tasks, list_profiles

logger = logging.getLogger(__name__)


def _detach(session, obj: Camera) -> Camera:
    """Safely detach a Camera instance so it can be used outside the session."""
    if obj is None:
        return obj
    # Touch all simple attributes so they are loaded
    _ = (
        obj.id,
        obj.camera_id,
        obj.name,
        obj.source_type,
        obj.source,
        obj.location,
        obj.enabled,
        obj.ai_profile,
        obj.device,
        obj.confidence,
        obj.frame_interval,
        obj.created_at,
        obj.updated_at,
    )
    session.expunge(obj)
    return obj


class CameraService:
    def list_cameras(self) -> List[Camera]:
        with get_session() as session:
            repo = CameraRepository(session)
            cams = repo.list_all()
            return [_detach(session, c) for c in cams]

    def get_camera(self, camera_id: str) -> Optional[Camera]:
        with get_session() as session:
            repo = CameraRepository(session)
            cam = repo.get_by_camera_id(camera_id)
            return _detach(session, cam)

    def add_camera(
        self,
        camera_id: str,
        name: str,
        source_type: str,
        source: str,
        location: str = "",
        ai_profile: str = "General Detection",
        tasks: Optional[Sequence[str]] = None,
        device: str = "AUTO",
        confidence: float = 0.5,
        frame_interval: int = 2,
    ) -> Camera:
        if tasks is None:
            tasks = get_profile_tasks(ai_profile)
        with get_session() as session:
            repo = CameraRepository(session)
            if repo.get_by_camera_id(camera_id):
                raise ValueError(f"Camera ID already exists: {camera_id}")
            cam = repo.create(
                camera_id=camera_id,
                name=name,
                source_type=source_type,
                source=source,
                location=location,
                ai_profile=ai_profile,
                device=device,
                confidence=confidence,
                frame_interval=frame_interval,
                tasks=tasks,
            )
            session.flush()
            return _detach(session, cam)

    def update_camera(self, camera_id: str, **kwargs) -> Optional[Camera]:
        with get_session() as session:
            repo = CameraRepository(session)
            cam = repo.get_by_camera_id(camera_id)
            if not cam:
                return None
            tasks = kwargs.pop("tasks", None)
            repo.update(cam, **kwargs)
            if tasks is not None:
                repo.set_tasks(camera_id, tasks)
            session.flush()
            return _detach(session, cam)

    def delete_camera(self, camera_id: str) -> bool:
        with get_session() as session:
            repo = CameraRepository(session)
            return repo.delete(camera_id)

    def get_tasks(self, camera_id: str) -> List[str]:
        with get_session() as session:
            repo = CameraRepository(session)
            return repo.get_enabled_tasks(camera_id)

    def list_profiles(self) -> List[str]:
        return list_profiles()
