def point_in_polygon(point, polygon):
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside

class VirtualFence:
    def __init__(self, polygon, enabled=True):
        self.polygon = polygon
        self.enabled = enabled
        self.inside_ids = set()

    def check(self, detections):
        if not self.enabled:
            return []
        events = []
        for d in detections:
            x1, y1, x2, y2 = d.bbox
            center = ((x1+x2)//2, (y1+y2)//2)
            if point_in_polygon(center, self.polygon):
                key = d.track_id if d.track_id is not None else id(d)
                if key not in self.inside_ids:
                    self.inside_ids.add(key)
                    events.append(d)
            elif d.track_id is not None:
                self.inside_ids.discard(d.track_id)
        return events
