"""System-level helpers: device detection, stats."""
from __future__ import annotations

import platform
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class SystemService:
    @staticmethod
    def detect_ai_device() -> str:
        """Return 'GPU' if CUDA available, else 'CPU'."""
        try:
            import torch
            if torch.cuda.is_available():
                return "GPU"
        except Exception:
            pass
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            if "CUDAExecutionProvider" in providers or "DmlExecutionProvider" in providers:
                return "GPU"
        except Exception:
            pass
        return "CPU"

    @staticmethod
    def get_system_info() -> Dict[str, str]:
        return {
            "os": platform.system(),
            "python": platform.python_version(),
            "machine": platform.machine(),
            "ai_device": SystemService.detect_ai_device(),
        }
