"""Bounded frame buffer with drop-when-behind policy."""
from __future__ import annotations

from collections import deque
from typing import Optional, Any
from threading import Lock
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BufferedFrame:
    frame: Any
    timestamp: datetime
    frame_index: int


class FrameBuffer:
    def __init__(self, maxsize: int = 30):
        self._queue: deque = deque(maxlen=maxsize)
        self._lock = Lock()
        self._dropped = 0

    def put(self, frame: Any, timestamp: datetime, frame_index: int) -> None:
        with self._lock:
            if len(self._queue) == self._queue.maxlen:
                self._dropped += 1
            self._queue.append(BufferedFrame(frame, timestamp, frame_index))

    def get(self) -> Optional[BufferedFrame]:
        with self._lock:
            if not self._queue:
                return None
            return self._queue.popleft()

    def clear(self) -> None:
        with self._lock:
            self._queue.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def dropped(self) -> int:
        return self._dropped
