"""IBVAP Core package."""
from .config import AppConfig
from .contracts import DetectionResult, FaceResult, ANPRResult, BoundingBox
from .exceptions import IBVAPError, ModelNotFoundError, CameraError, ConfigError

__all__ = [
    "AppConfig",
    "DetectionResult",
    "FaceResult",
    "ANPRResult",
    "BoundingBox",
    "IBVAPError",
    "ModelNotFoundError",
    "CameraError",
    "ConfigError",
]
