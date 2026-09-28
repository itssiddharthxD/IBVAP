from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    Text,
    Float,
    Integer,
    Boolean,
)

from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now
    )

    camera: Mapped[str] = mapped_column(
        String(255)
    )

    event_type: Mapped[str] = mapped_column(
        String(100)
    )

    severity: Mapped[str] = mapped_column(
        String(30)
    )

    message: Mapped[str] = mapped_column(
        Text
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    snapshot_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(255)
    )

    location: Mapped[str] = mapped_column(
        String(255)
    )

    source_type: Mapped[str] = mapped_column(
        String(50)
    )

    source: Mapped[str] = mapped_column(
        String(500)
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="OFFLINE"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now
    )