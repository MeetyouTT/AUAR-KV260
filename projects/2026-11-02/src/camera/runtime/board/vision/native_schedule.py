"""Business/health facade; native code alone owns the shared DPU lease.

No Python lock spans an inference call. Notification waits are performed by the
native condition variable and release the GIL without acquiring a DPU lease.
"""
from contextlib import contextmanager
import copy
import math
import threading
import time

from board.vision.native_protection import PHASES, REASONS


class NativeDpuSchedule:
    native_critical = True

    def __init__(self, context, *, yunet_slot_wait_ms=0, sface_slot_wait_ms=0,
                 inherited_optional=None, inherited_sface_counters=None, diagnostics=None):
        self.context = context
        self._local = threading.local()
        self._metrics_lock = threading.Lock()
        self._last_reports = {}
        self._inherited = copy.deepcopy(inherited_optional or {})
        self.inherited_sface_counters = dict(inherited_sface_counters or {})
        self.diagnostics = diagnostics
        self.protection_handoff = {}
        self._wait = {}
        for task, limit in (('yunet', yunet_slot_wait_ms), ('sface', sface_slot_wait_ms)):
            if type(limit) is not int or not 0 <= limit <= 100:
                raise ValueError('Native optional notification wait must be in 0..100ms')
            setattr(self, task+'_slot_wait_ms', limit)
            self._wait[task] = dict(enabled=bool(limit), maximum_wait_ms=limit,
                calls=0, ready=0, timeouts=0, total_wall_ms=0., maximum_wall_ms=0.)

    @staticmethod
    def _task(kind):
        if kind not in ('yunet', 'sface'):raise ValueError('Unknown optional task')
        return 1 if kind == 'yunet' else 2

    @contextmanager
    def primary(self, next_deadline):
        if type(next_deadline) not in (int,float) or not math.isfinite(next_deadline) or next_deadline <= 0:
            raise ValueError('Finite original primary deadline required')
        if getattr(self._local, 'primary_deadline_ns', None) is not None:
            raise RuntimeError('Nested primary business scope')
        deadline = int(next_deadline * 1e9)
        self.context.announce_primary(deadline)
        self._local.primary_deadline_ns = deadline
        try:
            # Only a thread-local deadline is retained here. The native YOLO
            # call acquires/releases the actual gate, before regaining the GIL.
            yield
        finally:
            self._local.primary_deadline_ns = None

    def primary_deadline_ns(self):
        value = getattr(self._local, 'primary_deadline_ns', None)
        if value is None:raise RuntimeError('YOLO business inference requires the original primary scope')
        return value

    def optional(self, kind):
        raise RuntimeError('Legacy Python optional execution lease is forbidden for native execution')

    def native_starting(self, kind):
        raise RuntimeError('Native recovery is owned by the compiled execution path')

    def native_completed(self, kind, *, usable=True):
        raise RuntimeError('Native completion is confirmed through the result-token protocol')

    def _snapshot(self):
        return self.context.snapshot()

    def disabled(self, kind):
        task = self._task(kind)
        state = self._snapshot()
        return bool(state['fenced'] or state['quiesced'] or self.context.quarantined or state['disabled'][task])

    @staticmethod
    def _policy(state, index):
        raw = state['recovery'][index]
        return dict(enabled=bool(raw['enabled']), phase=PHASES[raw['phase']], reason=REASONS[raw['reason']],
            cooldown_s=10., window_s=600., maximum_attempts=2, required_successes=3,
            probe_successes=raw['probe_successes'], faults=raw['faults'], attempts=raw['attempts'],
            recoveries=raw['recoveries'], cooldown_until_monotonic_s=raw['cooldown_until_ns']/1e9,
            attempts_in_window=(raw['opaque_attempt_count'] if raw['history_opaque'] else raw['attempt_count']),
            history_opaque=bool(raw['history_opaque']))

    def optional_status(self, kind):
        task = self._task(kind)
        state = self._snapshot()
        result = copy.deepcopy(self._inherited.get(kind, {}))
        result.update(calls=state['admissions'][task], overruns=state['overruns'][task],
            disabled=bool(state['disabled'][task] or state['fenced'] or self.context.quarantined),
            native_completed=state['completed'][task], native_failures=state['native_failures'][task],
            not_submitted=state['not_submitted'][task], estimated_budget_ms=30.,
            recovery=self._policy(state, task-1), pending_result_token=state['pending_result_tokens'][task])
        with self._metrics_lock:
            report = copy.deepcopy(self._last_reports.get(kind))
        if report is not None:result['last_native_report'] = report
        return result

    def recovery_ready(self, kind):
        task = self._task(kind)
        state = self._snapshot()
        policy = state['recovery'][task-1]
        if state['fenced'] or self.context.quarantined or policy['phase'] != 1 or policy['history_opaque']:
            return False
        # A native query performs the policy's due/primary checks. It may wait
        # at most 1ms for an opportunity and owns no execution lease.
        return self.context.wait_optional(task, time.monotonic_ns()+1_000_000)

    def recovery_probe_allowed(self, kind):
        task = self._task(kind)
        state = self._snapshot()
        if state['fenced'] or self.context.quarantined:return False
        if state['recovery'][task-1]['phase'] == 2 and not state['disabled'][task]:return True
        return self.recovery_ready(kind)

    def wait_for_optional(self, kind, deadline):
        task = self._task(kind)
        if type(deadline) not in (int,float) or not math.isfinite(deadline):
            raise ValueError('Finite notification deadline required')
        limit = getattr(self, kind+'_slot_wait_ms')
        if not limit:return False
        began = time.monotonic_ns()
        until = min(int(deadline*1e9), began+limit*1_000_000)
        if until <= began:return False
        ready = self.context.wait_optional(task, until)
        elapsed = (time.monotonic_ns()-began)/1e6
        with self._metrics_lock:
            stats = self._wait[kind]
            stats['calls'] += 1
            stats['ready' if ready else 'timeouts'] += 1
            stats['total_wall_ms'] += elapsed
            stats['maximum_wall_ms'] = max(stats['maximum_wall_ms'], elapsed)
        return ready

    def note_result(self, kind, report):
        self._task(kind)
        # This runs after native release/confirmation. It has no authority over
        # admission, native completion, recovery counters or protected state.
        with self._metrics_lock:
            self._last_reports[kind] = dict(report)

    def health(self):
        state = self._snapshot()
        with self._metrics_lock:wait = copy.deepcopy(self._wait)
        active = ('yolo','yunet','sface')[state['active_task']] if state['active'] and state['active_task']<3 else None
        return dict(active=active, primary_calls=state['primary_calls'],
            primary_period_overruns=state['primary_period_overruns'], waiting_primary=state['primary_waiting'],
            budget_ms=20., guard_ms=5., admission_floor_ms=30.,
            optional={kind:self.optional_status(kind) for kind in ('yunet','sface')},
            yunet_recovery=self._policy(state,0), sface_recovery=self._policy(state,1),
            owner_fenced=bool(state['fenced'] or self.context.quarantined),
            owner_fault_reason=state['fence_reason'] or None, seed_loaded=bool(state['seed_loaded']),
            quiesced=bool(state['quiesced']), checkpoint_kind=state['checkpoint_kind'],
            diagnostic_failures=0, diagnostic_snapshot_atomic_with_schedule=False,
            occupancy_scope='native start through retained release decision; after-unlock upper endpoint retained',
            optional_diagnostics=dict(enabled=False, mode='NATIVE_C_ABI_REPORTS',
                inherited_provenance_retained=bool(self._inherited)),
            native_critical=True, native_abi=2, protection_handoff=copy.deepcopy(self.protection_handoff),
            yunet_slot_wait=wait['yunet'], sface_slot_wait=wait['sface'])
