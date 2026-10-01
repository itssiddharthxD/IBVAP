"""Delete old snapshots, recordings, and optional DB rows past retention_days."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from core.config import get_config
from database.database import get_session
from database.models import Event, SuspiciousActivity, ANPREvent

logger = logging.getLogger(__name__)


class RetentionService:
    @staticmethod
    def run() -> dict:
        cfg = get_config()
        days = int(cfg.get("storage", "retention_days", default=30) or 30)
        cutoff = datetime.utcnow() - timedelta(days=days)
        stats = {"files": 0, "events": 0, "suspicious": 0, "anpr": 0}

        for key in ("snapshot_path", "recording_path"):
            base = Path(cfg.get("storage", key, default=f"data/{key.split('_')[0]}s"))
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if not p.is_file():
                    continue
                try:
                    mtime = datetime.utcfromtimestamp(p.stat().st_mtime)
                    if mtime < cutoff:
                        p.unlink(missing_ok=True)
                        stats["files"] += 1
                except Exception:
                    pass

        try:
            with get_session() as session:
                for model, key in (
                    (Event, "events"),
                    (SuspiciousActivity, "suspicious"),
                    (ANPREvent, "anpr"),
                ):
                    q = session.query(model).filter(model.timestamp < cutoff)
                    n = q.count()
                    q.delete(synchronize_session=False)
                    stats[key] = n
                session.commit()
        except Exception:
            logger.exception("retention DB cleanup failed")

        logger.info("Retention cleanup (%sd): %s", days, stats)
        return stats
