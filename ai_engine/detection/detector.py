"""Base detector interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Any
from datetime import datetime

from core.contracts import DetectionResult, BoundingBox


class BaseDetector(ABC):
    """Interface so detectors can be swapped without changing callers."""

    @abstractmethod
    def is_ready(self) -> bool:
        """Return True if model is loaded and ready."""
        ...

    @abstractmethod
    def detect(
        self,
        frame: Any,
        camera_id: str,
        timestamp: datetime,
        conf_threshold: float = 0.5,
    ) -> List[DetectionResult]:
        ...

    @property
    @abstractmethod
    def model_path(self) -> str:
        ...
