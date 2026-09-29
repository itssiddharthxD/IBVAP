"""License plate detector stub."""
from __future__ import annotations

from pathlib import Path
from typing import List, Any, Optional
from datetime import datetime
import logging

from core.contracts import DetectionResult, BoundingBox
from core.config import get_config, PROJECT_ROOT

logger = logging.getLogger(__name__)


class PlateDetector:
    def __init__(self, model_path: Optional[str] = None):
        cfg = get_config()
        self._model_path = model_path or cfg.get(
            "ai", "model_paths", "plate_detector", default="models/plate_detector.pt"
        )
        self._ready = False
        self._error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        path = Path(self._model_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if not path.exists():
            self._error = f"Plate detector model not found:\n{path}"
            logger.warning(self._error)
            return
        self._error = f"Plate detector model present but inference not yet wired.\n{path}"
        logger.info(self._error)

    def is_ready(self) -> bool:
        return self._ready

    def get_error(self) -> Optional[str]:
        return self._error

    def detect(self, frame: Any, camera_id: str, timestamp: datetime) -> List[DetectionResult]:
        return []
