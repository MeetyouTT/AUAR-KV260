from dataclasses import dataclass
import threading
from typing import Any
from common.contracts import FrameRef


@dataclass(frozen=True)
class CapturedFrame:
    ref: FrameRef
    image: Any


class LatestFrameSlot:
    """One bounded slot: slow inference never builds an old-image queue."""
    def __init__(self):
        self._lock = threading.Lock()
        self._frame = None
        self.dropped = 0

    def put(self, frame):
        with self._lock:
            if self._frame is not None:
                self.dropped += 1
            self._frame = frame

    def take(self):
        with self._lock:
            frame, self._frame = self._frame, None
            return frame
