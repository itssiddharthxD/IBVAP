"""Alert / Event Manager — persist suspicious activities + optional short recording."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from database.database import get_session
from database.models import SuspiciousActivity
from database.repositories.security_rule_repository import SuspiciousActivityRepository
from database.repositories.event_repository import EventRepository
from core.config import get_config

logger = logging.getLogger(__name__)

# In-memory queue of recent alert ids for UI badge
_RECENT_ALERT_IDS: List[str] = []


def _detach(session, obj: SuspiciousActivity):
    """Return a plain copy safe to use after session closes."""
    if obj is None:
        return obj

    class Plain:
        pass

    p = Plain()
    for attr in (
        "id", "activity_id", "rule_id", "rule_name", "activity_type", "camera_id",
        "timestamp", "severity", "description", "snapshot", "recording", "track_id",
        "object_type", "zone_name", "duration_sec", "count_value", "confidence",
        "person_id", "plate_text", "status", "payload",
    ):
        val = getattr(obj, attr, None)
        if attr == "payload" and val is not None:
            val = dict(val)
        setattr(p, attr, val)
    return p


class AlertManager:
    def create_alert(
        self,
        *,
        rule_id: Optional[str],
        rule_name: str,
        activity_type: str,
        camera_id: str,
        timestamp: datetime,
        severity: str = "medium",
        description: str = "",
        track_id: Optional[int] = None,
        object_type: Optional[str] = None,
        zone_name: Optional[str] = None,
        duration_sec: Optional[float] = None,
        count_value: Optional[int] = None,
        confidence: Optional[float] = None,
        snapshot_path: Optional[str] = None,
        plate_text: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        record_on_alert: bool = False,
        frame=None,
    ) -> SuspiciousActivity:
        activity_id = f"sus_{uuid.uuid4().hex[:12]}"
        recording_path = None
        if record_on_alert and frame is not None:
            recording_path = self._save_alert_clip(frame, camera_id, activity_id)

        with get_session() as session:
            repo = SuspiciousActivityRepository(session)
            row = repo.create(
                activity_id=activity_id,
                rule_id=rule_id,
                rule_name=rule_name,
                activity_type=activity_type,
                camera_id=camera_id,
                timestamp=timestamp,
                severity=severity,
                description=description,
                snapshot=snapshot_path,
                recording=recording_path,
                track_id=track_id,
                object_type=object_type,
                zone_name=zone_name,
                duration_sec=duration_sec,
                count_value=count_value,
                confidence=confidence,
                plate_text=plate_text,
                status="new",
                payload=payload or {},
            )
            EventRepository(session).create(
                event_type="suspicious",
                camera_id=camera_id,
                severity=severity,
                description=f"[{rule_name}] {description}",
                track_id=track_id,
                plate_text=plate_text,
                snapshot=snapshot_path,
                payload={
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "activity_type": activity_type,
                    **(payload or {}),
                },
            )
            session.flush()
            out = _detach(session, row)

        _RECENT_ALERT_IDS.append(activity_id)
        if len(_RECENT_ALERT_IDS) > 50:
            del _RECENT_ALERT_IDS[:-50]
        return out

    def _save_alert_clip(self, frame, camera_id: str, activity_id: str) -> Optional[str]:
        """Save a still as alert artifact (full multi-frame clip needs ring buffer)."""
        try:
            import cv2
            cfg = get_config()
            base = Path(cfg.get("storage", "recording_path", default="data/recordings"))
            base.mkdir(parents=True, exist_ok=True)
            path = base / f"alert_{camera_id}_{activity_id}.jpg"
            cv2.imwrite(str(path), frame)
            return str(path)
        except Exception:
            logger.exception("alert recording save failed")
            return None

    def save_snapshot(self, frame, camera_id: str, prefix: str = "sus") -> Optional[str]:
        try:
            import cv2
            cfg = get_config()
            base = Path(cfg.get("storage", "snapshot_path", default="data/snapshots"))
            base.mkdir(parents=True, exist_ok=True)
            name = f"{prefix}_{camera_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
            path = base / name
            cv2.imwrite(str(path), frame)
            return str(path)
        except Exception:
            logger.exception("snapshot save failed")
            return None

    def recent(self, limit: int = 200, **filters) -> List[SuspiciousActivity]:
        with get_session() as session:
            repo = SuspiciousActivityRepository(session)
            rows = repo.list_filtered(limit=limit, **filters)
            return [_detach(session, r) for r in rows]

    def acknowledge(self, activity_id: str) -> bool:
        with get_session() as session:
            return SuspiciousActivityRepository(session).set_status(activity_id, "acknowledged")

    def resolve(self, activity_id: str) -> bool:
        with get_session() as session:
            return SuspiciousActivityRepository(session).set_status(activity_id, "resolved")

    def count_new(self) -> int:
        with get_session() as session:
            return SuspiciousActivityRepository(session).count_new()

    @staticmethod
    def pop_recent_alert_ids() -> List[str]:
        ids = list(_RECENT_ALERT_IDS)
        _RECENT_ALERT_IDS.clear()
        return ids
