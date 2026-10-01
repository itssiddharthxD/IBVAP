"""CSV export for events and suspicious activities."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from database.database import get_session
from database.models import Event, SuspiciousActivity
from sqlalchemy import select, desc


class ExportService:
    @staticmethod
    def export_events(path: str, limit: int = 5000) -> str:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with get_session() as session:
            rows = list(session.scalars(
                select(Event).order_by(desc(Event.timestamp)).limit(limit)
            ).all())
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "event_type", "camera_id", "description",
                        "track_id", "person_id", "plate_text", "severity", "status"])
            for e in rows:
                w.writerow([
                    e.timestamp.isoformat() if e.timestamp else "",
                    e.event_type, e.camera_id, e.description or "",
                    e.track_id or "", e.person_id or "", e.plate_text or "",
                    e.severity, e.status,
                ])
        return str(out)

    @staticmethod
    def export_suspicious(path: str, limit: int = 5000) -> str:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with get_session() as session:
            rows = list(session.scalars(
                select(SuspiciousActivity).order_by(desc(SuspiciousActivity.timestamp)).limit(limit)
            ).all())
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "rule_name", "activity_type", "camera_id",
                        "description", "track_id", "severity", "status", "snapshot"])
            for e in rows:
                w.writerow([
                    e.timestamp.isoformat() if e.timestamp else "",
                    e.rule_name, e.activity_type, e.camera_id,
                    e.description or "", e.track_id or "",
                    e.severity, e.status, e.snapshot or "",
                ])
        return str(out)
