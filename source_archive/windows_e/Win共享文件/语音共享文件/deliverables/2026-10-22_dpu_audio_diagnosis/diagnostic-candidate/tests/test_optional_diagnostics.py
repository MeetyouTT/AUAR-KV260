"""Synthetic clocks/native calls; no DPU, real frames, logs or audio devices."""
import board.vision
board.vision.__path__.insert(0,'/implementation/candidate/aura/board/vision')
import json
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from board.vision.pipeline_metrics import OptionalDiagnostics,PipelineMetrics
from board.vision.dpu_vision_schedule import DpuVisionSchedule
from board.vision.dpu_vision_runtime import PinnedRunner
from board.vision.ui_camera_service import CameraState


class Clock:
    def __init__(self):self.wall=1000000000;self.cpu=100000000
    def advance(self,wall_ms,cpu_ms):self.wall+=int(wall_ms*1e6);self.cpu+=int(cpu_ms*1e6)


class OptionalDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.clock=Clock()
        self.diag=OptionalDiagnostics(enabled=True,clock_ns=lambda:self.clock.wall,
                                      thread_clock_ns=lambda:self.clock.cpu)
        self.schedule=DpuVisionSchedule(clock=lambda:self.clock.wall/1e9,diagnostics=self.diag)
        self.schedule.next_primary=1.100

    def native(self):
        self.diag.native_mark('sface','execute_start')
        self.clock.advance(1,.5)
        self.diag.native_mark('sface','execute_return')
        self.diag.native_mark('sface','wait_start')
        self.clock.advance(34,.2)
        self.diag.native_mark('sface','wait_end',0)

    def test_default_disabled_has_no_clock_or_event_work(self):
        diag=OptionalDiagnostics(clock_ns=lambda: (_ for _ in ()).throw(AssertionError('clock used')))
        self.assertIsNone(diag.begin('unknown',True,'deadline',20,1))
        self.assertEqual(diag.snapshot(),{'enabled':False})
        self.assertEqual(PipelineMetrics().snapshot(),{'enabled':False})

    def test_overrun_event_separates_vart_wall_and_calling_thread_cpu(self):
        with self.schedule.optional('sface') as admitted:
            self.assertTrue(admitted)
            self.native()
        health=self.schedule.health()
        self.assertTrue(health['optional']['sface']['disabled'])
        event=health['optional_diagnostics']['fault_events'][0]
        self.assertEqual(event['optional_wall_ms'],35.)
        self.assertAlmostEqual(event['optional_thread_cpu_ms'],.7)
        self.assertEqual(event['execute_wall_ms'],1.)
        self.assertEqual(event['wait_wall_ms'],34.)
        self.assertEqual(event['native_completed'],1)
        self.assertEqual(event['hardcap_exceeded'],1)
        self.assertEqual(event['guard_exceeded'],0)
        self.assertTrue(all(type(v) in (int,float) for v in event.values()))

    def test_admission_is_not_native_completion_and_reasons_are_distinct(self):
        with self.schedule.optional('sface') as admitted:self.assertTrue(admitted)
        self.schedule.jobs['sface']['disabled']=True
        with self.schedule.optional('sface') as admitted:self.assertFalse(admitted)
        self.schedule.jobs['sface']['disabled']=False
        self.schedule.active='yolo'
        with self.schedule.optional('sface') as admitted:self.assertFalse(admitted)
        self.schedule.active=None;self.schedule.waiting_primary=1
        with self.schedule.optional('sface') as admitted:self.assertFalse(admitted)
        self.schedule.waiting_primary=0;self.schedule.next_primary=1.001
        with self.schedule.optional('sface') as admitted:self.assertFalse(admitted)
        row=self.diag.snapshot()['counters']['sface']
        self.assertEqual(row['requests'],5)
        self.assertEqual(row['admitted'],1)
        self.assertEqual(row['admitted_without_native'],1)
        self.assertEqual(row['native_completed'],0)
        self.assertEqual([row['rejected_'+v] for v in ('disabled','active','primary_waiting','deadline')],[1]*4)

    def test_original_guard_protection_stays_separate_from_30ms_cap(self):
        self.schedule.next_primary=1.026
        with self.schedule.optional('yunet') as admitted:
            self.assertTrue(admitted)
            self.clock.advance(22,1)
        event=self.diag.snapshot()['fault_events'][0]
        self.assertEqual(event['hardcap_exceeded'],0)
        self.assertEqual(event['guard_exceeded'],1)
        self.assertTrue(self.schedule.disabled('yunet'))

    def test_exact_30ms_is_not_relaxed_and_estimate_miss_is_not_fault(self):
        with self.schedule.optional('yunet') as admitted:
            self.assertTrue(admitted)
            self.clock.advance(25,1)
        self.assertFalse(self.schedule.disabled('yunet'))
        self.assertEqual(self.schedule.health()['optional']['yunet']['budget_exceeded'],1)
        self.assertEqual(self.diag.snapshot()['fault_events'],[])
        self.schedule.next_primary=1.200
        with self.schedule.optional('yunet') as admitted:
            self.assertTrue(admitted)
            self.clock.advance(31,1)
        self.assertTrue(self.schedule.disabled('yunet'))

    def test_fault_ring_is_bounded_and_snapshots_do_not_mutate(self):
        for _ in range(12):
            self.schedule.next_primary=self.clock.wall/1e9+.100
            self.schedule.jobs.pop('sface',None)
            with self.schedule.optional('sface') as admitted:
                self.assertTrue(admitted)
                self.native()
        data=self.diag.snapshot()
        self.assertEqual(len(data['fault_events']),8)
        self.assertEqual(data['evicted_events'],4)
        self.assertEqual(data['fault_events'][0]['event_sequence'],5)
        data['fault_events'][0]['native_completed']=999
        self.assertEqual(self.diag.snapshot()['fault_events'][0]['native_completed'],1)

    def test_active_native_wait_can_be_observed_without_claiming_preemption(self):
        with self.schedule.optional('sface') as admitted:
            self.assertTrue(admitted)
            self.diag.native_mark('sface','execute_start')
            self.diag.native_mark('sface','execute_return')
            self.diag.native_mark('sface','wait_start')
            data=self.diag.snapshot()
            self.assertEqual(data['active_optional']['sface']['phase_code'],3)
            self.assertEqual(data['counters']['sface']['native_completed'],0)
            self.assertEqual(data['fault_events'],[])
            self.diag.native_mark('sface','wait_end',0)
        self.assertEqual(self.diag.snapshot()['active_optional'],{})

    def test_other_thread_mark_cannot_attach_to_calling_thread_trace(self):
        with self.schedule.optional('sface') as admitted:
            self.assertTrue(admitted)
            thread=threading.Thread(target=lambda:self.diag.native_mark('sface','execute_start'))
            thread.start();thread.join(1)
        self.assertEqual(self.diag.snapshot()['counters']['sface']['native_attempts'],0)

    def test_missing_thread_clock_is_explicit_and_not_process_cpu(self):
        diag=OptionalDiagnostics(enabled=True,clock_ns=lambda:self.clock.wall,thread_clock_ns=None)
        token=diag.begin('sface',True,'deadline',20,1.1)
        self.clock.advance(35,1)
        diag.finish('sface',token,35,-60,0,True,False,False)
        event=diag.snapshot()['fault_events'][0]
        self.assertEqual(event['optional_thread_cpu_ms'],-1.)
        self.assertFalse(diag.snapshot()['thread_clock_available'])

    def test_ui_env_explicitly_enables_same_metrics_diagnostics(self):
        with patch.dict('os.environ',{'AURA_PIPELINE_METRICS':'0','AURA_DPU_DIAGNOSTICS':'1'}):
            self.assertFalse(CameraState('boot').pipeline_metrics.optional_diagnostics.enabled)
        with patch.dict('os.environ',{'AURA_PIPELINE_METRICS':'1','AURA_DPU_DIAGNOSTICS':'0'}):
            self.assertFalse(CameraState('boot').pipeline_metrics.optional_diagnostics.enabled)
        with patch.dict('os.environ',{'AURA_PIPELINE_METRICS':'1','AURA_DPU_DIAGNOSTICS':'1'}):
            metrics=CameraState('boot').pipeline_metrics
            self.assertTrue(metrics.optional_diagnostics.enabled)
            self.assertEqual(metrics.snapshot()['optional_diagnostics']['schema_version'],'aura-optional-diagnostics-1')

    def runner(self,*,status=0,where=None):
        test=self
        class Output:
            dims=[1,128];name='features'
            def get_attr(self,name):return 5
        class Native:
            def execute_async(self,inputs,outputs):
                test.clock.advance(1,.5)
                if where=='execute':raise RuntimeError('synthetic execute failure')
                outputs[0].fill(16)
                return 1
            def wait(self,job):
                test.clock.advance(34,.2)
                if where=='wait':raise RuntimeError('synthetic wait failure')
                return status
        runner=PinnedRunner.__new__(PinnedRunner)
        runner.owner=SimpleNamespace(ownership=SimpleNamespace(fileno=lambda:10))
        runner.runner=Native();runner.inputs=[SimpleNamespace(dims=[1,112,112,3])]
        runner.outputs=[Output()];runner.metrics=PipelineMetrics(enabled=True)
        runner.metrics.optional_diagnostics=self.diag
        runner.stage_kind='sface';runner.last_ms=None
        return runner

    def test_runtime_actual_markers_and_completed_count_survive_overrun(self):
        runner=self.runner()
        result=runner.execute_encoded(np.zeros((1,112,112,3),np.int8),slot=self.schedule.optional('sface'))
        np.testing.assert_array_equal(result['features'],np.full((1,128),.5,np.float32))
        data=self.diag.snapshot()
        self.assertEqual(data['counters']['sface']['native_attempts'],1)
        self.assertEqual(data['counters']['sface']['native_completed'],1)
        self.assertEqual(data['fault_events'][0]['wait_wall_ms'],34.)
        self.assertEqual(self.schedule.health()['optional']['sface']['overruns'],1)

    def test_native_error_marks_failure_without_fabricating_completed(self):
        for where,status,expected_attempts in [('execute',0,1),('wait',0,1),(None,7,1)]:
            self.setUp()
            runner=self.runner(status=status,where=where)
            with self.assertRaises(RuntimeError):
                runner.execute_encoded(np.zeros((1,112,112,3),np.int8),slot=self.schedule.optional('sface'))
            data=self.diag.snapshot()
            self.assertEqual(data['counters']['sface']['native_attempts'],expected_attempts)
            self.assertEqual(data['counters']['sface']['native_completed'],0)
            self.assertEqual(data['counters']['sface']['native_failed'],1)
            self.assertEqual(len(data['fault_events']),1)
            self.assertIsNone(self.schedule.active)

    def test_denied_runtime_never_calls_native_or_records_fault(self):
        runner=self.runner()
        self.schedule.next_primary=1.001
        self.assertIsNone(runner.execute_encoded(np.zeros((1,112,112,3),np.int8),slot=self.schedule.optional('sface')))
        row=self.diag.snapshot()['counters']['sface']
        self.assertEqual(row['rejected'],1)
        self.assertEqual(row['native_attempts'],0)
        self.assertEqual(self.diag.snapshot()['fault_events'],[])

    def test_diagnostic_failure_does_not_mask_original_native_error(self):
        runner=self.runner(where='wait')
        self.diag.native_mark=lambda *_:(_ for _ in ()).throw(ValueError('synthetic instrumentation fault'))
        with self.assertRaisesRegex(RuntimeError,'synthetic wait failure'):
            runner.execute_encoded(np.zeros((1,112,112,3),np.int8),slot=self.schedule.optional('sface'))
        self.assertIsNone(self.schedule.active)
        self.assertGreater(self.diag.snapshot()['diagnostic_errors'],0)


if __name__=='__main__':unittest.main(verbosity=2)
