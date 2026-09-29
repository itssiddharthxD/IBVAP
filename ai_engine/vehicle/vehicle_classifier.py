"""Vehicle type classifier (separate from basic YOLO detection)."""
from __future__ import annotations

from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Mapping from YOLO class to finer vehicle type
YOLO_TO_VEHICLE = {
    "car": "car",
    "motorcycle": "motorcycle",
    "bus": "bus",
    "truck": "truck",
    "bicycle": "bicycle",
}


class VehicleClassifier:
    """Simple rule-based classifier on top of detection class names.
    Can later be replaced by a dedicated classifier model.
    """

    def classify(self, class_name: str) -> Optional[str]:
        return YOLO_TO_VEHICLE.get(class_name.lower())
