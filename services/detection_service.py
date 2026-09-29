"""Persists detection events."""
from __future__ import annotations

from typing import List, Optional
import logging

from database.database import get_session
from database.repositories.event_repository import EventRepository
from database.repositories.anpr_repository import ANPRRepository
from database.models import Event
from core.contracts import DetectionResult, FaceResult, ANPRResult

logger = logging.getLogger(__name__)


def _detach_event(session, obj: Event) -> Event:
    if obj is None:
        return obj
    _ = (
        obj.id,
        obj.event_id,
        obj.event_type,
        obj.camera_id,
        obj.timestamp,
        obj.severity,
        obj.description,
        obj.snapshot,
        obj.track_id,
        obj.person_id,
        obj.plate_text,
        obj.status,
        obj.payload,
    )
    session.expunge(obj)
    return obj


class DetectionService:
    def save_detection(self, det: DetectionResult) -> None:
        with get_session() as session:
            repo = EventRepository(session)
            repo.create(
                event_type="detection",
                camera_id=det.camera_id,
                description=f"{det.class_name} ({det.confidence:.2f})",
                track_id=det.track_id,
                payload=det.to_dict(),
            )

    def save_face(self, face: FaceResult) -> None:
        with get_session() as session:
            repo = EventRepository(session)
            repo.create(
                event_type="face",
                camera_id=face.camera_id,
                description=f"{face.match_status.value} {face.name or ''}",
                person_id=face.person_id,
                payload=face.to_dict(),
            )

    def save_anpr(self, anpr: ANPRResult) -> None:
        with get_session() as session:
            event_repo = EventRepository(session)
            anpr_repo = ANPRRepository(session)
            event_repo.create(
                event_type="anpr",
                camera_id=anpr.camera_id,
                description=f"Plate: {anpr.plate_text}",
                plate_text=anpr.plate_text,
                payload=anpr.to_dict(),
            )
            anpr_repo.create(
                camera_id=anpr.camera_id,
                plate_text=anpr.plate_text,
                confidence=anpr.confidence,
                vehicle_type=anpr.vehicle_type,
                snapshot=anpr.snapshot_path,
                bounding_box=anpr.bounding_box.as_tuple() if anpr.bounding_box else None,
            )

    def recent_events(self, limit: int = 100) -> list:
        with get_session() as session:
            repo = EventRepository(session)
            events = repo.list_recent(limit=limit)
            return [_detach_event(session, e) for e in events]

    def count_detections(self, event_type: str = "detection", hours: int = 24) -> int:
        with get_session() as session:
            repo = EventRepository(session)
            return repo.count_by_type(event_type, since_hours=hours)
