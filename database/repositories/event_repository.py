"""Event repository."""
from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from database.models import Event


class EventRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        event_type: str,
        camera_id: str,
        description: str = "",
        severity: str = "info",
        snapshot: Optional[str] = None,
        track_id: Optional[int] = None,
        person_id: Optional[str] = None,
        plate_text: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> Event:
        evt = Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            camera_id=camera_id,
            timestamp=datetime.utcnow(),
            severity=severity,
            description=description,
            snapshot=snapshot,
            track_id=track_id,
            person_id=person_id,
            plate_text=plate_text,
            status="new",
            payload=payload,
        )
        self.session.add(evt)
        self.session.flush()
        return evt

    def list_recent(self, limit: int = 100, camera_id: Optional[str] = None) -> List[Event]:
        q = select(Event).order_by(desc(Event.timestamp)).limit(limit)
        if camera_id:
            q = q.where(Event.camera_id == camera_id)
        return list(self.session.scalars(q).all())

    def count_by_type(self, event_type: str, since_hours: int = 24) -> int:
        since = datetime.utcnow() - timedelta(hours=since_hours)
        q = select(Event).where(Event.event_type == event_type, Event.timestamp >= since)
        return len(list(self.session.scalars(q).all()))
