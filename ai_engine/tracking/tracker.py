"""Base tracker interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Any
from core.contracts import DetectionResult


class BaseTracker(ABC):
    @abstractmethod
    def update(self, detections: List[DetectionResult], frame: Any) -> List[DetectionResult]:
        """Assign / update track IDs on detections."""
        ...
