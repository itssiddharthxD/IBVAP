"""In-memory per-camera track state for temporal rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Tuple, List


@dataclass
class TrackState:
    track_id: int
    class_name: str
    first_seen: datetime
    last_seen: datetime
    last_cx: float
    last_cy: float
    positions: List[Tuple[datetime, float, float]] = field(default_factory=list)
    stationary_since: Optional[datetime] = None
    enter_zone_time: Optional[datetime] = None
    alert_count: int = 0


class StateStore:
    def __init__(self, max_history: int = 60):
        # camera_id -> track_id -> TrackState
        self._tracks: Dict[str, Dict[int, TrackState]] = {}
        # camera_id -> rule_id -> key -> last_alert_time
        self._cooldowns: Dict[str, Dict[str, Dict[str, datetime]]] = {}
        # camera_id -> rule_id -> list of event timestamps (repeated activity)
        self._repeat_events: Dict[str, Dict[str, List[datetime]]] = {}
        self.max_history = max_history

    def update_track(
        self,
        camera_id: str,
        track_id: int,
        class_name: str,
        cx: float,
        cy: float,
        timestamp: datetime,
        in_zone: bool = True,
    ) -> TrackState:
        cam = self._tracks.setdefault(camera_id, {})
        st = cam.get(track_id)
        if st is None:
            st = TrackState(
                track_id=track_id,
                class_name=class_name,
                first_seen=timestamp,
                last_seen=timestamp,
                last_cx=cx,
                last_cy=cy,
                positions=[(timestamp, cx, cy)],
                enter_zone_time=timestamp if in_zone else None,
            )
            cam[track_id] = st
        else:
            st.last_seen = timestamp
            st.class_name = class_name
            st.positions.append((timestamp, cx, cy))
            if len(st.positions) > self.max_history:
                st.positions = st.positions[-self.max_history :]
            # stationary detection (normalized displacement)
            dist = ((cx - st.last_cx) ** 2 + (cy - st.last_cy) ** 2) ** 0.5
            if dist < 0.01:
                if st.stationary_since is None:
                    st.stationary_since = timestamp
            else:
                st.stationary_since = None
            st.last_cx, st.last_cy = cx, cy
            if in_zone and st.enter_zone_time is None:
                st.enter_zone_time = timestamp
            if not in_zone:
                st.enter_zone_time = None
        return st

    def prune(self, camera_id: str, active_ids: set, timestamp: datetime) -> None:
        cam = self._tracks.get(camera_id)
        if not cam:
            return
        stale = [tid for tid in cam if tid not in active_ids]
        for tid in stale:
            del cam[tid]

    def in_cooldown(
        self, camera_id: str, rule_id: str, key: str, now: datetime, cooldown_sec: float
    ) -> bool:
        last = (
            self._cooldowns.get(camera_id, {})
            .get(rule_id, {})
            .get(key)
        )
        if last is None:
            return False
        return (now - last).total_seconds() < cooldown_sec

    def mark_alert(
        self, camera_id: str, rule_id: str, key: str, now: datetime
    ) -> None:
        self._cooldowns.setdefault(camera_id, {}).setdefault(rule_id, {})[key] = now

    def push_repeat(
        self, camera_id: str, rule_id: str, now: datetime, window_sec: float
    ) -> int:
        lst = self._repeat_events.setdefault(camera_id, {}).setdefault(rule_id, [])
        lst.append(now)
        cutoff = now.timestamp() - window_sec
        lst[:] = [t for t in lst if t.timestamp() >= cutoff]
        return len(lst)
