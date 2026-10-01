"""Persists detection events — UI always gets plain objects, never ORM."""
from __future__ import annotations

from typing import Optional, Sequence, Any
from datetime import datetime, timedelta
from types import SimpleNamespace
import logging
import threading

from database.database import get_session
from database.repositories.event_repository import EventRepository
from database.repositories.anpr_repository import ANPRRepository
from core.contracts import DetectionResult, FaceResult, ANPRResult, MatchStatus

logger = logging.getLogger(__name__)

VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "bicycle"}

_last_save: dict = {}
_lock = threading.Lock()
_SAVE_INTERVAL_SEC = 3.0


def _should_save(key: str) -> bool:
    now = datetime.utcnow()
    with _lock:
        last = _last_save.get(key)
        if last and (now - last).total_seconds() < _SAVE_INTERVAL_SEC:
            return False
        _last_save[key] = now
        if len(_last_save) > 500:
            cutoff = now - timedelta(seconds=60)
            for k in list(_last_save.keys()):
                if _last_save[k] < cutoff:
                    del _last_save[k]
        return True


def _dict_to_ns(d: dict) -> SimpleNamespace:
    return SimpleNamespace(**d)


class DetectionService:
    def save_detection(self, det: DetectionResult) -> None:
        cn = (det.class_name or "").lower()
        if cn == "person":
            etype = "person"
        elif cn in VEHICLE_CLASSES:
            etype = "vehicle"
        else:
            etype = "detection"
        tid = det.track_id if det.track_id is not None else -1
        key = f"{det.camera_id}:{etype}:{tid}:{cn}"
        if not _should_save(key):
            return
        try:
            with get_session() as session:
                EventRepository(session).create(
                    event_type=etype,
                    camera_id=det.camera_id,
                    description=f"{det.class_name} ({det.confidence:.2f})",
                    track_id=det.track_id,
                    payload=det.to_dict(),
                )
        except Exception:
            logger.exception("save_detection failed")

    def save_face(self, face: FaceResult) -> None:
        if face.match_status == MatchStatus.MATCHED:
            etype = "face_matched"
            desc = f"MATCHED {face.name or face.person_id or ''}"
        elif face.match_status == MatchStatus.UNKNOWN:
            etype = "face_unknown"
            desc = "UNKNOWN face"
        else:
            etype = "face"
            desc = f"{face.match_status.value} {face.name or ''}"
        key = f"{face.camera_id}:{etype}:{face.person_id or 'x'}"
        if not _should_save(key):
            return
        try:
            with get_session() as session:
                EventRepository(session).create(
                    event_type=etype,
                    camera_id=face.camera_id,
                    description=desc.strip(),
                    person_id=face.person_id,
                    severity="high" if etype == "face_unknown" else "info",
                    payload=face.to_dict(),
                )
        except Exception:
            logger.exception("save_face failed")

    def save_anpr(self, anpr: ANPRResult) -> None:
        plate = (anpr.plate_text or "").strip().upper()
        key = f"{anpr.camera_id}:anpr:{plate}"
        if not _should_save(key):
            return
        try:
            with get_session() as session:
                EventRepository(session).create(
                    event_type="anpr",
                    camera_id=anpr.camera_id,
                    description=f"Plate: {anpr.plate_text}",
                    plate_text=anpr.plate_text,
                    payload=anpr.to_dict(),
                )
                ANPRRepository(session).create(
                    camera_id=anpr.camera_id,
                    plate_text=anpr.plate_text,
                    confidence=anpr.confidence,
                    vehicle_type=anpr.vehicle_type,
                    snapshot=anpr.snapshot_path,
                    bounding_box=anpr.bounding_box.as_tuple() if anpr.bounding_box else None,
                )
        except Exception:
            logger.exception("save_anpr failed")

    def recent_events(
        self,
        limit: int = 100,
        event_types: Optional[Sequence[str]] = None,
    ) -> list:
        try:
            with get_session() as session:
                rows = EventRepository(session).list_recent(
                    limit=limit, event_types=event_types, as_dict=True
                )
                return [_dict_to_ns(d) for d in rows]
        except Exception:
            logger.exception("recent_events failed")
            return []

    def count_detections(self, event_type: str = "detection", hours: int = 24) -> int:
        try:
            with get_session() as session:
                return EventRepository(session).count_by_type(
                    event_type, since_hours=hours
                )
        except Exception:
            logger.exception("count_detections failed")
            return 0
