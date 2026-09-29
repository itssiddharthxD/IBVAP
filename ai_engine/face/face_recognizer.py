"""Face recognizer — local watchlist matching via FaceEngine."""
from __future__ import annotations

from typing import List, Optional, Any
from datetime import datetime
import logging

from core.contracts import FaceResult
from .face_engine import get_face_engine

logger = logging.getLogger(__name__)


class FaceRecognizer:
    def __init__(self, model_path: Optional[str] = None):
        self._engine = get_face_engine()

    def is_ready(self) -> bool:
        return self._engine.can_recognize()

    def get_error(self) -> Optional[str]:
        if self._engine.can_recognize():
            return None
        return self._engine.get_error() or "Recognition backend not available"

    def load_gallery(self, persons: List[dict]) -> None:
        self._engine.set_gallery(persons)

    def embed_image(self, image_bgr) -> Optional[Any]:
        return self._engine.embed_image(image_bgr)

    def recognize_frame(
        self, frame: Any, camera_id: str, timestamp: datetime
    ) -> List[FaceResult]:
        return self._engine.detect_and_match(
            frame, camera_id, timestamp, do_recognize=True
        )
