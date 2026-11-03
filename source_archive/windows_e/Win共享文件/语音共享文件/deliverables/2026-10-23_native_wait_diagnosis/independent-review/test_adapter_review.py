"""Host-only factory/lock fault injection for the candidate Python adapter."""
import copy
import importlib.util
import os
from pathlib import Path
import signal
import threading
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('review_adapter',ROOT/'native_thread_probe.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)

class Reader:
    def __init__(self):self.tid=threading.get_native_id();self.calls=self.closed=0;self.raw=None
    def sample(self):
        self.calls+=1
        return self.raw if self.raw is not None else (self.tid,0,0,1,2,3,4,5,10,9)
    def close(self):self.closed+=1

class AdapterReviewTests(unittest.TestCase):
    def make(self):
        readers=[]
        def factory():
            r=Reader();readers.append(r);return r
        return adapter.NativeThreadSchedProbe(factory),readers

    def test_complete_numeric_mapping_and_same_thread_delta(self):
        p,readers=self.make();a=p.sample();b=p.sample()
        self.assertEqual(a['pid'],os.getpid());self.assertEqual(a['tid'],threading.get_native_id())
        self.assertEqual((a['runqueue_ns'],a['timeslices']),(2,3))
        d=p.delta(a,b);self.assertEqual(d['probe_same_thread'],1)
        self.assertEqual(d['probe_execute_runqueue_ns_delta'],0);p.close()

    def test_all_zero_schedstat_is_unavailable_not_zero_queue_delay(self):
        p,readers=self.make();p.sample();readers[0].raw=(threading.get_native_id(),0,0,0,0,0,0,0,10,9)
        a=p.sample();b=p.sample()
        self.assertEqual(a['sched_available'],0);self.assertEqual(a['usage_available'],1)
        self.assertEqual(p.delta(a,b)['probe_execute_runqueue_ns_delta'],-1);p.close()

    def test_invalid_native_shape_or_tid_stays_missing_without_changing_inference(self):
        p,readers=self.make();p.sample()
        for raw in ((1,2),(-1,0,0,1,2,3,4,5,10,9),(threading.get_native_id()+1000,0,0,1,2,3,4,5,10,9)):
            readers[0].raw=raw;row=p.sample()
            self.assertEqual(row['tid'],-1);self.assertEqual(row['sched_available'],0)
        self.assertEqual(p.snapshot()['read_failures'],3);p.close()

    def test_cpu_cost_disables_later_reads_but_late_low_cpu_wall_does_not(self):
        p,readers=self.make()
        with patch.object(adapter.time,'monotonic_ns',side_effect=[0,1_000_000]),patch.object(adapter.time,'thread_time_ns',side_effect=[0,600_000]):
            row=p.sample()
        self.assertTrue(p.disabled);self.assertEqual(row['read_cpu_ns'],600_000)
        self.assertEqual(p.sample()['tid'],-1);self.assertEqual(readers[0].calls,1);p.close()
        q,readers=self.make()
        with patch.object(adapter.time,'monotonic_ns',side_effect=[0,3_000_000]),patch.object(adapter.time,'thread_time_ns',side_effect=[0,1000]):
            row=q.sample()
        self.assertEqual(row['slow_read'],1);self.assertFalse(q.disabled);q.close()

    def test_two_thread_reader_budget_and_cleanup_are_bounded(self):
        p,readers=self.make();p.sample();results=[]
        for _ in range(2):
            t=threading.Thread(target=lambda:results.append(p.sample()));t.start();t.join(2)
            self.assertFalse(t.is_alive())
        self.assertEqual(len(readers),2);self.assertEqual(sum(r['tid']<0 for r in results),1)
        p.close();p.close();self.assertTrue(all(r.closed==1 for r in readers));self.assertEqual(p.sample()['tid'],-1)

    def test_delta_rejects_cross_pid_tid_and_counter_decrease(self):
        p,_=self.make();a=p.sample()
        for key in ('pid','tid'):
            b=dict(a);b[key]+=1;d=p.delta(a,b)
            self.assertEqual(d['probe_same_thread'],0);self.assertEqual(d['probe_execute_runqueue_ns_delta'],-1)
        b=dict(a);b['runqueue_ns']-=1
        self.assertEqual(p.delta(a,b)['probe_execute_runqueue_ns_delta'],-1);p.close()

    @unittest.skipUnless(hasattr(os,'fork'),'Linux inherited-lock test')
    def test_fork_with_foreign_parent_lock_cannot_hang_sample_snapshot_or_close(self):
        p,_=self.make();p.sample();ready=threading.Event();release=threading.Event()
        def owner():
            with p.lock:ready.set();release.wait(3)
        t=threading.Thread(target=owner);t.start();self.assertTrue(ready.wait(2))
        child=os.fork()
        if child==0:
            signal.alarm(1)
            try:
                row=p.sample();assert row['tid']==-1 and row.get('fork_mismatch')==1
                state=p.snapshot();assert state.get('fork_mismatch') and state.get('enabled') is False
                p.close();assert p.closed;os._exit(0)
            except BaseException:os._exit(1)
        release.set();t.join(2);_,status=os.waitpid(child,0)
        self.assertEqual(status,0,'Fork child blocked on inherited lock or failed bounded rejection')
        self.assertEqual(p.sample()['tid'],threading.get_native_id())
        p.close()

if __name__=='__main__':unittest.main(verbosity=2)
