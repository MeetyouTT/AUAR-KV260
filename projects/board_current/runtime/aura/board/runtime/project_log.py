"""Small structured trace; records references/timings rather than raw media."""
from collections import Counter
import json
from pathlib import Path
import threading


class ProjectTrace:
    def __init__(self, release_id, environment, path=None):
        self.release_id, self.environment = release_id, environment
        self.counts = Counter()
        self._lock = threading.Lock()
        self.handle = None
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.handle = Path(path).open("x", encoding="utf-8")

    def record(self, kind, now_ms, **fields):
        event = {"schema_version": "aura-trace-1", "release_id": self.release_id,
                 "environment": self.environment, "kind": kind, "at_ms": now_ms, **fields}
        with self._lock:
            self.counts[kind] += 1
            if self.handle:
                self.handle.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
                self.handle.flush()
        return event

    def close(self):
        if self.handle:
            self.handle.close()
