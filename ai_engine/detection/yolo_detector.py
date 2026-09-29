"""YOLO detector using Ultralytics. Graceful if model missing; can auto-fetch nano model."""
from __future__ import annotations

from pathlib import Path
from typing import List, Any, Optional
from datetime import datetime
import logging

from core.contracts import DetectionResult, BoundingBox
from core.config import get_config, PROJECT_ROOT
from .detector import BaseDetector

logger = logging.getLogger(__name__)

# COCO classes we care about
TARGET_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


class YOLODetector(BaseDetector):
    def __init__(self, model_path: Optional[str] = None, device: str = "AUTO"):
        cfg = get_config()
        self._model_path = model_path or cfg.get(
            "ai", "model_paths", "yolo", default="models/yolo11n.pt"
        )
        self._device = device
        self._model = None
        self._ready = False
        self._error: Optional[str] = None
        self._load()

    def _resolve_device(self) -> str:
        if self._device.upper() == "CPU":
            return "cpu"
        if self._device.upper() == "GPU":
            return "0"
        try:
            import torch
            if torch.cuda.is_available():
                return "0"
        except Exception:
            pass
        return "cpu"

    def _load(self) -> None:
        path = Path(self._model_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path

        # Ensure models directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from ultralytics import YOLO
        except ImportError:
            self._error = (
                "ultralytics package not installed.\n"
                "Run: pip install ultralytics"
            )
            logger.error(self._error)
            return

        device = self._resolve_device()

        # 1) Prefer local file if present
        if path.exists():
            try:
                self._model = YOLO(str(path))
                self._model.to(device)
                self._ready = True
                logger.info("YOLO model loaded from %s (device=%s)", path, device)
                return
            except Exception as e:
                self._error = f"Failed to load local YOLO model: {e}"
                logger.exception(self._error)
                return

        # 2) Local file missing → let Ultralytics download a small nano model once
        #    and save it into models/ for offline use next time.
        logger.warning(
            "YOLO model not found at %s — downloading yolo11n.pt (one-time, ~6MB)...",
            path,
        )
        try:
            # Ultralytics will download weights on first use
            model = YOLO("yolo11n.pt")
            # Save a copy into our models folder for offline reuse
            try:
                export_path = path
                # model.ckpt path may vary; just copy from ultralytics default if possible
                import shutil
                from ultralytics.utils import WEIGHTS_DIR
                # After load, weights are cached; try common locations
                candidates = [
                    Path("yolo11n.pt"),
                    Path.home() / ".cache" / "ultralytics" / "yolo11n.pt",
                    Path("yolov8n.pt"),
                ]
                src = None
                for c in candidates:
                    if c.exists():
                        src = c
                        break
                if src is None:
                    # Force a predict so weights are written, then search again
                    import numpy as np
                    dummy = np.zeros((320, 320, 3), dtype=np.uint8)
                    model.predict(dummy, verbose=False)
                    for c in candidates:
                        if c.exists():
                            src = c
                            break
                if src and src.resolve() != path.resolve():
                    shutil.copy2(src, path)
                    logger.info("Saved model copy to %s", path)
                self._model = YOLO(str(path)) if path.exists() else model
            except Exception:
                # Still usable even if copy failed
                self._model = model

            self._model.to(device)
            self._ready = True
            self._error = None
            logger.info("YOLO model ready (device=%s)", device)
        except Exception as e:
            self._error = (
                f"YOLO model not found and auto-download failed:\n{e}\n\n"
                f"Manual fix:\n"
                f"1. pip install ultralytics\n"
                f"2. Download yolo11n.pt and place it at:\n   {path}"
            )
            logger.exception(self._error)

    @property
    def model_path(self) -> str:
        return self._model_path

    def is_ready(self) -> bool:
        return self._ready

    def get_error(self) -> Optional[str]:
        return self._error

    def detect(
        self,
        frame: Any,
        camera_id: str,
        timestamp: datetime,
        conf_threshold: float = 0.5,
    ) -> List[DetectionResult]:
        if not self._ready or self._model is None:
            return []

        results: List[DetectionResult] = []
        try:
            preds = self._model.predict(
                source=frame,
                conf=conf_threshold,
                verbose=False,
                classes=list(TARGET_CLASSES.keys()),
                imgsz=320,   # smaller = much faster on CPU
                half=False,
            )
            if not preds:
                return results

            pred = preds[0]
            boxes = pred.boxes
            if boxes is None:
                return results

            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i].item())
                conf = float(boxes.conf[i].item())
                xyxy = boxes.xyxy[i].cpu().numpy()
                class_name = TARGET_CLASSES.get(cls_id, f"class_{cls_id}")
                track_id = None
                if boxes.id is not None:
                    try:
                        track_id = int(boxes.id[i].item())
                    except Exception:
                        track_id = None

                results.append(
                    DetectionResult(
                        camera_id=camera_id,
                        timestamp=timestamp,
                        class_name=class_name,
                        confidence=conf,
                        bounding_box=BoundingBox(
                            x1=float(xyxy[0]),
                            y1=float(xyxy[1]),
                            x2=float(xyxy[2]),
                            y2=float(xyxy[3]),
                        ),
                        track_id=track_id,
                    )
                )
        except Exception as e:
            logger.exception("YOLO detect error: %s", e)

        return results
