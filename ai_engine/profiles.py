"""AI Profile definitions.

AI tasks answer: "What can the camera detect?"
Security rules (future) answer: "What should happen when something is detected?"
"""
from __future__ import annotations

from typing import Dict, List

# Available individual tasks
ALL_TASKS = [
    "Person Detection",
    "Vehicle Detection",
    "Face Detection",
    "Face Recognition",
    "License Plate Detection",
    "ANPR / OCR",
    "Vehicle Classification",
    "Tracking",
]

# Profile -> default enabled tasks
AI_PROFILES: Dict[str, List[str]] = {
    "ANPR": [
        "Vehicle Detection",
        "License Plate Detection",
        "ANPR / OCR",
        "Vehicle Classification",
        "Tracking",
    ],
    "Person Monitoring": [
        "Person Detection",
        "Face Detection",
        "Face Recognition",
        "Tracking",
    ],
    "Vehicle Monitoring": [
        "Vehicle Detection",
        "Vehicle Classification",
        "Tracking",
    ],
    "General Detection": [
        "Person Detection",
        "Vehicle Detection",
        "Tracking",
    ],
    "Custom": [],  # user selects freely
}


def get_profile_tasks(profile_name: str) -> List[str]:
    return list(AI_PROFILES.get(profile_name, []))


def list_profiles() -> List[str]:
    return list(AI_PROFILES.keys())
