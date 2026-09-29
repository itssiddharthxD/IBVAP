"""ByteTrack wrapper. Relies on Ultralytics tracker when available."""
from __future__ import annotations

from typing import List, Any
import logging

from core.contracts import DetectionResult
from .tracker import BaseTracker

logger = logging.getLogger(__name__)


class ByteTrackTracker(BaseTracker):
    """
    Lightweight tracker.
    When YOLO is run with track=True Ultralytics already provides IDs.
    This class is a pass-through / placeholder for future custom BoT-SORT.
    """

    def __init__(self):
        self._enabled = True

    def update(self, detections: List[DetectionResult], frame: Any) -> List[DetectionResult]:
        # IDs are already populated by YOLO track mode if used.
        # For pure detect mode we leave track_id as-is (None).
        return detections
