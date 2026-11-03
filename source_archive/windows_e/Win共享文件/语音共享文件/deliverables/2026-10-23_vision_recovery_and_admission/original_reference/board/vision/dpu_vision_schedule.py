"""One process, primary YOLO deadlines, optional bounded CNN jobs."""
from contextlib import contextmanager
import threading
import time
import math


class DpuVisionSchedule:
    def __init__(self, *, budget_ms=20, guard_ms=5, clock=time.monotonic, diagnostics=None,
                 yunet_recovery=False, yunet_slot_wait_ms=0, sface_slot_wait_ms=0):
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
        self._lease_sequence = 0
        self._diagnostic_failures = 0
        self.owner_fenced = False
        self.owner_fault_reason = None
        if yunet_recovery:
            from board.vision.dpu_recovery_policy import YuNetRecoveryPolicy
            self.yunet_recovery = YuNetRecoveryPolicy()
        if type(yunet_slot_wait_ms) is not int or not 0 <= yunet_slot_wait_ms <= 100:
            raise ValueError('YuNet slot wait must be an integer in 0..100 milliseconds')
        self.yunet_slot_wait_ms = yunet_slot_wait_ms
        self._slot_wait_stats = {'enabled': True, 'maximum_wait_ms': yunet_slot_wait_ms,
            'calls': 0, 'ready': 0, 'timeouts': 0, 'disabled': 0, 'condition_waits': 0,
            'total_wall_ms': 0., 'maximum_wall_ms': 0.}
        if type(sface_slot_wait_ms) is not int or not 0<=sface_slot_wait_ms<=100:
            raise ValueError('SFace slot wait must be an integer in 0..100 milliseconds')
        self.sface_slot_wait_ms=sface_slot_wait_ms
        self._sface_wait_stats=dict(self._slot_wait_stats,maximum_wait_ms=sface_slot_wait_ms)

    def _diagnostic_error(self):
        # Auxiliary failures must never retain the inference lease or replace
        # the original native exception, including failures in error().
        with self.condition:
            self._diagnostic_failures += 1
        try:
            self.diagnostics.error()
        except BaseException:
            pass

    def _discard_diagnostic(self, kind, trace=None):
        try:
            discard = getattr(self.diagnostics, 'discard_current', None)
            if callable(discard):discard(kind, trace)
        except BaseException:
            self._diagnostic_error()

    @contextmanager
    def primary(self, next_deadline):
        with self.condition:
            if self.owner_fenced:raise RuntimeError('DPU owner unavailable: native completion unconfirmed')
            self.next_primary = next_deadline
            self.waiting_primary += 1
            try:
                while self.active is not None:
                    self.condition.wait()
                    if self.owner_fenced:raise RuntimeError('DPU owner unavailable: native completion unconfirmed')
                self.active = 'yolo'
            finally:
                self.waiting_primary -= 1
        try:
            yield
        finally:
            with self.condition:
                try:
                    self.primary_calls += 1
                    primary_late = self.clock() > next_deadline
                    self.primary_overruns += int(primary_late)
                    if self.yunet_recovery is not None:
                        self._last_primary = self.clock()
                        if primary_late and self.yunet_recovery.primary_failed():
                            self.jobs['yunet']['disabled'] = True
                finally:
                    self.active = None
                    self.condition.notify_all()

    def disabled(self, kind):
        with self.condition:
            return self.owner_fenced or self.jobs.get(kind, {}).get('disabled', False)

    def optional_status(self, kind):
        with self.condition:
            result = dict(self.jobs.get(kind, {}))
            if kind == 'yunet' and self.yunet_recovery is not None:
                result['recovery'] = self.yunet_recovery.snapshot()
            return result

    def _recovery_due(self, kind):
        policy = self.yunet_recovery
        return (not self.owner_fenced and kind == 'yunet' and policy is not None and policy.due(self.clock(),
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

    def wait_for_optional(self, kind, deadline):
        """Wait for a scheduling opportunity; caller still acquires normally.

        No slot, image or native job is owned here. Both ordinary admission
        and the pre-execute freshness callback run again after notification.
        """
        if kind not in ('yunet','sface'):raise ValueError('Unknown optional notification kind')
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError('Finite monotonic admission deadline required')
        limit=self.yunet_slot_wait_ms if kind=='yunet' else self.sface_slot_wait_ms
        if not limit:return False
        began = self.clock()
        until = min(deadline, began+limit/1000.)
        with self.condition:
            stats = self._slot_wait_stats if kind=='yunet' else self._sface_wait_stats
            stats['calls'] += 1
            try:
                while True:
                    now = self.clock()
                    if now >= until:
                        stats['timeouts'] += 1; return False
                    job = self.jobs.get(kind, {})
                    if self.owner_fenced or (job.get('disabled', False) and not self._recovery_due(kind)):
                        stats['disabled'] += 1; return False
                    estimate = max(self.budget, job.get('estimated_budget_ms', self.budget*1000.)/1000.)
                    if (self.active is None and not self.waiting_primary
                            and self.next_primary-now >= estimate+self.guard):
                        stats['ready'] += 1; return True
                    stats['condition_waits'] += 1
                    # Releases the scheduler condition and the GIL. Existing
                    # primary/optional completion notify_all wakes this wait.
                    self.condition.wait(until-now)
            finally:
                elapsed = max(0., self.clock()-began)*1000.
                stats['total_wall_ms'] += elapsed
                stats['maximum_wall_ms'] = max(stats['maximum_wall_ms'], elapsed)

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
            acquired = (not self.owner_fenced and (not stats['disabled'] or recovering) and self.active is None and not self.waiting_primary
                        and self.next_primary - self.clock() >= estimate + self.guard)
            if acquired:
                started = self.clock()
                self.active = kind
                self._lease_sequence += 1
                lease_sequence = self._lease_sequence
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
        if diagnostics is not None:
            try:
                if diagnostics.enabled:
                    trace = diagnostics.begin(kind,acquired,rejection,estimate*1000.,diagnostic_deadline)
                if acquired and isinstance(trace, dict):
                    trace.update(lease_sequence=lease_sequence, lease_started_mono_ns=int(started*1e9))
            except BaseException:
                self._diagnostic_error()
                self._discard_diagnostic(kind)
                trace = None
        body_failed = False
        native_not_submitted = False
        native_unknown = False
        try:
            yield acquired
        except BaseException as exc:
            body_failed = True
            native_not_submitted = getattr(exc, 'native_not_submitted', False) is True
            native_unknown = getattr(exc, 'native_execution_unknown', False) is True
            raise
        finally:
            if acquired:
                finish_arguments = None
                with self.condition:
                    try:
                        elapsed = self.clock() - started
                        stats['calls'] += 1
                        stats['maximum_ms'] = max(stats['maximum_ms'], elapsed * 1000.)
                        if elapsed > estimate:
                            stats['budget_exceeded'] += 1
                            stats['estimated_budget_ms'] = min(30., elapsed * 1000. + 2.)
                        hardcap_exceeded = elapsed > .030
                        guard_exceeded = self.clock() > finish_deadline
                        failed_native = body_failed and not native_not_submitted
                        if native_unknown:
                            self.owner_fenced = True
                            self.owner_fault_reason = 'NATIVE_COMPLETION_UNCONFIRMED'
                        if hardcap_exceeded or guard_exceeded:
                            stats['overruns'] += 1
                            stats['disabled'] = True
                            stats['last_overrun'] = {'elapsed_ms': elapsed * 1000.,
                                'finish_after_guard_ms': (self.clock() - finish_deadline) * 1000.,
                                'waiting_primary': self.waiting_primary}
                        if failed_native:stats['disabled'] = True
                        if self.yunet_recovery is not None and kind == 'yunet':
                            if hardcap_exceeded or guard_exceeded or failed_native:
                                self.yunet_recovery.fault(self.clock(), completed=self._native_completed,
                                    body_failed=body_failed, hardcap=hardcap_exceeded, guard=guard_exceeded,
                                    primary_calls=self.primary_calls, primary_overruns=self.primary_overruns)
                            elif self._native_completed:
                                self.yunet_recovery.success()
                        finish_arguments = (kind, trace, elapsed*1000.,
                            (self.clock()-finish_deadline)*1000.,self.waiting_primary,
                            hardcap_exceeded,guard_exceeded,body_failed)
                        if isinstance(trace, dict):
                            trace['lease_release_decision_mono_ns'] = int(self.clock()*1e9)
                    finally:
                        # The native body has returned/raised. Protection and
                        # recovery decisions precede release; auxiliary trace
                        # aggregation runs after releasing the condition.
                        self._native_owner = None
                        self._native_completed = False
                        self.active = None
                        self.condition.notify_all()
                if trace is not None and finish_arguments is not None:
                    try:
                        if isinstance(trace, dict):
                            trace['after_release_observed_mono_ns'] = int(self.clock()*1e9)
                        diagnostics.finish(*finish_arguments)
                    except BaseException:
                        self._diagnostic_error()
                        self._discard_diagnostic(kind, trace)

    def health(self):
        with self.condition:
            result = {'active': self.active, 'primary_calls': self.primary_calls,
                    'primary_period_overruns': self.primary_overruns,
                    'waiting_primary': self.waiting_primary, 'budget_ms': self.budget * 1000.,
                    'guard_ms': self.guard * 1000., 'optional': {k: dict(v) for k, v in self.jobs.items()},
                    'lease_sequence':self._lease_sequence,'diagnostic_failures':self._diagnostic_failures,
                    'owner_fenced':self.owner_fenced,'owner_fault_reason':self.owner_fault_reason,
                    'diagnostic_snapshot_atomic_with_schedule':False,
                    'occupancy_scope':'admission through pre-release protection decision; auxiliary finish runs after release'}
            if self.yunet_recovery is not None:
                result['yunet_recovery'] = self.yunet_recovery.snapshot()
            if self.yunet_slot_wait_ms:
                result['yunet_slot_wait'] = dict(self._slot_wait_stats)
            if self.sface_slot_wait_ms:
                result['sface_slot_wait']=dict(self._sface_wait_stats)
        try:
            result['optional_diagnostics'] = self.diagnostics.snapshot() if self.diagnostics is not None else {'enabled':False}
        except BaseException:
            self._diagnostic_error()
            result['optional_diagnostics'] = {'enabled':True,'snapshot_unavailable':True}
        return result
