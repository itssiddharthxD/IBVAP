from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class Detection:
    class_id: int
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]
    track_id: int | None = None

@dataclass
class VideoFrame:
    frame: Any
    source: str
    timestamp: datetime

@dataclass
class SecurityEvent:
    event_type: str
    severity: str
    camera: str
    timestamp: datetime
    message: str
    detection: Detection | None = None
    snapshot_path: str | None = None
