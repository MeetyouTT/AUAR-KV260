"""Bounded numeric stage timings. No frames, vectors, names or track IDs.

All durations use monotonic_ns; source ages retain the existing appsink-dequeue
millisecond semantics. Quantiles describe the recent bounded window only.
"""
from collections import deque
import math
import threading
import time


STAGES = frozenset({
    'capture.callback_prepare', 'yolo.schedule_wait', 'yolo.native_and_decode',
    'yolo.track', 'yolo.path', 'yolo.source_age_at_start', 'yolo.publish_source_age',
    'preview.render_encode_publish', 'preview.publish_source_age',
    'yunet.allocate', 'yunet.slot_wait', 'yunet.execute_wait', 'yunet.dequantize',
    'sface.allocate', 'sface.slot_wait', 'sface.execute_wait', 'sface.dequantize',
    'sface.normalize_input', 'sface.validate_output',
})


class PipelineMetrics:
    def __init__(self, *, enabled=False, capacity=256, diagnostics_enabled=False):
        if type(enabled) is not bool or type(capacity) is not int or not 16 <= capacity <= 1024:
            raise ValueError('Invalid bounded pipeline metrics configuration')
        self.enabled, self.capacity = enabled, capacity
        self.lock = threading.Lock()
        self.stages = {}
        self.optional_diagnostics = OptionalDiagnostics(enabled=diagnostics_enabled)

    def value(self, stage, milliseconds):
        if not self.enabled:
            return
        if stage not in STAGES or type(milliseconds) not in (float, int) or not math.isfinite(milliseconds) or milliseconds < 0:
            raise ValueError('Invalid numeric pipeline timing')
        with self.lock:
            row = self.stages.setdefault(stage, {'count':0, 'sum':0., 'minimum':None,
                'maximum':None, 'recent':deque(maxlen=self.capacity)})
            row['count'] += 1
            row['sum'] += milliseconds
            row['minimum'] = milliseconds if row['minimum'] is None else min(row['minimum'], milliseconds)
            row['maximum'] = milliseconds if row['maximum'] is None else max(row['maximum'], milliseconds)
            row['recent'].append(float(milliseconds))

    def elapsed(self, stage, started_ns):
        if self.enabled:
            self.value(stage, (time.monotonic_ns()-started_ns)/1e6)

    def snapshot(self):
        if not self.enabled:
            return {'enabled':False}
        with self.lock:
            copied={key:{**{k:v for k,v in value.items() if k!='recent'},
                'recent':tuple(value['recent'])} for key,value in self.stages.items()}
        rows={}
        for key,value in copied.items():
            recent=sorted(value['recent']);n=len(recent)
            rows[key]={'count':value['count'], 'total_ms':value['sum'],
                'mean_ms':value['sum']/value['count'], 'min_ms':value['minimum'],
                'max_ms':value['maximum'], 'recent_count':n,
                'recent_p50_ms':recent[math.ceil(.5*n)-1],
                'recent_p95_ms':recent[math.ceil(.95*n)-1]}
        return {'enabled':True,'schema_version':'aura-pipeline-metrics-1',
            'clock':'monotonic_ns', 'unit':'milliseconds', 'capacity_per_stage':self.capacity,
            'quantile_scope':'most recent bounded samples per stage; not all calls or health-snapshot quantiles',
            'source_age_scope':'existing appsink-dequeue timestamp; not sensor exposure or glass-to-glass',
            'yolo_native_scope':'native preprocessing + DPU + native decode; not DPU-only time',
            'stages':rows,'optional_diagnostics':self.optional_diagnostics.snapshot()}


TASK_CODES = {'yunet':1, 'sface':2}
REJECTION_CODES = {'disabled':1, 'active':2, 'primary_waiting':3, 'deadline':4}


class OptionalDiagnostics:
    """At most 8 numeric fault events, same owner/clock, no I/O or background work.

Thread CPU is the CALLING Python/native thread only. Wall minus this CPU is
not hardware time; it includes waits, descheduling, GIL, and other contention.
"""
    CAPACITY = 8

    def __init__(self, *, enabled=False, clock_ns=time.monotonic_ns,
                 thread_clock_ns=getattr(time,'thread_time_ns',None)):
        if type(enabled) is not bool or not callable(clock_ns):
            raise ValueError('Invalid optional diagnostic configuration')
        self.enabled, self.clock, self.thread_clock = enabled, clock_ns, thread_clock_ns
        self.lock, self.local = threading.Lock(), threading.local()
        self.started_mono_ns = self.clock() if enabled else None
        self.events = deque(maxlen=self.CAPACITY)
        self.active, self.counters = {}, {}
        self.sequence = self.diagnostic_errors = self.evicted_events = 0

    def _thread_ns(self):
        if not callable(self.thread_clock): return -1
        try:return int(self.thread_clock())
        except Exception:return -1

    @staticmethod
    def _counter():
        return {'requests':0,'admitted':0,'rejected':0,'rejected_disabled':0,
                'rejected_active':0,'rejected_primary_waiting':0,'rejected_deadline':0,
                'native_attempts':0,'native_execute_returned':0,'native_wait_entered':0,
                'native_wait_returned':0,'native_completed':0,'native_failed':0,
                'admitted_without_native':0,'optional_finished':0,'faults':0}

    def error(self):
        if self.enabled:
            with self.lock:self.diagnostic_errors += 1

    def begin(self, kind, admitted, rejection, estimate_ms, guard_deadline_s):
        if not self.enabled:return None
        if kind not in TASK_CODES:raise ValueError('Invalid optional diagnostic task')
        now, cpu = self.clock(), self._thread_ns()
        with self.lock:
            row = self.counters.setdefault(kind,self._counter())
            row['requests'] += 1
            if not admitted:
                row['rejected'] += 1
                row['rejected_'+rejection] += 1
                return None
            row['admitted'] += 1
            self.sequence += 1
            trace = {'event_sequence':self.sequence,'task_code':TASK_CODES[kind],
                'optional_start_mono_ns':now,'optional_start_thread_cpu_ns':cpu,
                'optional_end_mono_ns':0,'optional_end_thread_cpu_ns':-1,
                'last_mark_mono_ns':now,'last_mark_thread_cpu_ns':cpu,'phase_code':0,
                'guard_deadline_mono_ns':int(guard_deadline_s*1e9),'estimated_budget_ms':float(estimate_ms),
                'execute_start_mono_ns':0,'execute_return_mono_ns':0,
                'execute_start_thread_cpu_ns':-1,'execute_return_thread_cpu_ns':-1,
                'wait_start_mono_ns':0,'wait_end_mono_ns':0,
                'wait_start_thread_cpu_ns':-1,'wait_end_thread_cpu_ns':-1,
                'native_attempts':0,'native_completed':0,'native_failed':0,
                'native_status':-2147483648,'native_failure_phase_code':0}
            self.active[kind] = trace
            self.local.trace = (kind,trace)
            return trace

    def native_mark(self, kind, phase, status=None):
        if not self.enabled:return
        current = getattr(self.local,'trace',None)
        if current is None or current[0] != kind:return
        now, cpu = self.clock(), self._thread_ns()
        with self.lock:
            trace = current[1]
            row = self.counters[kind]
            trace['last_mark_mono_ns'],trace['last_mark_thread_cpu_ns'] = now,cpu
            if phase == 'execute_start':
                trace['phase_code'] = 1
                trace['execute_start_mono_ns'],trace['execute_start_thread_cpu_ns'] = now,cpu
                trace['native_attempts'] += 1
                row['native_attempts'] += 1
            elif phase == 'execute_return':
                trace['phase_code'] = 2
                trace['execute_return_mono_ns'],trace['execute_return_thread_cpu_ns'] = now,cpu
                row['native_execute_returned'] += 1
            elif phase == 'wait_start':
                trace['phase_code'] = 3
                trace['wait_start_mono_ns'],trace['wait_start_thread_cpu_ns'] = now,cpu
                row['native_wait_entered'] += 1
            elif phase == 'wait_end':
                trace['phase_code'] = 4
                trace['wait_end_mono_ns'],trace['wait_end_thread_cpu_ns'] = now,cpu
                trace['native_status'] = int(status) if type(status) is int else -2147483648
                row['native_wait_returned'] += 1
                if status == 0:
                    trace['native_completed'] += 1
                    row['native_completed'] += 1
                else:
                    trace['native_failed'] = 1
                    row['native_failed'] += 1
                    trace['native_failure_phase_code'] = 4
            elif phase == 'exception':
                trace['native_failure_phase_code'] = trace['phase_code']
                trace['phase_code'] = 5
                if not trace['native_failed']:
                    trace['native_failed'] = 1
                    row['native_failed'] += 1
            else:raise ValueError('Invalid native diagnostic phase')

    def finish(self, kind, trace, occupancy_ms, deadline_delta_ms,
               waiting_primary, hardcap_exceeded, guard_exceeded, body_failed):
        if not self.enabled or trace is None:return
        now, cpu = self.clock(), self._thread_ns()
        with self.lock:
            row = self.counters[kind]
            trace.update({'optional_end_mono_ns':now,'optional_end_thread_cpu_ns':cpu,
                'optional_wall_ms':(now-trace['optional_start_mono_ns'])/1e6,
                'optional_thread_cpu_ms':(cpu-trace['optional_start_thread_cpu_ns'])/1e6
                    if cpu >= 0 and trace['optional_start_thread_cpu_ns'] >= 0 else -1.,
                'scheduler_occupancy_ms':float(occupancy_ms),'finish_after_guard_ms':float(deadline_delta_ms),
                'waiting_primary':int(waiting_primary),'hardcap_exceeded':int(hardcap_exceeded),
                'guard_exceeded':int(guard_exceeded),'body_failed':int(body_failed)})
            row['optional_finished'] += 1
            row['admitted_without_native'] += int(not trace['native_attempts'])
            for prefix in ('execute','wait'):
                end = 'execute_return' if prefix == 'execute' else 'wait_end'
                a,b = trace[prefix+'_start_mono_ns'],trace[end+'_mono_ns']
                x,y = trace[prefix+'_start_thread_cpu_ns'],trace[end+'_thread_cpu_ns']
                trace[prefix+'_wall_ms'] = (b-a)/1e6 if a and b else -1.
                trace[prefix+'_thread_cpu_ms'] = (y-x)/1e6 if x >= 0 and y >= 0 else -1.
            if hardcap_exceeded or guard_exceeded or trace['native_failed'] or body_failed:
                row['faults'] += 1
                self.evicted_events += int(len(self.events)==self.CAPACITY)
                self.events.append(dict(trace))
            self.active.pop(kind,None)
            self.local.trace = None

    def snapshot(self):
        if not self.enabled:return {'enabled':False}
        with self.lock:
            return {'enabled':True,'schema_version':'aura-optional-diagnostics-1',
                'clock':'monotonic_ns','started_mono_ns':self.started_mono_ns,
                'snapshot_mono_ns':self.clock(),
                'thread_clock_available':callable(self.thread_clock),
                'thread_cpu_scope':'calling thread only; excludes other native/runtime/kernel threads',
                'wall_scope':'optional gate and VART API walls; includes wait/descheduling/GIL; not pure hardware time',
                'numeric_missing_value':-1,'task_codes':dict(TASK_CODES),
                'phase_codes':{'before_native':0,'execute_entered':1,'execute_returned':2,
                    'wait_entered':3,'wait_returned':4,'native_exception':5},
                'event_capacity':self.CAPACITY,'evicted_events':self.evicted_events,
                'diagnostic_errors':self.diagnostic_errors,
                'counters':{key:dict(row) for key,row in self.counters.items()},
                'active_optional':{key:dict(value) for key,value in self.active.items()},
                'fault_events':[dict(event) for event in self.events]}
