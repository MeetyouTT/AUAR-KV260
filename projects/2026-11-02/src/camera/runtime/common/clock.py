import time
import uuid
from .contracts import integer


class MonotonicClock:
    def __init__(self):
        self.domain = "runtime-monotonic:" + uuid.uuid4().hex

    def now_ms(self):
        return time.monotonic_ns() // 1000000


class SimulationClock:
    def __init__(self, start_ms=1000):
        if not integer(start_ms):
            raise ValueError("Invalid simulation time")
        self.domain = "simulation:" + uuid.uuid4().hex
        self._now = start_ms

    def now_ms(self):
        return self._now

    def advance(self, milliseconds):
        if not integer(milliseconds):
            raise ValueError("Simulation time cannot reverse")
        self._now += milliseconds
