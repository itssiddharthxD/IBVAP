"""ANPR event repository."""
from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from database.models import ANPREvent


class ANPRRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        camera_id: str,
        plate_text: str,
        confidence: float,
        vehicle_type: Optional[str] = None,
        snapshot: Optional[str] = None,
        bounding_box: Optional[dict] = None,
    ) -> ANPREvent:
        evt = ANPREvent(
            camera_id=camera_id,
            timestamp=datetime.utcnow(),
            plate_text=plate_text,
            confidence=confidence,
            vehicle_type=vehicle_type,
            snapshot=snapshot,
            bounding_box=bounding_box,
        )
        self.session.add(evt)
        self.session.flush()
        return evt

    def list_recent(self, limit: int = 100) -> List[ANPREvent]:
        q = select(ANPREvent).order_by(desc(ANPREvent.timestamp)).limit(limit)
        return list(self.session.scalars(q).all())
