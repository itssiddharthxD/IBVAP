"""CRUD for SecurityRule and query helpers for SuspiciousActivity."""
from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from database.models import SecurityRule, SuspiciousActivity


class SecurityRuleRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, **kwargs) -> SecurityRule:
        if "rule_id" not in kwargs or not kwargs["rule_id"]:
            kwargs["rule_id"] = f"rule_{uuid.uuid4().hex[:12]}"
        row = SecurityRule(**kwargs)
        self.session.add(row)
        self.session.flush()
        return row

    def update(self, rule_id: str, **kwargs) -> Optional[SecurityRule]:
        row = self.get(rule_id)
        if not row:
            return None
        for k, v in kwargs.items():
            if hasattr(row, k):
                setattr(row, k, v)
        row.updated_at = datetime.utcnow()
        self.session.flush()
        return row

    def delete(self, rule_id: str) -> bool:
        row = self.get(rule_id)
        if not row:
            return False
        self.session.delete(row)
        self.session.flush()
        return True

    def get(self, rule_id: str) -> Optional[SecurityRule]:
        return self.session.scalars(
            select(SecurityRule).where(SecurityRule.rule_id == rule_id)
        ).first()

    def list_all(self, enabled_only: bool = False) -> List[SecurityRule]:
        q = select(SecurityRule).order_by(SecurityRule.name)
        if enabled_only:
            q = q.where(SecurityRule.enabled.is_(True))
        return list(self.session.scalars(q).all())

    def list_for_camera(self, camera_id: str, enabled_only: bool = True) -> List[SecurityRule]:
        q = select(SecurityRule).where(
            (SecurityRule.camera_id == camera_id)
            | (SecurityRule.camera_id == "")
            | (SecurityRule.camera_id == "*")
        )
        if enabled_only:
            q = q.where(SecurityRule.enabled.is_(True))
        return list(self.session.scalars(q).all())


class SuspiciousActivityRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, **kwargs) -> SuspiciousActivity:
        if "activity_id" not in kwargs:
            kwargs["activity_id"] = f"sus_{uuid.uuid4().hex[:12]}"
        row = SuspiciousActivity(**kwargs)
        self.session.add(row)
        self.session.flush()
        return row

    def list_filtered(
        self,
        limit: int = 200,
        rule_name: Optional[str] = None,
        camera_id: Optional[str] = None,
        activity_type: Optional[str] = None,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[SuspiciousActivity]:
        q = select(SuspiciousActivity).order_by(desc(SuspiciousActivity.timestamp))
        if rule_name:
            q = q.where(SuspiciousActivity.rule_name == rule_name)
        if camera_id:
            q = q.where(SuspiciousActivity.camera_id == camera_id)
        if activity_type:
            q = q.where(SuspiciousActivity.activity_type == activity_type)
        if status:
            q = q.where(SuspiciousActivity.status == status)
        if since:
            q = q.where(SuspiciousActivity.timestamp >= since)
        if until:
            q = q.where(SuspiciousActivity.timestamp <= until)
        q = q.limit(limit)
        return list(self.session.scalars(q).all())

    def set_status(self, activity_id: str, status: str) -> bool:
        row = self.session.scalars(
            select(SuspiciousActivity).where(
                SuspiciousActivity.activity_id == activity_id
            )
        ).first()
        if not row:
            return False
        row.status = status
        self.session.flush()
        return True

    def count_new(self) -> int:
        from sqlalchemy import func
        return (
            self.session.query(func.count(SuspiciousActivity.id))
            .filter(SuspiciousActivity.status == "new")
            .scalar()
            or 0
        )
