"""Geometry helpers for zones and line crossing (normalized 0..1)."""
from __future__ import annotations

from typing import List, Sequence, Tuple, Optional
import math

Point = Tuple[float, float]


def point_in_polygon(x: float, y: float, polygon: Sequence[Sequence[float]]) -> bool:
    if not polygon or len(polygon) < 3:
        return True
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = float(polygon[i][0]), float(polygon[i][1])
        xj, yj = float(polygon[j][0]), float(polygon[j][1])
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) + 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def bbox_center(x1: float, y1: float, x2: float, y2: float) -> Point:
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def bbox_bottom_center(x1: float, y1: float, x2: float, y2: float) -> Point:
    """Foot of object — better for road line crossing."""
    return ((x1 + x2) / 2.0, max(y1, y2))


def bbox_in_zone(
    x1: float, y1: float, x2: float, y2: float,
    zone: Optional[Sequence[Sequence[float]]],
    frame_w: float = 1.0,
    frame_h: float = 1.0,
) -> bool:
    if not zone or len(zone) < 3:
        return True
    cx, cy = bbox_center(x1, y1, x2, y2)
    if frame_w > 1.5 or frame_h > 1.5:
        cx, cy = cx / frame_w, cy / frame_h
    return point_in_polygon(cx, cy, zone)


def movement_angle_deg(dx: float, dy: float) -> float:
    ang = math.degrees(math.atan2(-dy, dx))
    if ang < 0:
        ang += 360.0
    return ang


def angle_diff_deg(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def segments_intersect(p1, p2, p3, p4, eps: float = 1e-9) -> bool:
    """True if segment p1-p2 crosses p3-p4 (including near-touches)."""
    def orient(a, b, c):
        return (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])

    def on_seg(a, b, c):
        return (
            min(a[0], b[0]) - eps <= c[0] <= max(a[0], b[0]) + eps
            and min(a[1], b[1]) - eps <= c[1] <= max(a[1], b[1]) + eps
        )

    o1 = orient(p1, p2, p3)
    o2 = orient(p1, p2, p4)
    o3 = orient(p3, p4, p1)
    o4 = orient(p3, p4, p2)

    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    # collinear / endpoint touches
    if abs(o1) <= eps and on_seg(p1, p2, p3):
        return True
    if abs(o2) <= eps and on_seg(p1, p2, p4):
        return True
    if abs(o3) <= eps and on_seg(p3, p4, p1):
        return True
    if abs(o4) <= eps and on_seg(p3, p4, p2):
        return True
    return False


def resolve_line(
    line: Optional[Sequence],
    zone: Optional[Sequence],
) -> Optional[Tuple[Point, Point]]:
    """
    Prefer explicit line (2 points).
    Else longest edge of zone polygon (works when user drew a strip/poly).
    Else first two zone points.
    """
    pts = None
    if line and len(line) >= 2:
        pts = [(float(line[0][0]), float(line[0][1])),
               (float(line[1][0]), float(line[1][1]))]
        return pts[0], pts[1]
    if not zone or len(zone) < 2:
        return None
    z = [(float(p[0]), float(p[1])) for p in zone]
    if len(z) == 2:
        return z[0], z[1]
    # longest edge
    best = None
    best_d = -1.0
    n = len(z)
    for i in range(n):
        a, b = z[i], z[(i + 1) % n]
        d = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
        if d > best_d:
            best_d = d
            best = (a, b)
    return best


def face_quality_ok(bbox, frame_w: float, frame_h: float, min_side: float = 0.04) -> bool:
    x1, y1, x2, y2 = bbox.as_tuple() if hasattr(bbox, "as_tuple") else bbox
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    if frame_w > 1.5:
        w, h = w / frame_w, h / frame_h
    return min(w, h) >= min_side
