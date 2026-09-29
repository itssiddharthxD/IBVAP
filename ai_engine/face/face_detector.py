"""Face detector — delegates to FaceEngine."""
from __future__ import annotations

from typing import List, Any, Optional
from datetime import datetime
import logging

from core.contracts import FaceResult
from .face_engine import get_face_engine

logger = logging.getLogger(__name__)


class FaceDetector:
    def __init__(self, model_path: Optional[str] = None):
        self._engine = get_face_engine()

    def is_ready(self) -> bool:
        return self._engine.is_ready()

    def get_error(self) -> Optional[str]:
        return self._engine.get_error()

    def detect(
        self, frame: Any, camera_id: str, timestamp: datetime, conf: float = 0.5
    ) -> List[FaceResult]:
        return self._engine.detect_and_match(
            frame, camera_id, timestamp, conf_threshold=conf, do_recognize=False
        )
