"""Counter semantics and injection failures; no native inference or devices."""
import board.vision
board.vision.__path__.insert(0,'/implementation/candidate/aura/board/vision')
import json
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from board.vision.thread_sched_metrics import ThreadSchedProbe,read_schedstat,CallingThreadSchedReader,ThreadSwitchProbe
from board.vision.pipeline_metrics import OptionalDiagnostics,PipelineMetrics
from board.vision.dpu_vision_schedule import DpuVisionSchedule


class CounterTests(unittest.TestCase):
    def probe(self,reader=lambda:(100,20,3),usage=lambda:(4,5),tid=lambda:7,clock=None):
        return ThreadSchedProbe(reader=reader,usage_reader=usage,tid_reader=tid,clock_ns=clock or (lambda:100))

    def test_counter_delta_matches_calling_thread_and_stays_numeric(self):
        values=iter([(100,20,3),(400,90,5)]);switches=iter([(4,5),(5,8)])
        p=self.probe(reader=lambda:next(values),usage=lambda:next(switches))
        a,b=p.sample(),p.sample();d=p.delta(a,b)
        self.assertEqual(d['probe_execute_runqueue_ns_delta'],70)
        self.assertEqual(d['probe_execute_runtime_ns_delta'],300)
        self.assertEqual(d['probe_execute_voluntary_delta'],1)
        self.assertEqual(d['probe_execute_involuntary_delta'],3)
        self.assertTrue(all(type(x) is int for x in d.values()))

    def test_zero_disabled_or_missing_sched_counters_are_not_zero_wait(self):
        for reader in (lambda:(0,0,0),lambda:(_ for _ in ()).throw(FileNotFoundError('synthetic'))):
            with self.subTest(reader=reader):
                p=self.probe(reader=reader);a,b=p.sample(),p.sample()
                d=p.delta(a,b);self.assertEqual(d['probe_execute_runqueue_ns_delta'],-1)
                self.assertEqual(d['probe_execute_voluntary_delta'],0)

    def test_counter_decrease_and_cross_thread_are_missing(self):
        p=self.probe();a=p.sample();b=p.sample()
        b['runqueue_ns']=0;self.assertEqual(p.delta(a,b)['probe_execute_runqueue_ns_delta'],-1)
        b['tid']=8;self.assertEqual(p.delta(a,b)['probe_same_thread'],0)
        self.assertEqual(p.delta(a,b)['probe_execute_voluntary_delta'],-1)

    def test_failed_usage_does_not_discard_schedstat(self):
        p=self.probe(usage=lambda:(_ for _ in ()).throw(RuntimeError('synthetic')))
        d=p.delta(p.sample(),p.sample())
        self.assertEqual(d['probe_execute_runqueue_ns_delta'],0)
        self.assertEqual(d['probe_execute_voluntary_delta'],-1)
        self.assertEqual(p.snapshot()['usage_read_failures'],2)

    def test_slow_read_latches_future_sampling_off(self):
        t=iter([0,3_000_000]);calls=[]
        p=self.probe(reader=lambda:calls.append(1) or (100,20,3),clock=lambda:next(t))
        a=p.sample();self.assertEqual(a['slow_read'],1)
        b=p.sample();self.assertEqual(b['sched_available'],0)
        self.assertEqual(len(calls),1);self.assertTrue(p.snapshot()['disabled_after_slow_read'])

    def test_malformed_counters_are_isolated(self):
        for values in ((True,1,2),(-1,2,3),(1,2),(2**64,1,1)):
            p=self.probe(reader=lambda:values)
            self.assertEqual(p.sample()['sched_available'],0)
            self.assertEqual(p.snapshot()['schedstat_read_failures'],1)

    def test_reader_bounds_parse_and_closes_descriptor(self):
        class Stream:
            def __init__(self,raw):self.raw=raw;self.closed=False
            def read(self,count):self.count=count;return self.raw
            def __enter__(self):return self
            def __exit__(self,*args):self.closed=True
        for raw in (b'10 20 3\n',b'0 0 0\n',b'a 3 4',b'1 2',b'1 -2 3',b'9'*257):
            stream=Stream(raw)
            with patch('builtins.open',return_value=stream) as opened:
                if raw in (b'10 20 3\n',b'0 0 0\n'):self.assertEqual(len(read_schedstat()),3)
                else:
                    with self.assertRaises(ValueError):read_schedstat()
            self.assertTrue(stream.closed);self.assertEqual(stream.count,257)
            opened.assert_called_once_with('/proc/thread-self/schedstat','rb',buffering=0)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.wall=1_000_000_000;self.cpu=10_000_000;self.counter=0
        def read():self.counter+=1;return (self.counter*100,self.counter*7,self.counter)
        self.probe=ThreadSchedProbe(reader=read,usage_reader=lambda:(1,2),
            tid_reader=lambda:44,clock_ns=lambda:0)
        self.diag=OptionalDiagnostics(enabled=True,clock_ns=lambda:self.wall,
            thread_clock_ns=lambda:self.cpu,thread_probe=self.probe)
        self.schedule=DpuVisionSchedule(clock=lambda:self.wall/1e9,diagnostics=self.diag)

    def job(self,ms=5):
        self.schedule.next_primary=self.wall/1e9+.1
        with self.schedule.optional('yunet') as admitted:
            self.assertTrue(admitted);self.diag.native_mark('yunet','execute_start')
            self.wall+=int(ms*1e6);self.cpu+=500_000
            self.diag.native_mark('yunet','execute_return');self.diag.native_mark('yunet','wait_start')
            self.diag.native_mark('yunet','wait_end',0)

    def test_success_has_two_samples_and_detached_flat_trace(self):
        self.job();s=self.diag.snapshot();t=s['maximum_normal_trace']
        self.assertEqual(t['probe_execute_runqueue_ns_delta'],7)
        self.assertEqual(s['thread_sched_observer']['samples'],2)
        self.assertTrue(all(type(v) in (int,float) for v in t.values()))
        t['probe_execute_runqueue_ns_delta']=999
        self.assertEqual(self.diag.snapshot()['maximum_normal_trace']['probe_execute_runqueue_ns_delta'],7)
        json.dumps(s,allow_nan=False)

    def test_fault_keeps_original_hardcap_and_contains_counter_context(self):
        self.job(33);s=self.diag.snapshot();event=s['fault_events'][0]
        self.assertEqual(event['hardcap_exceeded'],1);self.assertTrue(self.schedule.disabled('yunet'))
        self.assertEqual(event['execute_wall_ms'],33)
        self.assertEqual(event['probe_execute_runqueue_ns_delta'],7)
        self.assertEqual(s['normal_success_timings'],{})

    def test_probe_failure_never_changes_native_outcome(self):
        self.probe.sample=lambda:(_ for _ in ()).throw(RuntimeError('synthetic'))
        self.job();s=self.diag.snapshot()
        self.assertEqual(s['counters']['yunet']['native_completed'],1)
        self.assertEqual(s['diagnostic_errors'],2)
        self.assertFalse(self.schedule.disabled('yunet'))

    def test_reader_is_outside_metrics_lock(self):
        original=self.probe.sample
        def checked():
            self.assertTrue(self.diag.lock.acquire(blocking=False));self.diag.lock.release()
            return original()
        self.probe.sample=checked;self.job()
        self.assertEqual(self.probe.snapshot()['samples'],2)

    def test_disabled_option_does_not_read_proc_or_usage(self):
        with patch.dict('os.environ',{},clear=True),patch(
                'board.vision.thread_sched_metrics.ThreadSchedProbe',side_effect=AssertionError('constructed')):
            m=PipelineMetrics(enabled=True,diagnostics_enabled=True)
        self.assertIsNone(m.optional_diagnostics.thread_probe)
        self.assertEqual(m.optional_diagnostics.snapshot()['thread_sched_observer'],{'enabled':False})

    def test_explicit_flag_requires_existing_diagnostics(self):
        with patch.dict('os.environ',{'AURA_THREAD_SCHED_DIAGNOSTICS':'1'}),patch(
                'board.vision.thread_sched_metrics.ThreadSchedProbe',return_value=self.probe) as factory:
            disabled=PipelineMetrics(enabled=True,diagnostics_enabled=False)
            enabled=PipelineMetrics(enabled=True,diagnostics_enabled=True)
        self.assertIsNone(disabled.optional_diagnostics.thread_probe)
        self.assertIs(enabled.optional_diagnostics.thread_probe,self.probe);factory.assert_called_once()

    def test_two_task_threads_do_not_mix_counter_pairs(self):
        def work(kind):
            token=self.diag.begin(kind,True,'deadline',20,1.1)
            self.diag.native_mark(kind,'execute_start');self.diag.native_mark(kind,'execute_return')
            self.diag.native_mark(kind,'wait_start');self.diag.native_mark(kind,'wait_end',0)
            self.diag.finish(kind,token,1,-90,0,False,False,False)
        threads=[threading.Thread(target=work,args=(kind,)) for kind in ('sface','yunet')]
        for thread in threads:thread.start()
        for thread in threads:thread.join()
        s=self.diag.snapshot();self.assertEqual(s['thread_sched_observer']['samples'],4)
        self.assertEqual(set(s['normal_success_timings']),{'sface','yunet'})


class DescriptorTests(unittest.TestCase):
    def test_descriptor_reused_and_closed_once(self):
        reader=CallingThreadSchedReader()
        with patch('threading.get_native_id',return_value=10,create=True),patch('os.open',return_value=41) as opened,patch('os.pread',return_value=b'10 2 1\n') as read,patch('os.close') as close:
            self.assertEqual(reader(),(10,2,1));self.assertEqual(reader(),(10,2,1))
            self.assertEqual(opened.call_count,1);self.assertEqual(read.call_count,2)
            reader.close();reader.close();close.assert_called_once_with(41)
            with self.assertRaises(RuntimeError):reader()

    def test_different_threads_never_reuse_each_others_fd_and_bound_is_two(self):
        reader=CallingThreadSchedReader()
        with patch('os.open',side_effect=[41,42]) as opened,patch('os.pread',return_value=b'10 2 1\n') as read,patch('os.close') as close,patch(
                'threading.get_native_id',side_effect=[10,20,30],create=True):
            reader();reader()
            with self.assertRaises(RuntimeError):reader()
            self.assertEqual(opened.call_count,2);self.assertEqual([c[0][0] for c in read.call_args_list],[41,42])
            reader.close();self.assertEqual(close.call_count,2)

    def test_metrics_close_releases_probe_and_stops_reads(self):
        probe=ThreadSchedProbe(reader=lambda:(10,2,1),usage_reader=lambda:(0,0))
        metrics=PipelineMetrics(enabled=True,diagnostics_enabled=True)
        metrics.optional_diagnostics.thread_probe=probe;metrics.close()
        self.assertTrue(probe.snapshot()['closed']);self.assertEqual(probe.sample()['sched_available'],0)


class SwitchOnlyTests(unittest.TestCase):
    def test_low_cpu_wall_pause_is_flagged_and_actual_cpu_cost_can_stop_observer(self):
        for cpu_end,disabled in ((40_000,False),(800_000,True),(-1,True)):
            wall=iter([0,3_000_000]);cpu=iter([0,cpu_end])
            probe=ThreadSwitchProbe(usage_reader=lambda:(1,2),tid_reader=lambda:1,
                clock_ns=lambda:next(wall),thread_clock_ns=lambda:next(cpu))
            value=probe.sample();self.assertEqual(value['slow_read'],1)
            self.assertEqual(probe.snapshot()['disabled_after_slow_read'],disabled)
            self.assertEqual(probe.snapshot()['wall_late_samples'],1)

    def test_switch_only_never_opens_proc_or_claims_queue_time(self):
        values=iter([(1,2),(3,5)])
        probe=ThreadSwitchProbe(usage_reader=lambda:next(values),tid_reader=lambda:22,clock_ns=lambda:0)
        with patch('os.open',side_effect=AssertionError('opened')),patch('builtins.open',side_effect=AssertionError('opened')):
            result=probe.delta(probe.sample(),probe.sample())
        self.assertEqual(result['probe_execute_voluntary_delta'],2)
        self.assertEqual(result['probe_execute_involuntary_delta'],3)
        self.assertFalse(any('runqueue' in key for key in result))
        self.assertFalse(probe.snapshot()['runqueue_time_collected'])

    def test_switch_only_failure_or_changed_thread_is_missing(self):
        probe=ThreadSwitchProbe(usage_reader=lambda:(_ for _ in ()).throw(OSError('synthetic')),clock_ns=lambda:0)
        self.assertEqual(probe.delta(probe.sample(),probe.sample())['probe_execute_voluntary_delta'],-1)
        probe.close();self.assertEqual(probe.sample()['tid'],-1)

    def test_switch_mode_is_explicit_and_default_does_no_read(self):
        with patch.dict('os.environ',{'AURA_THREAD_SCHED_DIAGNOSTICS':'switches'}):
            metrics=PipelineMetrics(enabled=True,diagnostics_enabled=True)
        self.assertIsInstance(metrics.optional_diagnostics.thread_probe,ThreadSwitchProbe)
        metrics.close();self.assertTrue(metrics.optional_diagnostics.thread_probe.snapshot()['closed'])


if __name__=='__main__':unittest.main(verbosity=2)
