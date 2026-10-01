"""Plate blacklist / whitelist CRUD."""
from __future__ import annotations

import uuid
from typing import List, Optional

from database.database import get_session
from database.models import WatchlistPlate
from sqlalchemy import select


def _detach(session, obj):
    if obj is None:
        return obj
    for a in ("id", "plate_id", "plate_text", "list_type", "notes", "status", "created_at"):
        getattr(obj, a, None)
    session.expunge(obj)
    return obj


class PlateWatchlistService:
    def list_plates(self, list_type: Optional[str] = None, active_only: bool = True) -> List[WatchlistPlate]:
        with get_session() as session:
            q = select(WatchlistPlate)
            if list_type:
                q = q.where(WatchlistPlate.list_type == list_type)
            if active_only:
                q = q.where(WatchlistPlate.status == "active")
            rows = list(session.scalars(q).all())
            return [_detach(session, r) for r in rows]

    def add(self, plate_text: str, list_type: str = "blacklist", notes: str = "") -> WatchlistPlate:
        plate_text = plate_text.strip().upper().replace(" ", "")
        with get_session() as session:
            row = WatchlistPlate(
                plate_id=f"plt_{uuid.uuid4().hex[:10]}",
                plate_text=plate_text,
                list_type=list_type,
                notes=notes or None,
                status="active",
            )
            session.add(row)
            session.flush()
            return _detach(session, row)

    def delete(self, plate_id: str) -> bool:
        with get_session() as session:
            row = session.scalars(
                select(WatchlistPlate).where(WatchlistPlate.plate_id == plate_id)
            ).first()
            if not row:
                return False
            session.delete(row)
            session.flush()
            return True

    def is_blacklisted(self, plate_text: str) -> bool:
        plate_text = (plate_text or "").strip().upper().replace(" ", "")
        with get_session() as session:
            row = session.scalars(
                select(WatchlistPlate).where(
                    WatchlistPlate.plate_text == plate_text,
                    WatchlistPlate.list_type == "blacklist",
                    WatchlistPlate.status == "active",
                )
            ).first()
            return row is not None

    def normalized_blacklist(self) -> set:
        return {p.plate_text for p in self.list_plates("blacklist")}
