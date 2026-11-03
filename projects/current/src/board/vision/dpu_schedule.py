"""One process owns the DPU; detection wins, identity never queues behind it."""
from contextlib import contextmanager
import threading
import time


class DpuSchedule:
    def __init__(self, *, identity_budget_ms=20, guard_ms=5, clock=time.monotonic):
        if not 5 <= identity_budget_ms <= 30 or not 1 <= guard_ms <= 20:
            raise ValueError('Invalid DPU scheduling budget')
        self.clock = clock
        self.budget, self.guard = identity_budget_ms/1000, guard_ms/1000
        self.condition = threading.Condition()
        self.active, self.waiting_detection = None, 0
        self.next_detection = 0
        self.identity_disabled = False
        self.detection_calls = self.identity_calls = self.identity_skipped = self.identity_overruns = 0
        self.maximum_detection_wait_ms = self.maximum_identity_ms = 0.

    @contextmanager
    def detection(self, next_deadline):
        queued = self.clock()
        with self.condition:
            self.next_detection = next_deadline
            self.waiting_detection += 1
            try:
                while self.active is not None:self.condition.wait()
                self.active = 'detection'
                self.maximum_detection_wait_ms = max(self.maximum_detection_wait_ms, (self.clock()-queued)*1000)
            finally:
                self.waiting_detection -= 1
        try:
            yield
        finally:
            with self.condition:
                self.detection_calls += 1
                self.active = None
                self.condition.notify_all()

    @contextmanager
    def identity(self):
        with self.condition:
            acquired = (not self.identity_disabled and self.active is None and not self.waiting_detection
                        and self.next_detection-self.clock() >= self.budget+self.guard)
            if acquired:
                self.active = 'identity'
                started = self.clock()
            else:
                self.identity_skipped += 1
        try:
            yield acquired
        finally:
            if acquired:
                with self.condition:
                    elapsed = self.clock()-started
                    self.identity_calls += 1
                    self.maximum_identity_ms = max(self.maximum_identity_ms, elapsed*1000)
                    if elapsed > self.budget:
                        # Submitted DPU work cannot be preempted. Stop future
                        # identity tasks after an overrun to protect detection.
                        self.identity_overruns += 1
                        self.identity_disabled = True
                    self.active = None
                    self.condition.notify_all()

    def health(self):
        with self.condition:
            return {'active': self.active, 'waiting_detection': self.waiting_detection,
                'detection_calls': self.detection_calls, 'identity_calls': self.identity_calls,
                'identity_skipped': self.identity_skipped, 'identity_overruns': self.identity_overruns,
                'identity_disabled': self.identity_disabled, 'identity_budget_ms': self.budget*1000,
                'maximum_detection_wait_ms': round(self.maximum_detection_wait_ms, 3),
                'maximum_identity_ms': round(self.maximum_identity_ms, 3)}
