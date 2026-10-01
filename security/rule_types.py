"""Metadata for each suspicious-activity rule type."""
from __future__ import annotations

from typing import Dict, List, Any

RULE_TYPES: Dict[str, Dict[str, Any]] = {
    "restricted_zone": {
        "label": "Restricted Zone Entry",
        "description": "Object enters a defined polygon zone.",
        "fields": ["zone", "object_type", "schedule", "cooldown", "record"],
        "default_severity": "high",
    },
    "loitering": {
        "label": "Loitering",
        "description": "Object stays in view (or zone) longer than duration.",
        "fields": ["zone", "object_type", "duration", "schedule", "cooldown", "record"],
        "default_severity": "medium",
        "defaults": {"duration_sec": 30},
    },
    "crowd": {
        "label": "Crowd Detection",
        "description": "Number of people in frame/zone exceeds minimum count.",
        "fields": ["zone", "min_count", "schedule", "cooldown", "record"],
        "default_severity": "high",
        "defaults": {"min_count": 5, "object_type": "person"},
    },
    "abnormal_movement": {
        "label": "Abnormal Movement",
        "description": "Sudden fast displacement of tracked object.",
        "fields": ["object_type", "speed_threshold", "schedule", "cooldown", "record"],
        "default_severity": "medium",
        "defaults": {"speed_threshold": 0.15},
    },
    "wrong_direction": {
        "label": "Wrong Direction",
        "description": "Object moves against the configured allowed direction.",
        "fields": ["zone", "object_type", "direction", "schedule", "cooldown", "record"],
        "default_severity": "high",
        "defaults": {"direction_deg": 0, "direction_tolerance_deg": 45},
    },
    "stopped_vehicle": {
        "label": "Stopped Vehicle",
        "description": "Vehicle remains nearly stationary longer than duration.",
        "fields": ["zone", "duration", "schedule", "cooldown", "record"],
        "default_severity": "medium",
        "defaults": {"duration_sec": 60, "object_type": "vehicle"},
    },
    "repeated_activity": {
        "label": "Repeated Activity",
        "description": "Same area triggers detections repeatedly within a window.",
        "fields": ["zone", "object_type", "min_count", "window", "schedule", "cooldown", "record"],
        "default_severity": "medium",
        "defaults": {"min_count": 3, "window_sec": 120},
    },
    "unattended_object": {
        "label": "Unattended Object",
        "description": "Static non-person object left longer than duration.",
        "fields": ["zone", "duration", "schedule", "cooldown", "record"],
        "default_severity": "high",
        "defaults": {"duration_sec": 90, "object_type": "object"},
    },
    "unknown_face": {
        "label": "Unknown Face",
        "description": "Face recognized as UNKNOWN (not on watchlist).",
        "fields": ["schedule", "cooldown", "record"],
        "default_severity": "high",
        "defaults": {"object_type": "person", "cooldown_sec": 30},
    },
    "line_crossing": {
        "label": "Line Crossing",
        "description": "Tracked object crosses a virtual line (entry/exit). Use object type vehicle for traffic.",
        "fields": ["line", "object_type", "schedule", "cooldown", "record"],
        "default_severity": "medium",
        "defaults": {"object_type": "vehicle", "cooldown_sec": 5},
    },
    "plate_blacklist": {
        "label": "Plate Blacklist Match",
        "description": "ANPR plate matches blacklist watchlist.",
        "fields": ["schedule", "cooldown", "record"],
        "default_severity": "critical",
        "defaults": {"object_type": "vehicle", "cooldown_sec": 60},
    },
}

OBJECT_TYPES = ["person", "vehicle", "object", "any"]
VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "bicycle"}
PERSON_CLASSES = {"person"}
OBJECT_CLASSES = {"backpack", "handbag", "suitcase", "umbrella", "bottle", "chair"}

# One-click rule templates
RULE_TEMPLATES = [
    {
        "name": "Border Night Pack",
        "rules": [
            {"name": "Night Restricted Zone", "rule_type": "restricted_zone", "severity": "high",
             "schedule_start_hour": 20, "schedule_end_hour": 6, "cooldown_sec": 30},
            {"name": "Night Loitering", "rule_type": "loitering", "severity": "medium",
             "duration_sec": 45, "schedule_start_hour": 20, "schedule_end_hour": 6},
            {"name": "Night Unknown Face", "rule_type": "unknown_face", "severity": "high",
             "schedule_start_hour": 20, "schedule_end_hour": 6},
        ],
    },
    {
        "name": "Gate Control Pack",
        "rules": [
            {"name": "Gate Line Crossing", "rule_type": "line_crossing", "severity": "medium",
             "object_type": "vehicle", "cooldown_sec": 5},
            {"name": "Blacklist Plate", "rule_type": "plate_blacklist", "severity": "critical"},
            {"name": "Stopped Vehicle at Gate", "rule_type": "stopped_vehicle", "severity": "medium",
             "duration_sec": 90},
        ],
    },
    {
        "name": "Crowd Monitor Pack",
        "rules": [
            {"name": "Crowd Alert", "rule_type": "crowd", "severity": "high", "min_count": 8},
            {"name": "Area Loitering", "rule_type": "loitering", "severity": "medium", "duration_sec": 60},
        ],
    },
]


def list_rule_types() -> List[str]:
    return list(RULE_TYPES.keys())


def rule_type_label(key: str) -> str:
    return RULE_TYPES.get(key, {}).get("label", key)


def fields_for(key: str) -> List[str]:
    return list(RULE_TYPES.get(key, {}).get("fields", []))


def defaults_for(key: str) -> Dict[str, Any]:
    meta = RULE_TYPES.get(key, {})
    out = dict(meta.get("defaults") or {})
    out.setdefault("severity", meta.get("default_severity", "medium"))
    return out
