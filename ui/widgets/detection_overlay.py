"""Draw detection overlays + security rule zones — restrained operational colors."""
from __future__ import annotations

from typing import List, Optional, Sequence, Any
import cv2
import numpy as np

from core.contracts import DetectionResult, FaceResult, ANPRResult


# Zone colors by rule type (BGR)
_ZONE_COLORS = {
    "restricted_zone": (60, 60, 220),      # red
    "loitering": (0, 165, 255),            # orange
    "crowd": (0, 200, 200),                # yellow-ish
    "wrong_direction": (220, 140, 0),      # blue-ish
    "stopped_vehicle": (180, 100, 200),    # purple
    "abnormal_movement": (100, 180, 100),  # green
    "repeated_activity": (200, 160, 80),
    "unattended_object": (80, 80, 200),
}


def draw_zones(
    frame: np.ndarray,
    zones: Optional[List[dict]] = None,
) -> np.ndarray:
    """Draw rule zones on frame.

    Each zone dict:
      {
        "points": [[x,y], ...] normalized 0..1 OR pixel coords,
        "label": str,
        "rule_type": str,
        "normalized": True/False
      }
    """
    if not zones:
        return frame
    out = frame
    h, w = out.shape[:2]
    for z in zones:
        pts = z.get("points") or []
        if len(pts) < 2:
            continue
        normalized = z.get("normalized", True)
        color = _ZONE_COLORS.get(z.get("rule_type", ""), (60, 60, 220))
        label = z.get("label") or z.get("rule_type") or "ZONE"

        pixel_pts = []
        for p in pts:
            x, y = float(p[0]), float(p[1])
            if normalized:
                x, y = x * w, y * h
            pixel_pts.append([int(x), int(y)])
        arr = np.array(pixel_pts, dtype=np.int32)

        overlay = out.copy()
        if len(arr) >= 3:
            cv2.fillPoly(overlay, [arr], color)
            out = cv2.addWeighted(overlay, 0.22, out, 0.78, 0)
            cv2.polylines(out, [arr], isClosed=True, color=color, thickness=2, lineType=cv2.LINE_AA)
        else:
            cv2.polylines(out, [arr], isClosed=False, color=color, thickness=2)

        # label at first point
        lx, ly = pixel_pts[0]
        ly = max(ly - 6, 14)
        cv2.rectangle(out, (lx - 2, ly - 14), (lx + 8 * len(label) + 4, ly + 4), (10, 10, 10), -1)
        cv2.putText(
            out, label, (lx, ly),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA,
        )
    return out


def draw_detections(
    frame: np.ndarray,
    detections: List[DetectionResult],
    faces: List[FaceResult] | None = None,
    anpr: List[ANPRResult] | None = None,
    zones: Optional[List[dict]] = None,
) -> np.ndarray:
    out = frame.copy()

    # Zones under detections
    out = draw_zones(out, zones)

    for d in detections:
        x1, y1, x2, y2 = d.bounding_box.to_int()
        color = (180, 160, 90) if d.class_name == "person" else (160, 180, 100)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 1)
        label = f"{d.class_name} {d.confidence:.2f}"
        if d.track_id is not None:
            label += f" #{d.track_id}"
        cv2.putText(
            out, label, (x1, max(y1 - 4, 12)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA,
        )

    if faces:
        for f in faces:
            x1, y1, x2, y2 = f.bounding_box.to_int()
            color = (100, 180, 100) if f.match_status.value == "MATCHED" else (140, 140, 140)
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 1)
            label = f.match_status.value
            if f.name:
                label += f" {f.name}"
            cv2.putText(
                out, label, (x1, max(y1 - 4, 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA,
            )

    if anpr:
        for a in anpr:
            if a.bounding_box:
                x1, y1, x2, y2 = a.bounding_box.to_int()
                cv2.rectangle(out, (x1, y1), (x2, y2), (80, 160, 220), 1)
                cv2.putText(
                    out, a.plate_text, (x1, max(y1 - 4, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 160, 220), 1, cv2.LINE_AA,
                )
    return out
