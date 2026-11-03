"""One non-preemptible execution owner; estimates and overruns stay visible."""
from collections import deque
from dataclasses import dataclass
import threading
import time
from common.contracts import finite


@dataclass(frozen=True)
class Admission:
    allowed: bool
    reason: str
    remaining_ms: float
    required_ms: float


class SingleCuScheduler:
    def __init__(self, config):
        self.config = dict(config)
        self._lock = threading.Lock()
        self._samples = {"detection": deque(maxlen=128), "identity": deque(maxlen=128)}
        self.overruns = {"detection": 0, "identity": 0}
        self.identity_deferred = 0
        self.detections_since_identity = 0

    def estimated_ms(self, task):
        return max([self.config[task + "_ms"]] + list(self._samples[task]))

    def admit_identity(self, now_ms, deadline_ms):
        required = (self.estimated_ms("identity") + self.estimated_ms("detection")
                    + self.config["other_ms"] + self.config["margin_ms"])
        remaining = deadline_ms - now_ms
        if self.config["policy"] == "deadline_admission":
            allowed = required < remaining
            reason = "BUDGET_AVAILABLE" if allowed else "DETECTION_FIRST"
        else:
            allowed = self.detections_since_identity >= self.config["identity_every_n_detections"]
            reason = "PERIODIC_IDENTITY" if allowed else "DETECTION_FIRST"
        if not allowed:
            self.identity_deferred += 1
        return Admission(allowed, reason, remaining, required)

    def run(self, task, function):
        if task not in self._samples:
            raise ValueError("Unknown inference task")
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("Single inference CU is busy; queue at its owner")
        start = time.perf_counter()
        estimate = self.estimated_ms(task)
        try:
            return function()
        finally:
            self.observe(task, (time.perf_counter() - start) * 1000, estimate)
            if task == "detection":
                self.detections_since_identity += 1
            else:
                self.detections_since_identity = 0
            self._lock.release()

    def observe(self, task, elapsed_ms, estimate=None):
        if task not in self._samples or not finite(elapsed_ms) or elapsed_ms < 0:
            raise ValueError("Invalid measured task cost")
        estimate = self.estimated_ms(task) if estimate is None else estimate
        if elapsed_ms > estimate:
            self.overruns[task] += 1
        self._samples[task].append(elapsed_ms)

    def snapshot(self):
        return {"policy": self.config["policy"], "identity_deferred": self.identity_deferred,
                "estimates_ms": {k: self.estimated_ms(k) for k in self._samples},
                "overruns": dict(self.overruns), "execution": "non_preemptible_single_owner"}
