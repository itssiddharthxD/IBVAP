"""Draw detection overlays — restrained operational colors."""
from __future__ import annotations

from typing import List
import cv2
import numpy as np

from core.contracts import DetectionResult, FaceResult, ANPRResult


def draw_detections(
    frame: np.ndarray,
    detections: List[DetectionResult],
    faces: List[FaceResult] | None = None,
    anpr: List[ANPRResult] | None = None,
) -> np.ndarray:
    out = frame.copy()
    for d in detections:
        x1, y1, x2, y2 = d.bounding_box.to_int()
        # muted teal / steel blue
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
