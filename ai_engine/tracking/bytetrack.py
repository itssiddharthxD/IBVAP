"""Simple multi-object tracker (IoU + centroid) — assigns stable track_id."""
from __future__ import annotations

from typing import List, Any, Dict, Tuple, Optional
from dataclasses import dataclass, field
import logging

from core.contracts import DetectionResult
from .tracker import BaseTracker

logger = logging.getLogger(__name__)


def _iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _center(b) -> Tuple[float, float]:
    return ((b[0] + b[2]) * 0.5, (b[1] + b[3]) * 0.5)


@dataclass
class _Track:
    track_id: int
    bbox: Tuple[float, float, float, float]
    class_name: str
    hits: int = 1
    age: int = 0
    time_since_update: int = 0


class ByteTrackTracker(BaseTracker):
    """
    Frame-to-frame association by IoU (fallback: nearest center).
    Always fills DetectionResult.track_id so line-crossing / loitering work.
    """

    def __init__(self, iou_threshold: float = 0.25, max_age: int = 30, max_center_dist: float = 120.0):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.max_center_dist = max_center_dist
        self._next_id = 1
        self._tracks: List[_Track] = []
        # Per-camera state so multiple cameras don't share IDs incorrectly
        self._by_camera: Dict[str, List[_Track]] = {}
        self._next_by_camera: Dict[str, int] = {}

    def update(self, detections: List[DetectionResult], frame: Any = None) -> List[DetectionResult]:
        if not detections:
            # age all camera tracks that might be idle — skip without camera_id
            return detections

        cam = detections[0].camera_id or "_default"
        tracks = self._by_camera.setdefault(cam, [])
        next_id = self._next_by_camera.get(cam, 1)

        # Age existing
        for t in tracks:
            t.age += 1
            t.time_since_update += 1

        det_boxes = [d.bounding_box.as_tuple() for d in detections]
        det_classes = [(d.class_name or "").lower() for d in detections]
        matched_det = set()
        matched_trk = set()

        # Score matrix IoU
        pairs = []
        for ti, t in enumerate(tracks):
            if t.time_since_update > self.max_age:
                continue
            for di, box in enumerate(det_boxes):
                # prefer same class family (person vs vehicle)
                same_family = True
                tc = (t.class_name or "").lower()
                dc = det_classes[di]
                veh = {"car", "motorcycle", "bus", "truck", "bicycle"}
                if (tc in veh) != (dc in veh) and not (tc == "person" and dc == "person"):
                    if tc == "person" or dc == "person":
                        same_family = False
                if not same_family:
                    continue
                iou = _iou(t.bbox, box)
                if iou >= self.iou_threshold:
                    pairs.append((iou, ti, di))
                else:
                    # center distance fallback
                    cx1, cy1 = _center(t.bbox)
                    cx2, cy2 = _center(box)
                    dist = ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5
                    if dist < self.max_center_dist:
                        pairs.append((iou + 0.01 * (1.0 - dist / self.max_center_dist), ti, di))

        pairs.sort(key=lambda x: -x[0])
        for score, ti, di in pairs:
            if ti in matched_trk or di in matched_det:
                continue
            matched_trk.add(ti)
            matched_det.add(di)
            tracks[ti].bbox = det_boxes[di]
            tracks[ti].class_name = det_classes[di]
            tracks[ti].hits += 1
            tracks[ti].time_since_update = 0
            detections[di].track_id = tracks[ti].track_id

        # New tracks for unmatched detections
        for di, d in enumerate(detections):
            if di in matched_det:
                continue
            tid = next_id
            next_id += 1
            tracks.append(
                _Track(
                    track_id=tid,
                    bbox=det_boxes[di],
                    class_name=det_classes[di],
                )
            )
            d.track_id = tid

        # Drop stale tracks
        tracks[:] = [t for t in tracks if t.time_since_update <= self.max_age]
        self._by_camera[cam] = tracks
        self._next_by_camera[cam] = next_id
        return detections
