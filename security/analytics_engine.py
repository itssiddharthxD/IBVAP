"""Analytics Engine — evaluate detections against user-configured rules."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Any

from core.contracts import DetectionResult, FaceResult, MatchStatus, ANPRResult
from database.models import SecurityRule
from security.rule_manager import RuleManager
from security.state_store import StateStore
from security.geometry import (
    bbox_center, bbox_bottom_center, bbox_in_zone, movement_angle_deg, angle_diff_deg,
    segments_intersect, face_quality_ok, resolve_line,
)
from security.rule_types import VEHICLE_CLASSES, PERSON_CLASSES, OBJECT_CLASSES
from security.alert_manager import AlertManager

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    def __init__(
        self,
        rule_manager: Optional[RuleManager] = None,
        alert_manager: Optional[AlertManager] = None,
        state: Optional[StateStore] = None,
    ):
        self.rules = rule_manager or RuleManager.instance()
        self.alerts = alert_manager or AlertManager()
        self.state = state or StateStore()
        self._plate_cache: Optional[set] = None
        self._plate_cache_ts: float = 0

    def _blacklist_plates(self) -> set:
        import time
        now = time.time()
        if self._plate_cache is not None and now - self._plate_cache_ts < 30:
            return self._plate_cache
        try:
            from services.plate_watchlist_service import PlateWatchlistService
            self._plate_cache = PlateWatchlistService().normalized_blacklist()
            self._plate_cache_ts = now
        except Exception:
            self._plate_cache = set()
        return self._plate_cache or set()

    def process(
        self,
        camera_id: str,
        timestamp: datetime,
        detections: List[DetectionResult] | None = None,
        frame: Any = None,
        frame_size: tuple | None = None,
        faces: List[FaceResult] | None = None,
        anpr: List[ANPRResult] | None = None,
    ) -> list:
        detections = detections or []
        faces = faces or []
        anpr = anpr or []
        rules = self.rules.rules_for_camera(camera_id)
        if not rules:
            return []

        fw, fh = 1.0, 1.0
        if frame_size:
            fw, fh = float(frame_size[0]), float(frame_size[1])
        elif frame is not None:
            try:
                fh, fw = frame.shape[:2]
                fw, fh = float(fw), float(fh)
            except Exception:
                pass
        # Auto-detect pixel coords when frame_size unknown (zones are 0..1)
        if fw <= 1.5 and detections:
            try:
                max_x = max(d.bounding_box.x2 for d in detections)
                max_y = max(d.bounding_box.y2 for d in detections)
                if max_x > 1.5 or max_y > 1.5:
                    fw = max(float(max_x) * 1.08, 640.0)
                    fh = max(float(max_y) * 1.08, 360.0)
            except Exception:
                pass

        active_ids = set()
        enriched = []
        for d in detections:
            x1, y1, x2, y2 = d.bounding_box.as_tuple()
            cx, cy = bbox_center(x1, y1, x2, y2)
            if fw > 1.5:
                ncx, ncy = cx / fw, cy / fh
            else:
                ncx, ncy = cx, cy
            tid = d.track_id if d.track_id is not None else -abs(hash((x1, y1, x2, y2))) % 10_000_000
            if d.track_id is not None:
                active_ids.add(tid)
            enriched.append((d, tid, ncx, ncy, x1, y1, x2, y2))

        created = []
        for rule in rules:
            if not self._schedule_active(rule, timestamp):
                continue
            try:
                hits = self._dispatch(rule, camera_id, timestamp, enriched, fw, fh, faces, anpr)
                for hit in hits:
                    snap = None
                    if frame is not None:
                        snap = self.alerts.save_snapshot(frame, camera_id)
                    row = self.alerts.create_alert(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        activity_type=rule.rule_type,
                        camera_id=camera_id,
                        timestamp=timestamp,
                        severity=rule.severity or "medium",
                        description=hit["description"],
                        track_id=hit.get("track_id"),
                        object_type=hit.get("object_type") or rule.object_type,
                        zone_name=rule.name if rule.zone else None,
                        duration_sec=hit.get("duration_sec"),
                        count_value=hit.get("count_value"),
                        confidence=hit.get("confidence"),
                        snapshot_path=snap,
                        plate_text=hit.get("plate_text"),
                        payload=hit.get("payload"),
                        record_on_alert=bool(getattr(rule, "record_on_alert", False)),
                        frame=frame,
                    )
                    created.append(row)
            except Exception:
                logger.exception("Rule eval failed: %s", rule.name)

        self.state.prune(camera_id, active_ids, timestamp)
        return created

    def _schedule_active(self, rule: SecurityRule, ts: datetime) -> bool:
        start = getattr(rule, "schedule_start_hour", None)
        end = getattr(rule, "schedule_end_hour", None)
        if start is None and end is None:
            return True
        if start is None or end is None:
            return True
        h = ts.hour
        if start <= end:
            return start <= h < end
        # overnight window e.g. 20 → 6
        return h >= start or h < end

    def _dispatch(self, rule, camera_id, ts, enriched, fw, fh, faces, anpr):
        rt = rule.rule_type
        if rt == "unknown_face":
            return self._unknown_face(rule, camera_id, ts, faces, fw, fh)
        if rt == "line_crossing":
            return self._line_crossing(rule, camera_id, ts, enriched, fw, fh)
        if rt == "plate_blacklist":
            return self._plate_blacklist(rule, camera_id, ts, anpr)
        if rt == "restricted_zone":
            return self._restricted_zone(rule, camera_id, ts, enriched, fw, fh)
        if rt == "loitering":
            return self._loitering(rule, camera_id, ts, enriched, fw, fh)
        if rt == "crowd":
            return self._crowd(rule, camera_id, ts, enriched, fw, fh)
        if rt == "abnormal_movement":
            return self._abnormal(rule, camera_id, ts, enriched, fw, fh)
        if rt == "wrong_direction":
            return self._wrong_direction(rule, camera_id, ts, enriched, fw, fh)
        if rt == "stopped_vehicle":
            return self._stopped_vehicle(rule, camera_id, ts, enriched, fw, fh)
        if rt == "repeated_activity":
            return self._repeated(rule, camera_id, ts, enriched, fw, fh)
        if rt == "unattended_object":
            return self._unattended(rule, camera_id, ts, enriched, fw, fh)
        return []

    def _matches_object(self, class_name: str, object_type: str) -> bool:
        cn = (class_name or "").lower()
        ot = (object_type or "person").lower()
        if ot in ("any", "all", "*"):
            return True
        if ot == "person":
            return cn in PERSON_CLASSES
        if ot == "vehicle":
            return cn in VEHICLE_CLASSES
        if ot == "object":
            return cn in OBJECT_CLASSES or cn not in PERSON_CLASSES | VEHICLE_CLASSES
        return True

    def _in_zone(self, rule, x1, y1, x2, y2, fw, fh) -> bool:
        return bbox_in_zone(x1, y1, x2, y2, rule.zone, fw, fh)

    def _cooldown_ok(self, rule, camera_id, key, now) -> bool:
        cd = float(rule.cooldown_sec or 30)
        if self.state.in_cooldown(camera_id, rule.rule_id, key, now, cd):
            return False
        self.state.mark_alert(camera_id, rule.rule_id, key, now)
        return True

    def _restricted_zone(self, rule, camera_id, ts, enriched, fw, fh):
        if not rule.zone or len(rule.zone) < 3:
            return []
        hits = []
        for d, tid, ncx, ncy, x1, y1, x2, y2 in enriched:
            if not self._matches_object(d.class_name, rule.object_type):
                continue
            if not self._in_zone(rule, x1, y1, x2, y2, fw, fh):
                continue
            key = f"rz:{tid}"
            if not self._cooldown_ok(rule, camera_id, key, ts):
                continue
            hits.append({
                "description": f"Restricted zone entry: {d.class_name} track #{tid}",
                "track_id": tid if tid >= 0 else None,
                "object_type": d.class_name,
                "confidence": d.confidence,
                "payload": {"class_name": d.class_name},
            })
        return hits

    def _loitering(self, rule, camera_id, ts, enriched, fw, fh):
        duration = float(rule.duration_sec or 30)
        hits = []
        for d, tid, ncx, ncy, x1, y1, x2, y2 in enriched:
            if not self._matches_object(d.class_name, rule.object_type):
                continue
            if not self._in_zone(rule, x1, y1, x2, y2, fw, fh):
                continue
            st = self.state.update_track(camera_id, tid, d.class_name, ncx, ncy, ts, in_zone=True)
            start = st.enter_zone_time or st.first_seen
            elapsed = (ts - start).total_seconds()
            if elapsed < duration:
                continue
            key = f"loiter:{tid}"
            if not self._cooldown_ok(rule, camera_id, key, ts):
                continue
            hits.append({
                "description": f"Loitering: track #{tid} for {int(elapsed)}s",
                "track_id": tid if tid >= 0 else None,
                "object_type": d.class_name,
                "duration_sec": elapsed,
                "confidence": d.confidence,
                "payload": {"elapsed": elapsed, "threshold": duration},
            })
        return hits

    def _crowd(self, rule, camera_id, ts, enriched, fw, fh):
        min_count = int(rule.min_count or 5)
        persons = [
            d for d, tid, ncx, ncy, x1, y1, x2, y2 in enriched
            if self._matches_object(d.class_name, rule.object_type or "person")
            and self._in_zone(rule, x1, y1, x2, y2, fw, fh)
        ]
        if len(persons) < min_count:
            return []
        if not self._cooldown_ok(rule, camera_id, "crowd", ts):
            return []
        return [{
            "description": f"Crowd: {len(persons)} persons (min {min_count})",
            "count_value": len(persons),
            "object_type": "person",
            "payload": {"count": len(persons), "threshold": min_count},
        }]

    def _abnormal(self, rule, camera_id, ts, enriched, fw, fh):
        thresh = float(rule.speed_threshold or 0.15)
        hits = []
        for d, tid, ncx, ncy, x1, y1, x2, y2 in enriched:
            if not self._matches_object(d.class_name, rule.object_type):
                continue
            st = self.state.update_track(camera_id, tid, d.class_name, ncx, ncy, ts)
            if len(st.positions) < 2:
                continue
            t0, x0, y0 = st.positions[-2]
            dt = max((ts - t0).total_seconds(), 1e-3)
            speed = ((ncx - x0) ** 2 + (ncy - y0) ** 2) ** 0.5 / dt
            if speed < thresh:
                continue
            key = f"abn:{tid}"
            if not self._cooldown_ok(rule, camera_id, key, ts):
                continue
            hits.append({
                "description": f"Abnormal movement: track #{tid} speed={speed:.3f}",
                "track_id": tid if tid >= 0 else None,
                "object_type": d.class_name,
                "confidence": d.confidence,
                "payload": {"speed": speed, "threshold": thresh},
            })
        return hits

    def _wrong_direction(self, rule, camera_id, ts, enriched, fw, fh):
        allowed = float(rule.direction_deg if rule.direction_deg is not None else 0)
        tol = float(rule.direction_tolerance_deg if rule.direction_tolerance_deg is not None else 45)
        hits = []
        for d, tid, ncx, ncy, x1, y1, x2, y2 in enriched:
            if not self._matches_object(d.class_name, rule.object_type):
                continue
            if not self._in_zone(rule, x1, y1, x2, y2, fw, fh):
                continue
            st = self.state.update_track(camera_id, tid, d.class_name, ncx, ncy, ts, in_zone=True)
            if len(st.positions) < 3:
                continue
            t0, x0, y0 = st.positions[-3]
            dx, dy = ncx - x0, ncy - y0
            if (dx * dx + dy * dy) ** 0.5 < 0.02:
                continue
            ang = movement_angle_deg(dx, dy)
            if angle_diff_deg(ang, allowed) <= tol:
                continue
            key = f"dir:{tid}"
            if not self._cooldown_ok(rule, camera_id, key, ts):
                continue
            hits.append({
                "description": f"Wrong direction: track #{tid} heading {ang:.0f}°",
                "track_id": tid if tid >= 0 else None,
                "object_type": d.class_name,
                "confidence": d.confidence,
                "payload": {"heading": ang, "allowed": allowed, "tolerance": tol},
            })
        return hits

    def _stopped_vehicle(self, rule, camera_id, ts, enriched, fw, fh):
        duration = float(rule.duration_sec or 60)
        hits = []
        for d, tid, ncx, ncy, x1, y1, x2, y2 in enriched:
            if not self._matches_object(d.class_name, rule.object_type or "vehicle"):
                continue
            if not self._in_zone(rule, x1, y1, x2, y2, fw, fh):
                continue
            st = self.state.update_track(camera_id, tid, d.class_name, ncx, ncy, ts, in_zone=True)
            if st.stationary_since is None:
                continue
            elapsed = (ts - st.stationary_since).total_seconds()
            if elapsed < duration:
                continue
            key = f"stop:{tid}"
            if not self._cooldown_ok(rule, camera_id, key, ts):
                continue
            hits.append({
                "description": f"Stopped vehicle: track #{tid} stationary {int(elapsed)}s",
                "track_id": tid if tid >= 0 else None,
                "object_type": d.class_name,
                "duration_sec": elapsed,
                "confidence": d.confidence,
                "payload": {"elapsed": elapsed, "threshold": duration},
            })
        return hits

    def _repeated(self, rule, camera_id, ts, enriched, fw, fh):
        min_count = int(rule.min_count or 3)
        window = float(rule.window_sec or 120)
        relevant = [
            1 for d, tid, ncx, ncy, x1, y1, x2, y2 in enriched
            if self._matches_object(d.class_name, rule.object_type)
            and self._in_zone(rule, x1, y1, x2, y2, fw, fh)
        ]
        if not relevant:
            return []
        count = self.state.push_repeat(camera_id, rule.rule_id, ts, window)
        if count < min_count:
            return []
        if not self._cooldown_ok(rule, camera_id, "repeat", ts):
            return []
        return [{
            "description": f"Repeated activity: {count} events in {int(window)}s",
            "count_value": count,
            "object_type": rule.object_type,
            "payload": {"count": count, "window_sec": window, "threshold": min_count},
        }]

    def _unattended(self, rule, camera_id, ts, enriched, fw, fh):
        duration = float(rule.duration_sec or 90)
        hits = []
        for d, tid, ncx, ncy, x1, y1, x2, y2 in enriched:
            if not self._matches_object(d.class_name, rule.object_type or "object"):
                continue
            if d.class_name.lower() in PERSON_CLASSES | VEHICLE_CLASSES:
                continue
            if not self._in_zone(rule, x1, y1, x2, y2, fw, fh):
                continue
            st = self.state.update_track(camera_id, tid, d.class_name, ncx, ncy, ts, in_zone=True)
            if st.stationary_since is None:
                st.stationary_since = st.first_seen
            elapsed = (ts - st.stationary_since).total_seconds()
            if elapsed < duration:
                continue
            key = f"unatt:{tid}"
            if not self._cooldown_ok(rule, camera_id, key, ts):
                continue
            hits.append({
                "description": f"Unattended object: {d.class_name} track #{tid} for {int(elapsed)}s",
                "track_id": tid if tid >= 0 else None,
                "object_type": d.class_name,
                "duration_sec": elapsed,
                "confidence": d.confidence,
                "payload": {"elapsed": elapsed, "threshold": duration},
            })
        return hits

    def _unknown_face(self, rule, camera_id, ts, faces, fw, fh):
        hits = []
        for f in faces or []:
            status = getattr(f, "match_status", None)
            val = status.value if hasattr(status, "value") else str(status or "")
            if val != "UNKNOWN" and status != MatchStatus.UNKNOWN:
                continue
            if not face_quality_ok(f.bounding_box, fw, fh):
                continue
            try:
                x1, y1, x2, y2 = f.bounding_box.as_tuple()
                key = f"uf:{int(x1)//20}:{int(y1)//20}"
            except Exception:
                key = "uf:global"
            if not self._cooldown_ok(rule, camera_id, key, ts):
                continue
            hits.append({
                "description": "Unknown face detected",
                "object_type": "person",
                "confidence": getattr(f, "confidence", None),
                "payload": {"match_status": "UNKNOWN", "similarity": getattr(f, "similarity", 0)},
            })
        return hits

    def _line_crossing(self, rule, camera_id, ts, enriched, fw, fh):
        raw_line = getattr(rule, "line", None)
        if not raw_line and rule.params:
            raw_line = rule.params.get("line")
        resolved = resolve_line(raw_line, rule.zone)
        if not resolved:
            return []
        p3, p4 = resolved
        # default object type for line crossing: vehicle (traffic)
        obj_type = rule.object_type or "vehicle"
        hits = []
        for d, tid, ncx, ncy, x1, y1, x2, y2 in enriched:
            if not self._matches_object(d.class_name, obj_type):
                continue
            # use bottom-center for vehicles (road contact), else center
            cn = (d.class_name or "").lower()
            if cn in VEHICLE_CLASSES:
                bx, by = bbox_bottom_center(x1, y1, x2, y2)
                if fw > 1.5:
                    ncx, ncy = bx / fw, by / fh
                else:
                    ncx, ncy = bx, by
            st = self.state.update_track(camera_id, tid, d.class_name, ncx, ncy, ts)
            if len(st.positions) < 2:
                continue
            # check last few segments (missed frames)
            crossed = False
            for i in range(max(0, len(st.positions) - 4), len(st.positions) - 1):
                _, xa, ya = st.positions[i]
                _, xb, yb = st.positions[i + 1]
                if segments_intersect((xa, ya), (xb, yb), p3, p4):
                    crossed = True
                    break
            if not crossed:
                continue
            key = f"line:{tid}"
            if not self._cooldown_ok(rule, camera_id, key, ts):
                continue
            hits.append({
                "description": f"Line crossing: {d.class_name} track #{tid}",
                "track_id": tid if tid >= 0 else None,
                "object_type": d.class_name,
                "confidence": d.confidence,
                "payload": {"line": [list(p3), list(p4)], "class_name": d.class_name},
            })
        return hits

    def _plate_blacklist(self, rule, camera_id, ts, anpr_list):
        bl = self._blacklist_plates()
        if not bl:
            return []
        hits = []
        for a in anpr_list or []:
            plate = (getattr(a, "plate_text", None) or "").strip().upper().replace(" ", "")
            if not plate or plate not in bl:
                continue
            key = f"plate:{plate}"
            if not self._cooldown_ok(rule, camera_id, key, ts):
                continue
            hits.append({
                "description": f"Blacklisted plate: {plate}",
                "object_type": "vehicle",
                "plate_text": plate,
                "confidence": getattr(a, "confidence", None),
                "payload": {"plate_text": plate},
            })
        return hits
