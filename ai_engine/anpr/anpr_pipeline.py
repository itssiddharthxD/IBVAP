"""ANPR pipeline — vehicle crop + OCR with full-res friendly regions."""
from __future__ import annotations

from typing import List, Any, Optional, Tuple
from datetime import datetime
import time
import logging

import numpy as np
import cv2

from core.contracts import ANPRResult, BoundingBox, DetectionResult
from .ocr import OCREngine

logger = logging.getLogger(__name__)

VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "van", "bicycle"}


class ANPRPipeline:
    def __init__(self, min_ocr_conf: float = 0.12, ocr_interval_sec: float = 0.6):
        self.ocr = OCREngine()
        self.min_ocr_conf = min_ocr_conf
        self.ocr_interval_sec = ocr_interval_sec
        self._recent: dict = {}
        self._cooldown_sec = 2.0
        self._last_ocr_time = 0.0
        if self.ocr.is_ready():
            logger.info("ANPR pipeline ready")
        else:
            logger.warning("ANPR OCR not ready: %s", self.ocr.get_error())

    def is_ready(self) -> bool:
        return self.ocr.is_ready()

    def get_errors(self) -> List[str]:
        if self.ocr.is_ready():
            return []
        err = self.ocr.get_error()
        return [err] if err else ["OCR not ready"]

    def process(
        self,
        frame: Any,
        camera_id: str,
        timestamp: datetime,
        vehicle_detections: Optional[List[DetectionResult]] = None,
        vehicle_type: Optional[str] = None,
    ) -> List[ANPRResult]:
        if frame is None:
            return []
        if not self.is_ready():
            return []

        now = time.monotonic()
        if (now - self._last_ocr_time) < self.ocr_interval_sec:
            return []

        h, w = frame.shape[:2]
        vehicles = [
            d for d in (vehicle_detections or [])
            if str(d.class_name).lower() in VEHICLE_CLASSES
        ]

        regions: List[Tuple[np.ndarray, BoundingBox, str]] = []
        if vehicles:
            def _area(d: DetectionResult) -> float:
                b = d.bounding_box
                return max(0.0, (b.x2 - b.x1) * (b.y2 - b.y1))

            for d in sorted(vehicles, key=_area, reverse=True)[:3]:
                regions.extend(self._vehicle_plate_regions(frame, d, w, h))
        # Always add fallback strips (helps when YOLO box is loose/missed)
        regions.extend(self._fallback_regions(frame, w, h, vehicle_type))

        if not regions:
            return []

        self._last_ocr_time = now
        results: List[ANPRResult] = []
        tried = 0

        for crop, bbox, vt in regions:
            if crop is None or crop.size == 0:
                continue
            # skip tiny crops
            ch, cw = crop.shape[:2]
            if cw < 40 or ch < 12:
                continue
            tried += 1
            text, conf = self.ocr.read(crop)
            if not text:
                continue
            if conf < self.min_ocr_conf and not self.ocr.looks_like_plate(text):
                continue
            if len(text) < 4:
                continue
            if not self.ocr.looks_like_plate(text) and conf < 0.25:
                continue

            key = f"{camera_id}:{text}"
            ts = timestamp.timestamp() if hasattr(timestamp, "timestamp") else time.time()
            if ts - self._recent.get(key, 0) < self._cooldown_sec:
                continue
            self._recent[key] = ts

            results.append(
                ANPRResult(
                    camera_id=camera_id,
                    timestamp=timestamp,
                    plate_text=text,
                    confidence=float(conf),
                    vehicle_type=vt,
                    bounding_box=bbox,
                    snapshot_path=None,
                )
            )
            logger.info("ANPR %s → %s (conf=%.2f)", camera_id, text, conf)
            break

        if not results and tried:
            logger.debug("ANPR %s: OCR tried %d crops, no plate", camera_id, tried)
        return results

    def _vehicle_plate_regions(
        self, frame, d: DetectionResult, w: int, h: int
    ) -> List[Tuple[np.ndarray, BoundingBox, str]]:
        x1, y1, x2, y2 = d.bounding_box.to_int()
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)
        if x2 <= x1 or y2 <= y1:
            return []
        vh, vw = y2 - y1, x2 - x1
        vt = (d.extra or {}).get("vehicle_type") or d.class_name
        out = []
        # full vehicle first (OCR finds plate region inside)
        bands = [
            (0.40, 1.00, 0.05, 0.05),
            (0.55, 1.00, 0.08, 0.08),
            (0.62, 0.98, 0.12, 0.12),
            (0.50, 0.90, 0.10, 0.10),
            (0.00, 1.00, 0.00, 0.00),  # full box
        ]
        for top_r, bot_r, left_r, right_r in bands:
            py1 = y1 + int(vh * top_r)
            py2 = y1 + int(vh * bot_r)
            px1 = x1 + int(vw * left_r)
            px2 = x2 - int(vw * right_r)
            py1, py2 = max(0, py1), min(h, py2)
            px1, px2 = max(0, px1), min(w, px2)
            if px2 - px1 < 40 or py2 - py1 < 15:
                continue
            crop = frame[py1:py2, px1:px2]
            if crop is None or crop.size == 0:
                continue
            out.append(
                (crop.copy(), BoundingBox(float(px1), float(py1), float(px2), float(py2)), vt)
            )
        return out

    def _fallback_regions(
        self, frame, w: int, h: int, vehicle_type: Optional[str]
    ) -> List[Tuple[np.ndarray, BoundingBox, str]]:
        out = []
        strips = [
            (0.50, 0.95, 0.10, 0.90),
            (0.60, 1.00, 0.15, 0.85),
            (0.35, 0.85, 0.20, 0.80),
        ]
        for t, b, l, r in strips:
            py1, py2 = int(h * t), int(h * b)
            px1, px2 = int(w * l), int(w * r)
            crop = frame[py1:py2, px1:px2]
            if crop is None or crop.size == 0:
                continue
            out.append(
                (
                    crop.copy(),
                    BoundingBox(float(px1), float(py1), float(px2), float(py2)),
                    vehicle_type or "vehicle",
                )
            )
        return out
