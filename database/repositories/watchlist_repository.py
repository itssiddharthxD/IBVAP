"""Watchlist repository."""
from __future__ import annotations

from typing import List, Optional
from datetime import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import WatchlistPerson


class WatchlistRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self, active_only: bool = False) -> List[WatchlistPerson]:
        q = select(WatchlistPerson).order_by(WatchlistPerson.name)
        if active_only:
            q = q.where(WatchlistPerson.status == "active")
        return list(self.session.scalars(q).all())

    def get(self, person_id: str) -> Optional[WatchlistPerson]:
        return self.session.scalar(
            select(WatchlistPerson).where(WatchlistPerson.person_id == person_id)
        )

    def create(
        self,
        name: str,
        reference_image: Optional[str] = None,
        embedding: Optional[bytes] = None,
        notes: Optional[str] = None,
        person_id: Optional[str] = None,
    ) -> WatchlistPerson:
        pid = person_id or str(uuid.uuid4())[:8].upper()
        person = WatchlistPerson(
            person_id=pid,
            name=name,
            reference_image=reference_image,
            embedding=embedding,
            status="active",
            notes=notes,
        )
        self.session.add(person)
        self.session.flush()
        return person

    def update(self, person: WatchlistPerson, **kwargs) -> WatchlistPerson:
        for k, v in kwargs.items():
            if hasattr(person, k) and k not in ("id", "person_id", "created_at"):
                setattr(person, k, v)
        person.updated_at = datetime.utcnow()
        self.session.flush()
        return person

    def delete(self, person_id: str) -> bool:
        p = self.get(person_id)
        if not p:
            return False
        self.session.delete(p)
        self.session.flush()
        return True
