"""Manages which AI tasks are active for a camera."""
from __future__ import annotations

from typing import List, Set


class TaskManager:
    def __init__(self, enabled_tasks: List[str] | None = None):
        self._tasks: Set[str] = set(enabled_tasks or [])

    def set_tasks(self, tasks: List[str]) -> None:
        self._tasks = set(tasks)

    def is_enabled(self, task_name: str) -> bool:
        if task_name in self._tasks:
            return True
        # fuzzy: ANPR aliases
        aliases = {
            "ANPR / OCR": ("ANPR", "OCR", "License Plate", "ANPR / OCR"),
            "License Plate Detection": ("License Plate", "ANPR", "Plate"),
        }
        keys = aliases.get(task_name)
        if keys:
            for t in self._tasks:
                tl = t.lower()
                if any(k.lower() in tl for k in keys):
                    return True
        return False

    def enabled_tasks(self) -> List[str]:
        return sorted(self._tasks)

    def has_anpr(self) -> bool:
        return self.is_enabled("ANPR / OCR") or self.is_enabled("License Plate Detection")

    def has_any_detection(self) -> bool:
        return bool(
            self._tasks
            & {
                "Person Detection",
                "Vehicle Detection",
                "Face Detection",
                "License Plate Detection",
                "ANPR / OCR",
            }
        ) or self.has_anpr()
