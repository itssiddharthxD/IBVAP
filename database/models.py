"""SQLAlchemy models for IBVAP."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(512), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_profile: Mapped[str] = mapped_column(String(64), default="General Detection")
    device: Mapped[str] = mapped_column(String(16), default="AUTO")
    confidence: Mapped[float] = mapped_column(Float, default=0.50)
    frame_interval: Mapped[int] = mapped_column(Integer, default=2)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tasks: Mapped[List["CameraTask"]] = relationship(
        "CameraTask", back_populates="camera", cascade="all, delete-orphan"
    )


class CameraTask(Base):
    __tablename__ = "camera_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("cameras.camera_id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_name: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    camera: Mapped["Camera"] = relationship("Camera", back_populates="tasks")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    camera_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="info")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snapshot: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    track_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    person_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    plate_text: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="new")
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class WatchlistPerson(Base):
    __tablename__ = "watchlist_persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    reference_image: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    embedding: Mapped[Optional[bytes]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class WatchlistPlate(Base):
    """Blacklist / whitelist number plates."""
    __tablename__ = "watchlist_plates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plate_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    plate_text: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    list_type: Mapped[str] = mapped_column(String(16), default="blacklist")  # blacklist | whitelist
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ANPREvent(Base):
    __tablename__ = "anpr_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    plate_text: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    vehicle_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    snapshot: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    bounding_box: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class SecurityRule(Base):
    __tablename__ = "security_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    camera_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(32), default="person")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    severity: Mapped[str] = mapped_column(String(32), default="medium")
    zone: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Line crossing: two points [[x1,y1],[x2,y2]] normalized
    line: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    direction_deg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    direction_tolerance_deg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    speed_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    window_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cooldown_sec: Mapped[float] = mapped_column(Float, default=30.0)
    # Schedule: active hours (None = always)
    schedule_start_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    schedule_end_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    record_on_alert: Mapped[bool] = mapped_column(Boolean, default=False)
    params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class SuspiciousActivity(Base):
    __tablename__ = "suspicious_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    rule_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    camera_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="medium")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snapshot: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    recording: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    track_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    object_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    zone_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    count_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    person_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    plate_text: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="new")
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
