"""Controlled clocks and real diagnostic/scheduler code; no board/media/DB."""
import threading
import unittest
from unittest.mock import patch

import board.vision
board.vision.__path__.insert(0,'/implementation/candidate/aura/board/vision')
from board.vision.pipeline_metrics import OptionalDiagnostics
from board.vision.dpu_vision_schedule import DpuVisionSchedule


class NormalTimingTests(unittest.TestCase):
    def setUp(self):
        self.wall=1_000_000_000
        self.cpu=10_000_000
        self.diag=OptionalDiagnostics(enabled=True,clock_ns=lambda:self.wall,
                                      thread_clock_ns=lambda:self.cpu)
        self.schedule=DpuVisionSchedule(clock=lambda:self.wall/1e9,diagnostics=self.diag)

    def advance(self,wall,cpu):
        self.wall+=int(wall*1e6);self.cpu+=int(cpu*1e6)

    def run_job(self,kind='yunet',execute=1,wait=4,status=0,fail=False):
        self.schedule.next_primary=self.wall/1e9+.100
        with self.schedule.optional(kind) as admitted:
            self.assertTrue(admitted)
            self.diag.native_mark(kind,'execute_start')
            self.advance(execute,.5)
            self.diag.native_mark(kind,'execute_return')
            self.diag.native_mark(kind,'wait_start')
            self.advance(wait,.25)
            self.diag.native_mark(kind,'wait_end',status)
            self.advance(1,.125)
            if fail:raise RuntimeError('original body failure')

    def test_normal_success_exact_aggregates_and_no_fault(self):
        self.run_job(execute=1,wait=4)
        self.run_job(execute=3,wait=6)
        data=self.diag.snapshot();rows=data['normal_success_timings']['yunet']
        for key,total,lo,hi in [('execute_wall_ms',4,1,3),('wait_wall_ms',10,4,6),
                ('optional_wall_ms',16,6,10),('execute_thread_cpu_ms',1,.5,.5),
                ('wait_thread_cpu_ms',.5,.25,.25),('optional_thread_cpu_ms',1.75,.875,.875)]:
            self.assertEqual(rows[key],{'count':2,'sum_ms':total,'min_ms':lo,'max_ms':hi})
        self.assertEqual(data['fault_events'],[])
        self.assertEqual(data['counters']['yunet']['native_completed'],2)

    def test_per_model_statistics_and_one_global_maximum_trace(self):
        self.run_job('yunet',wait=6)
        self.run_job('sface',wait=9)
        self.run_job('yunet',wait=1)
        data=self.diag.snapshot()
        self.assertEqual(data['normal_success_timings']['yunet']['optional_wall_ms']['count'],2)
        self.assertEqual(data['normal_success_timings']['sface']['optional_wall_ms']['count'],1)
        trace=data['maximum_normal_trace']
        self.assertEqual(trace['task_code'],2)
        self.assertEqual(trace['optional_wall_ms'],11)
        native_id=getattr(threading,'get_native_id',lambda:-1)
        self.assertEqual(trace['calling_thread_native_id'],native_id())
        self.assertTrue(all(type(v) in (int,float) for v in trace.values()))
        data['normal_success_timings']['yunet']['optional_wall_ms']['count']=999
        trace['task_code']=999
        fresh=self.diag.snapshot()
        self.assertEqual(fresh['maximum_normal_trace']['task_code'],2)
        self.assertEqual(fresh['normal_success_timings']['yunet']['optional_wall_ms']['count'],2)

    def test_failed_or_overrun_or_no_native_calls_are_excluded(self):
        self.run_job(status=7)
        with self.assertRaisesRegex(RuntimeError,'original body failure'):self.run_job(fail=True)
        self.schedule.next_primary=self.wall/1e9+.1
        with self.schedule.optional('yunet') as admitted:self.assertTrue(admitted)
        self.run_job(wait=31)
        with self.schedule.optional('yunet') as admitted:self.assertFalse(admitted)
        data=self.diag.snapshot()
        self.assertEqual(data['normal_success_timings'],{})
        self.assertIsNone(data['maximum_normal_trace'])
        self.assertEqual(len(data['fault_events']),3)
        self.assertEqual(data['counters']['yunet']['native_failed'],1)
        self.assertEqual(data['counters']['yunet']['native_completed'],2)
        self.assertTrue(self.schedule.disabled('yunet'))

    def test_unavailable_cpu_and_native_id_are_not_false_samples(self):
        self.diag.thread_clock=None
        with patch.object(threading,'get_native_id',None,create=True):self.run_job()
        data=self.diag.snapshot()
        for key,row in data['normal_success_timings']['yunet'].items():
            if 'thread_cpu' in key:
                self.assertEqual(row,{'count':0,'sum_ms':0.,'min_ms':None,'max_ms':None})
        self.assertEqual(data['maximum_normal_trace']['calling_thread_native_id'],-1)
        self.assertEqual(data['maximum_normal_trace']['optional_thread_cpu_ms'],-1)

    def test_native_id_exception_does_not_fail_business(self):
        with patch.object(threading,'get_native_id',side_effect=RuntimeError('unavailable'),create=True):
            self.run_job()
        self.assertEqual(self.diag.snapshot()['maximum_normal_trace']['calling_thread_native_id'],-1)

    def test_available_native_id_is_stored_in_success_and_fault(self):
        with patch.object(threading,'get_native_id',return_value=4321,create=True):
            self.run_job()
            self.run_job(wait=31)
        data=self.diag.snapshot()
        self.assertEqual(data['maximum_normal_trace']['calling_thread_native_id'],4321)
        self.assertEqual(data['fault_events'][0]['calling_thread_native_id'],4321)

    def test_completed_native_and_finish_are_counted_once(self):
        token=self.diag.begin('sface',True,'deadline',20,1.1)
        self.diag.native_mark('sface','execute_start')
        self.advance(1,.5);self.diag.native_mark('sface','execute_return')
        self.diag.native_mark('sface','wait_start')
        self.advance(4,.2);self.diag.native_mark('sface','wait_end',0)
        self.diag.native_mark('sface','wait_end',0)
        self.diag.native_mark('sface','exception')
        for _ in range(2):self.diag.finish('sface',token,5,-90,0,False,False,False)
        data=self.diag.snapshot();row=data['counters']['sface']
        self.assertEqual(row['native_completed'],1)
        self.assertEqual(row['native_failed'],0)
        self.assertEqual(row['optional_finished'],1)
        self.assertEqual(data['normal_success_timings']['sface']['wait_wall_ms']['count'],1)

    def test_failed_native_cannot_later_be_counted_completed(self):
        token=self.diag.begin('sface',True,'deadline',20,1.1)
        self.diag.native_mark('sface','execute_start')
        self.diag.native_mark('sface','wait_start')
        self.diag.native_mark('sface','wait_end',7)
        self.diag.native_mark('sface','exception')
        self.diag.native_mark('sface','wait_end',0)
        self.diag.finish('sface',token,5,-90,0,False,False,True)
        data=self.diag.snapshot();row=data['counters']['sface']
        self.assertEqual(row['native_failed'],1)
        self.assertEqual(row['native_completed'],0)
        self.assertEqual(data['normal_success_timings'],{})

    def test_normal_storage_stays_bounded_with_many_successes(self):
        for i in range(1000):self.run_job('yunet' if i%2 else 'sface')
        data=self.diag.snapshot()
        self.assertEqual(len(data['normal_success_timings']),2)
        self.assertTrue(all(len(rows)==6 for rows in data['normal_success_timings'].values()))
        self.assertEqual(data['maximum_normal_trace']['event_sequence'],1)
        self.assertEqual(data['fault_events'],[])

    def test_aggregation_error_cleans_trace_and_does_not_break_success(self):
        with patch.object(self.diag,'_normal_success',side_effect=ValueError('diagnostic fault')):
            self.run_job()
        data=self.diag.snapshot()
        self.assertEqual(data['diagnostic_errors'],1)
        self.assertEqual(data['active_optional'],{})
        self.assertIsNone(self.schedule.active)
        self.run_job()
        self.assertEqual(self.diag.snapshot()['normal_success_timings']['yunet']['wait_wall_ms']['count'],1)


if __name__=='__main__':unittest.main(verbosity=2)
