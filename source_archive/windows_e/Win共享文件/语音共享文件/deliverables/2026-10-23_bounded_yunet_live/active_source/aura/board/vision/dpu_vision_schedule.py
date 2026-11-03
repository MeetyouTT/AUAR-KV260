"""One process, primary YOLO deadlines, optional bounded CNN jobs."""
from contextlib import contextmanager
import threading
import time


class DpuVisionSchedule:
    def __init__(self, *, budget_ms=20, guard_ms=5, clock=time.monotonic, diagnostics=None,
                 yunet_recovery=False):
        if not 5 <= budget_ms <= 30 or not 1 <= guard_ms <= 20:
            raise ValueError('Invalid DPU budget')
        self.clock, self.budget, self.guard = clock, budget_ms / 1000., guard_ms / 1000.
        self.condition = threading.Condition()
        self.active, self.waiting_primary, self.next_primary = None, 0, 0.
        self.primary_calls = self.primary_overruns = 0
        self.jobs = {}
        self.diagnostics = diagnostics
        if type(yunet_recovery) is not bool:
            raise ValueError('YuNet recovery requires an explicit boolean')
        self.yunet_recovery = None
        self._last_primary = None
        self._native_owner = None
        self._native_completed = False
        if yunet_recovery:
            from board.vision.dpu_recovery_policy import YuNetRecoveryPolicy
            self.yunet_recovery = YuNetRecoveryPolicy()

    @contextmanager
    def primary(self, next_deadline):
        with self.condition:
            self.next_primary = next_deadline
            self.waiting_primary += 1
            try:
                while self.active is not None:
                    self.condition.wait()
                self.active = 'yolo'
            finally:
                self.waiting_primary -= 1
        try:
            yield
        finally:
            with self.condition:
                self.primary_calls += 1
                primary_late = self.clock() > next_deadline
                self.primary_overruns += int(primary_late)
                if self.yunet_recovery is not None:
                    self._last_primary = self.clock()
                    if primary_late and self.yunet_recovery.primary_failed():
                        self.jobs['yunet']['disabled'] = True
                self.active = None
                self.condition.notify_all()

    def disabled(self, kind):
        with self.condition:
            return self.jobs.get(kind, {}).get('disabled', False)

    def _recovery_due(self, kind):
        policy = self.yunet_recovery
        return (kind == 'yunet' and policy is not None and policy.due(self.clock(),
                primary_calls=self.primary_calls, primary_overruns=self.primary_overruns,
                last_primary=self._last_primary))

    def recovery_ready(self, kind):
        with self.condition:
            return (self.jobs.get(kind, {}).get('disabled', False)
                    and self.active is None and not self.waiting_primary
                    and self._recovery_due(kind))

    def native_completed(self, kind):
        if self.yunet_recovery is None or kind != 'yunet':
            return
        with self.condition:
            if self.active != kind or self._native_owner != (kind, threading.get_ident()):
                raise RuntimeError('Native completion does not own the active slot')
            self._native_completed = True

    @contextmanager
    def optional(self, kind):
        if kind not in ('yunet', 'sface'):
            raise ValueError('Unknown optional DPU task')
        with self.condition:
            stats = self.jobs.setdefault(kind, {'calls': 0, 'skipped': 0, 'overruns': 0,
                'budget_exceeded': 0, 'estimated_budget_ms': self.budget * 1000.,
                'maximum_ms': 0., 'disabled': False})
            estimate = max(self.budget, stats['estimated_budget_ms'] / 1000.)
            recovering = stats['disabled'] and self._recovery_due(kind)
            acquired = ((not stats['disabled'] or recovering) and self.active is None and not self.waiting_primary
                        and self.next_primary - self.clock() >= estimate + self.guard)
            if acquired:
                self.active, started = kind, self.clock()
                finish_deadline = self.next_primary - self.guard
                if self.yunet_recovery is not None and kind == 'yunet':
                    self._native_owner = (kind, threading.get_ident())
                    self._native_completed = False
                    if recovering:
                        self.yunet_recovery.admitted(started)
                        stats['disabled'] = False
            else:
                stats['skipped'] += 1
            rejection = ('disabled' if stats['disabled'] else 'active' if self.active is not None
                         else 'primary_waiting' if self.waiting_primary else 'deadline')
            diagnostic_deadline = self.next_primary-self.guard
        trace = None
        diagnostics = self.diagnostics
        if diagnostics is not None and diagnostics.enabled:
            try:trace = diagnostics.begin(kind,acquired,rejection,estimate*1000.,diagnostic_deadline)
            except Exception:diagnostics.error()
        body_failed = False
        native_not_submitted = False
        try:
            yield acquired
        except BaseException as exc:
            body_failed = True
            native_not_submitted = getattr(exc, 'native_not_submitted', False) is True
            raise
        finally:
            if acquired:
                with self.condition:
                    elapsed = self.clock() - started
                    stats['calls'] += 1
                    stats['maximum_ms'] = max(stats['maximum_ms'], elapsed * 1000.)
                    if elapsed > estimate:
                        stats['budget_exceeded'] += 1
                        stats['estimated_budget_ms'] = min(30., elapsed * 1000. + 2.)
                    # A one-off estimate miss within the admitted deadline is
                    # different from blocking the primary workload. Enforce the
                    # actual deadline plus a hard 30 ms optional occupancy cap.
                    hardcap_exceeded = elapsed > .030
                    guard_exceeded = self.clock() > finish_deadline
                    if hardcap_exceeded or guard_exceeded:
                        stats['overruns'] += 1
                        stats['disabled'] = True
                        stats['last_overrun'] = {'elapsed_ms': elapsed * 1000.,
                            'finish_after_guard_ms': (self.clock() - finish_deadline) * 1000.,
                            'waiting_primary': self.waiting_primary}
                    if self.yunet_recovery is not None and kind == 'yunet':
                        if hardcap_exceeded or guard_exceeded or (body_failed and not native_not_submitted):
                            stats['disabled'] = True
                            self.yunet_recovery.fault(self.clock(), completed=self._native_completed,
                                body_failed=body_failed, hardcap=hardcap_exceeded, guard=guard_exceeded,
                                primary_calls=self.primary_calls, primary_overruns=self.primary_overruns)
                        elif self._native_completed:
                            self.yunet_recovery.success()
                        self._native_owner = None
                        self._native_completed = False
                    if trace is not None:
                        try:diagnostics.finish(kind,trace,elapsed*1000.,
                            (self.clock()-finish_deadline)*1000.,self.waiting_primary,
                            hardcap_exceeded,guard_exceeded,body_failed)
                        except Exception:diagnostics.error()
                    self.active = None
                    self.condition.notify_all()

    def health(self):
        with self.condition:
            result = {'active': self.active, 'primary_calls': self.primary_calls,
                    'primary_period_overruns': self.primary_overruns,
                    'waiting_primary': self.waiting_primary, 'budget_ms': self.budget * 1000.,
                    'guard_ms': self.guard * 1000., 'optional': {k: dict(v) for k, v in self.jobs.items()},
                    'optional_diagnostics':self.diagnostics.snapshot() if self.diagnostics is not None else {'enabled':False}}
            if self.yunet_recovery is not None:
                result['yunet_recovery'] = self.yunet_recovery.snapshot()
            return result
