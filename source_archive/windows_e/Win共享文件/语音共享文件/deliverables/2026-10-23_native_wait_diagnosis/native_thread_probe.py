"""Isolated candidate adapter. Production does not import or select it yet."""
import os
import threading
import time

FIELDS=('tid','snapshot_before_mono_ns','snapshot_before_cpu_ns','runtime_ns',
        'runqueue_ns','timeslices','voluntary','involuntary','snapshot_after_mono_ns',
        'snapshot_after_cpu_ns')

def missing():
    return {**{name:-1 for name in FIELDS},'pid':-1,'sched_available':0,
            'usage_available':0,'read_wall_ns':-1,'read_cpu_ns':-1,'slow_read':0}

class NativeThreadSchedProbe:
    def __init__(self, factory=None, *, max_cpu_ns=500_000, max_wall_ns=2_000_000):
        if factory is None:
            from _aura_schedprobe import Probe
            factory=Probe
        if (not callable(factory) or type(max_cpu_ns) is not int or not 10_000<=max_cpu_ns<=2_000_000
                or type(max_wall_ns) is not int or not 100_000<=max_wall_ns<=5_000_000):
            raise ValueError('Invalid native observer configuration')
        self.factory=factory;self.pid=os.getpid();self.lock=threading.Lock()
        self.readers={};self.closed=self.disabled=False
        self.max_cpu_ns=max_cpu_ns;self.max_wall_ns=max_wall_ns
        self.samples=self.failures=self.slow_reads=0
        self.maximum_cpu_ns=self.maximum_wall_ns=0

    def sample(self):
        started=time.monotonic_ns();cpu=time.thread_time_ns();value=missing();failed=False
        # A user lock held by a vanished parent thread is not reset by fork.
        # Reject BEFORE touching that inherited lock.
        if os.getpid()!=self.pid:
            value['fork_mismatch']=1
            return value
        with self.lock:
            if self.closed or self.disabled:return value
            try:
                if os.getpid()!=self.pid:raise RuntimeError('Observer cannot be inherited across fork')
                key=(self.pid,threading.get_ident(),threading.get_native_id())
                reader=self.readers.get(key)
                if reader is None:
                    if len(self.readers)>=2:raise RuntimeError('Only two optional calling threads are supported')
                    reader=self.factory();self.readers[key]=reader
                raw=reader.sample()
                if len(raw)!=len(FIELDS) or any(type(n) is not int or n<0 for n in raw):
                    raise ValueError('Invalid native observer values')
                value.update(zip(FIELDS,raw));value['pid']=self.pid
                if value['tid']!=key[2]:raise ValueError('Calling thread changed')
                if (value['snapshot_after_mono_ns']<value['snapshot_before_mono_ns'] or
                        value['snapshot_after_cpu_ns']<value['snapshot_before_cpu_ns']):
                    raise ValueError('Invalid native observer clocks')
                value['sched_available']=int(any(value[k] for k in ('runtime_ns','runqueue_ns','timeslices')))
                value['usage_available']=1
            except Exception:
                failed=True;value=missing()
            value['read_wall_ns']=time.monotonic_ns()-started
            value['read_cpu_ns']=time.thread_time_ns()-cpu
            value['slow_read']=int(value['read_wall_ns']>self.max_wall_ns)
            self.samples+=1;self.failures+=int(failed);self.slow_reads+=value['slow_read']
            self.maximum_cpu_ns=max(self.maximum_cpu_ns,value['read_cpu_ns'])
            self.maximum_wall_ns=max(self.maximum_wall_ns,value['read_wall_ns'])
            # Same conservative CPU stop rule as the existing switch observer.
            # A descheduled low-CPU call stays visible and is never subtracted
            # from a scheduler lease. Benchmarks time the ENTIRE call outside.
            if value['read_cpu_ns']>self.max_cpu_ns:self.disabled=True
        return value

    @staticmethod
    def delta(before,after):
        same=(all(type(row.get(key)) is int and row[key]>0 for row in (before,after) for key in ('pid','tid'))
              and before['pid']==after['pid'] and before['tid']==after['tid'])
        out={'probe_same_thread':int(same),'probe_slow_read':int(bool(before.get('slow_read') or after.get('slow_read')))}
        for key,available in (('runtime_ns','sched_available'),('runqueue_ns','sched_available'),
                ('timeslices','sched_available'),('voluntary','usage_available'),('involuntary','usage_available')):
            a,b=before.get(key,-1),after.get(key,-1)
            out['probe_execute_'+key+'_delta']=(b-a if same and before.get(available)==after.get(available)==1
                and type(a) is int and type(b) is int and b>=a>=0 else -1)
        for key in ('read_wall_ns','read_cpu_ns'):
            a,b=before.get(key,-1),after.get(key,-1)
            out['probe_'+key+'_total']=a+b if type(a) is int and type(b) is int and a>=0 and b>=0 else -1
        return out

    def close(self):
        if os.getpid()!=self.pid:
            # The fork child owns a private descriptor table and object copy.
            # Its other parent threads no longer exist; do not wait on their
            # inherited lock. Closing these child references cannot close the
            # parent's descriptors.
            self.closed=True;self.disabled=True
            for reader in self.readers.values():reader.close()
            self.readers.clear()
            return
        with self.lock:
            self.closed=True
            for reader in self.readers.values():reader.close()
            self.readers.clear()

    def snapshot(self):
        if os.getpid()!=self.pid:
            return {'enabled':False,'mode':'NATIVE_SCHEDSTAT_RUSAGE_GIL_HELD',
                    'fork_mismatch':True,'closed':self.closed,
                    'scope':'parent observer cannot describe fork child counters'}
        with self.lock:
            return {'enabled':True,'mode':'NATIVE_SCHEDSTAT_RUSAGE_GIL_HELD','closed':self.closed,
                'disabled_after_cpu_cost':self.disabled,'samples':self.samples,'read_failures':self.failures,
                'readers':len(self.readers),'maximum_cpu_ns':self.maximum_cpu_ns,'maximum_wall_ns':self.maximum_wall_ns,
                'late_wall_samples':self.slow_reads,'cpu_cost_stop_ns':self.max_cpu_ns,
                'scope':'calling thread counters; ordered non-atomic snapshots, not DPU time or GIL attribution',
                'cpu_clock_scope':'CLOCK_THREAD_CPUTIME_ID; schedstat runtime is auxiliary and can lag',
                'timing_scope':'self read timers precede aggregate updates; external benchmark includes complete call',
                'late_scope':'late calls retained; no time subtraction or hard-cap/guard changes'}
