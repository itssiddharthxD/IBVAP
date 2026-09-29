"""
Common data contracts used across AI engine, services and UI.
UI and services must consume these instead of model internals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple, List, Any
from enum import Enum


class MatchStatus(str, Enum):
    MATCHED = "MATCHED"
    UNKNOWN = "UNKNOWN"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NO_FACE = "NO_FACE"


@dataclass
class BoundingBox:
    """Normalized or pixel bounding box (x1, y1, x2, y2)."""
    x1: float
    y1: float
    x2: float
    y2: float

    def as_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x1, self.y1, self.x2, self.y2)

    def to_int(self) -> Tuple[int, int, int, int]:
        return (int(self.x1), int(self.y1), int(self.x2), int(self.y2))


@dataclass
class DetectionResult:
    """Standard object detection result (person, vehicle, etc.)."""
    camera_id: str
    timestamp: datetime
    class_name: str
    confidence: float
    bounding_box: BoundingBox
    track_id: Optional[int] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bounding_box": self.bounding_box.as_tuple(),
            "track_id": self.track_id,
            "extra": self.extra,
        }


@dataclass
class FaceResult:
    """Face detection + recognition result."""
    camera_id: str
    timestamp: datetime
    bounding_box: BoundingBox
    confidence: float
    person_id: Optional[str] = None
    match_status: MatchStatus = MatchStatus.UNKNOWN
    similarity: float = 0.0
    name: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "bounding_box": self.bounding_box.as_tuple(),
            "confidence": self.confidence,
            "person_id": self.person_id,
            "match_status": self.match_status.value,
            "similarity": self.similarity,
            "name": self.name,
        }


@dataclass
class ANPRResult:
    """Automatic Number Plate Recognition result."""
    camera_id: str
    timestamp: datetime
    plate_text: str
    confidence: float
    vehicle_type: Optional[str] = None
    bounding_box: Optional[BoundingBox] = None
    snapshot_path: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "plate_text": self.plate_text,
            "confidence": self.confidence,
            "vehicle_type": self.vehicle_type,
            "bounding_box": self.bounding_box.as_tuple() if self.bounding_box else None,
            "snapshot_path": self.snapshot_path,
        }


@dataclass
class FramePacket:
    """Frame + metadata passed through the pipeline."""
    camera_id: str
    frame: Any  # numpy.ndarray
    timestamp: datetime
    frame_index: int = 0
    fps: float = 0.0
