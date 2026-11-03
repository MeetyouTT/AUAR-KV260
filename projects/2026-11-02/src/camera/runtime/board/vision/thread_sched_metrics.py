"""Calling-thread scheduler counters, opt-in and read-only. No device owners.

Linux 5.15 proc schedstat exposes sum_exec_runtime, sched_info.run_delay,
sched_info.pcount; all-zero output means sched_info may be disabled. Counters
bracket execute with small observer boundaries, not the pure hardware interval.
"""
import threading
import time
import os
try:
    import resource
except ImportError:
    resource=None


SAMPLE_FIELDS=('tid','runtime_ns','runqueue_ns','timeslices','voluntary','involuntary',
               'sched_available','usage_available','read_wall_ns','slow_read')


def missing_sample():
    return {name:0 if name in ('sched_available','usage_available','slow_read') else -1
            for name in SAMPLE_FIELDS}


def read_schedstat():
    with open('/proc/thread-self/schedstat','rb',buffering=0) as stream:raw=stream.read(257)
    return parse_schedstat(raw)


def parse_schedstat(raw):
    if len(raw)>256:raise ValueError('Oversized calling-thread schedstat')
    fields=raw.split()
    if len(fields)!=3 or not all(value.isdigit() for value in fields):
        raise ValueError('Invalid calling-thread schedstat')
    values=tuple(int(value) for value in fields)
    if any(value>=2**64 for value in values):raise ValueError('Invalid scheduler counter range')
    return values


class CallingThreadSchedReader:
    """At most two read-only descriptors, each bound to its creating thread."""
    def __init__(self):
        self.lock=threading.Lock();self.fds={};self.closed=False

    def __call__(self):
        tid=threading.get_native_id();key=(os.getpid(),threading.get_ident(),tid)
        with self.lock:
            if self.closed:raise RuntimeError('Thread counter reader closed')
            if key not in self.fds:
                if len(self.fds)>=2:raise RuntimeError('Only the two optional task threads may be observed')
                self.fds[key]=os.open('/proc/thread-self/schedstat',os.O_RDONLY|os.O_CLOEXEC)
            raw=os.pread(self.fds[key],257,0)
        return parse_schedstat(raw)

    def close(self):
        with self.lock:
            self.closed=True
            for fd in self.fds.values():os.close(fd)
            self.fds.clear()


def read_switches():
    if resource is None:raise RuntimeError('Calling-thread resource counters unavailable')
    usage=resource.getrusage(resource.RUSAGE_THREAD)
    return usage.ru_nvcsw,usage.ru_nivcsw


class ThreadSchedProbe:
    def __init__(self,*,reader=None,usage_reader=read_switches,
                 clock_ns=time.monotonic_ns,tid_reader=None,max_read_ns=2_000_000):
        if ((reader is not None and not callable(reader)) or not callable(usage_reader) or not callable(clock_ns)
                or type(max_read_ns) is not int or not 100_000<=max_read_ns<=5_000_000):
            raise ValueError('Invalid calling-thread observer')
        self.owns_reader=reader is None
        self.reader=CallingThreadSchedReader() if reader is None else reader
        self.usage_reader,self.clock=usage_reader,clock_ns
        self.tid_reader=tid_reader or getattr(threading,'get_native_id',lambda:-1)
        self.max_read_ns=max_read_ns;self.lock=threading.Lock()
        self.samples=self.sched_failures=self.usage_failures=self.slow_reads=0
        self.disabled=self.closed=False;self.maximum_read_ns=0

    def sample(self):
        with self.lock:
            if self.disabled or self.closed:return missing_sample()
        started=self.clock();value=missing_sample();sched_failed=usage_failed=0
        try:
            tid=self.tid_reader()
            if type(tid) is int and tid>0:value['tid']=tid
        except Exception:pass
        try:
            counters=self.reader()
            if (len(counters)!=3 or any(type(v) is not int or not 0<=v<2**64 for v in counters)):
                raise ValueError('Invalid scheduler counters')
            value.update(zip(('runtime_ns','runqueue_ns','timeslices'),counters))
            # Do not interpret Linux's disabled all-zero output as zero delay.
            value['sched_available']=int(any(counters))
        except Exception:sched_failed=1
        try:
            counters=self.usage_reader()
            if len(counters)!=2 or any(type(v) is not int or v<0 for v in counters):
                raise ValueError('Invalid switch counters')
            value.update(zip(('voluntary','involuntary'),counters));value['usage_available']=1
        except Exception:usage_failed=1
        elapsed=self.clock()-started
        value['read_wall_ns']=elapsed if type(elapsed) is int and elapsed>=0 else -1
        value['slow_read']=int(elapsed>self.max_read_ns)
        with self.lock:
            self.samples+=1;self.sched_failures+=sched_failed;self.usage_failures+=usage_failed
            self.maximum_read_ns=max(self.maximum_read_ns,value['read_wall_ns'])
            self.slow_reads+=value['slow_read']
            # One anomalously slow observation disables future reads. Its
            # full cost remains in the original scheduler hard-cap interval.
            if value['slow_read']:self.disabled=True
        if value['slow_read'] and self.owns_reader:self.reader.close()
        return value

    def close(self):
        with self.lock:self.closed=True
        if self.owns_reader:self.reader.close()

    @staticmethod
    def delta(before,after):
        same=(type(before.get('tid')) is int and before['tid']>0 and before['tid']==after.get('tid'))
        result={'probe_same_thread':int(same),
            'probe_read_wall_ns_total':sum(v['read_wall_ns'] for v in (before,after))
                if all(v['read_wall_ns']>=0 for v in (before,after)) else -1,
            'probe_slow_read':int(any(v.get('slow_read') for v in (before,after)))}
        for key,available in (('runtime_ns','sched_available'),('runqueue_ns','sched_available'),
                ('timeslices','sched_available'),('voluntary','usage_available'),('involuntary','usage_available')):
            a,b=before.get(key,-1),after.get(key,-1)
            result['probe_execute_'+key+'_delta']=(b-a if same
                and before.get(available)==after.get(available)==1
                and type(a) is int and type(b) is int and b>=a>=0 else -1)
        return result

    def snapshot(self):
        with self.lock:
            return {'enabled':True,'disabled_after_slow_read':self.disabled,'closed':self.closed,'samples':self.samples,
                'schedstat_read_failures':self.sched_failures,'usage_read_failures':self.usage_failures,
                'slow_reads':self.slow_reads,'maximum_read_ns':self.maximum_read_ns,
                'slow_read_limit_ns':self.max_read_ns,'missing_value':-1,
                'scope':'calling thread; scheduler counter interval surrounds execute wall interval; not DPU busy time',
                'zero_counter_scope':'all-zero schedstat is unavailable, not proof of no scheduling delay',
                'observer_cost_scope':'before/after reads remain inside original optional hard cap; never subtracted'}


class ThreadSwitchProbe:
    """Small getrusage-only fallback. It makes no runqueue-time claim."""
    def __init__(self,*,usage_reader=read_switches,clock_ns=time.monotonic_ns,
                 tid_reader=None,max_read_ns=2_000_000,thread_clock_ns=getattr(time,'thread_time_ns',None),
                 max_cpu_read_ns=500_000):
        self.usage_reader,self.clock=usage_reader,clock_ns
        self.tid_reader=tid_reader or getattr(threading,'get_native_id',lambda:-1)
        self.max_read_ns=max_read_ns;self.samples=self.failures=self.maximum_read_ns=0
        self.thread_clock,self.max_cpu_read_ns=thread_clock_ns,max_cpu_read_ns
        self.maximum_cpu_read_ns=self.wall_late_samples=0
        self.disabled=self.closed=False;self.lock=threading.Lock()

    def sample(self):
        with self.lock:
            if self.closed or self.disabled:
                return {'tid':-1,'voluntary':-1,'involuntary':-1,'read_wall_ns':-1,'read_cpu_ns':-1,'slow_read':0}
        started=self.clock();tid=-1;voluntary=involuntary=-1;failed=0
        try:cpu_started=self.thread_clock() if callable(self.thread_clock) else -1
        except Exception:cpu_started=-1
        try:
            tid=self.tid_reader();values=self.usage_reader()
            if type(tid) is not int or tid<1 or len(values)!=2 or any(type(v) is not int or v<0 for v in values):
                raise ValueError('Invalid calling-thread switch counters')
            voluntary,involuntary=values
        except Exception:tid=-1;failed=1
        elapsed=self.clock()-started
        try:cpu_end=self.thread_clock() if callable(self.thread_clock) else -1
        except Exception:cpu_end=-1
        cpu_elapsed=cpu_end-cpu_started if cpu_end>=cpu_started>=0 else -1
        slow=int(elapsed>self.max_read_ns)
        with self.lock:
            self.samples+=1;self.failures+=failed;self.maximum_read_ns=max(self.maximum_read_ns,elapsed)
            self.maximum_cpu_read_ns=max(self.maximum_cpu_read_ns,cpu_elapsed)
            self.wall_late_samples+=slow
            # A low-CPU wall pause is retained as an observation, not silently
            # counted as observer computation. All wall time still contributes
            # to the unchanged optional hard cap; late samples remain flagged.
            if cpu_elapsed>self.max_cpu_read_ns or (slow and cpu_elapsed<0):self.disabled=True
        return {'tid':tid,'voluntary':voluntary,'involuntary':involuntary,
            'read_wall_ns':elapsed,'read_cpu_ns':cpu_elapsed,'slow_read':slow}

    @staticmethod
    def delta(before,after):
        same=type(before.get('tid')) is int and before['tid']>0 and before['tid']==after.get('tid')
        result={'probe_same_thread':int(same),'probe_slow_read':int(bool(before.get('slow_read') or after.get('slow_read')))}
        for key in ('voluntary','involuntary'):
            a,b=before.get(key,-1),after.get(key,-1)
            result['probe_execute_'+key+'_delta']=b-a if same and type(a) is int and type(b) is int and b>=a>=0 else -1
        a,b=before.get('read_wall_ns',-1),after.get('read_wall_ns',-1)
        result['probe_read_wall_ns_total']=a+b if a>=0 and b>=0 else -1
        a,b=before.get('read_cpu_ns',-1),after.get('read_cpu_ns',-1)
        result['probe_read_cpu_ns_total']=a+b if a>=0 and b>=0 else -1
        return result

    def close(self):
        with self.lock:self.closed=True

    def snapshot(self):
        with self.lock:
            return {'enabled':True,'mode':'CALLING_THREAD_CONTEXT_SWITCHES_ONLY','runqueue_time_collected':False,
                'samples':self.samples,'read_failures':self.failures,'maximum_read_ns':self.maximum_read_ns,
                'maximum_cpu_read_ns':self.maximum_cpu_read_ns,'wall_late_samples':self.wall_late_samples,
                'disabled_after_slow_read':self.disabled,'closed':self.closed,'slow_read_limit_ns':self.max_read_ns,
                'cpu_read_limit_ns':self.max_cpu_read_ns,
                'stop_rule':'CPU read >0.5ms; wall read >2ms if CPU clock missing; low-CPU late wall reads stay flagged',
                'scope':'calling thread switch counts only; cannot time CPU runqueue or identify GIL/native root cause',
                'observer_cost_scope':'original optional hard cap includes all observation work; never subtracted'}
