"""Central Rule Manager — load, CRUD, cache enabled rules."""
from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any

from database.database import get_session
from database.models import SecurityRule
from database.repositories.security_rule_repository import SecurityRuleRepository
from security.rule_types import defaults_for

logger = logging.getLogger(__name__)


def _detach(session, obj: SecurityRule) -> SecurityRule:
    if obj is None:
        return obj
    for attr in (
        "id", "rule_id", "name", "rule_type", "camera_id", "object_type",
        "enabled", "severity", "zone", "line", "duration_sec", "min_count",
        "direction_deg", "direction_tolerance_deg", "speed_threshold",
        "window_sec", "cooldown_sec", "schedule_start_hour", "schedule_end_hour",
        "record_on_alert", "params", "created_at", "updated_at",
    ):
        getattr(obj, attr, None)
    session.expunge(obj)
    return obj


class RuleManager:
    """Singleton-style manager; call reload() after external DB changes."""

    _instance: Optional["RuleManager"] = None

    def __init__(self):
        self._cache: List[SecurityRule] = []
        self.reload()
        self._ensure_default_unknown_face_rule()

    @classmethod
    def instance(cls) -> "RuleManager":
        if cls._instance is None:
            cls._instance = RuleManager()
        return cls._instance

    def reload(self) -> None:
        try:
            with get_session() as session:
                repo = SecurityRuleRepository(session)
                rows = repo.list_all(enabled_only=False)
                self._cache = [_detach(session, r) for r in rows]
            logger.info("RuleManager loaded %d rules", len(self._cache))
        except Exception:
            logger.exception("RuleManager reload failed")
            self._cache = []

    def list_rules(self, enabled_only: bool = False) -> List[SecurityRule]:
        if enabled_only:
            return [r for r in self._cache if r.enabled]
        return list(self._cache)

    def rules_for_camera(self, camera_id: str) -> List[SecurityRule]:
        return [
            r for r in self._cache
            if r.enabled and (r.camera_id in ("", "*", camera_id))
        ]

    def get(self, rule_id: str) -> Optional[SecurityRule]:
        for r in self._cache:
            if r.rule_id == rule_id:
                return r
        return None

    def create_rule(self, data: Dict[str, Any]) -> SecurityRule:
        with get_session() as session:
            repo = SecurityRuleRepository(session)
            rtype = data.get("rule_type", "loitering")
            defs = defaults_for(rtype)
            for k, v in defs.items():
                data.setdefault(k, v)
            # Map severity from defaults if stored under that key
            if "severity" not in data and "severity" in defs:
                data["severity"] = defs["severity"]
            row = repo.create(**data)
            session.flush()
            out = _detach(session, row)
        self.reload()
        return out

    def update_rule(self, rule_id: str, data: Dict[str, Any]) -> Optional[SecurityRule]:
        with get_session() as session:
            repo = SecurityRuleRepository(session)
            row = repo.update(rule_id, **data)
            if not row:
                return None
            out = _detach(session, row)
        self.reload()
        return out

    def delete_rule(self, rule_id: str) -> bool:
        with get_session() as session:
            repo = SecurityRuleRepository(session)
            ok = repo.delete(rule_id)
        if ok:
            self.reload()
        return ok

    def set_enabled(self, rule_id: str, enabled: bool) -> Optional[SecurityRule]:
        return self.update_rule(rule_id, {"enabled": enabled})

    def _ensure_default_unknown_face_rule(self) -> None:
        """Create a default enabled Unknown Face rule if none exists."""
        existing = [r for r in self._cache if r.rule_type == "unknown_face"]
        if existing:
            return
        try:
            with get_session() as session:
                repo = SecurityRuleRepository(session)
                data = {
                    "name": "Unknown Face Alert",
                    "rule_type": "unknown_face",
                    "camera_id": "*",
                    "object_type": "person",
                    "severity": "high",
                    "enabled": True,
                    "cooldown_sec": 30.0,
                }
                defs = defaults_for("unknown_face")
                for k, v in defs.items():
                    data.setdefault(k, v)
                row = repo.create(**data)
                session.flush()
                self._cache.append(_detach(session, row))
            logger.info("Created default Unknown Face security rule")
        except Exception:
            logger.exception("Could not create default unknown_face rule")
