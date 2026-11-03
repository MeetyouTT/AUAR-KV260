import bootstrap
from contextlib import contextmanager
from types import SimpleNamespace
import threading,unittest
from unittest.mock import patch
import numpy as np
from board.identity.deferred import DeferredIdentity
from board.vision.dpu_sface import DpuSFace
from board.vision.dpu_vision_runtime import PinnedRunner,NativeExecutionError
from board.vision.dpu_vision_schedule import DpuVisionSchedule


class SFaceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.now=1000.;self.ms=10000;self.duration=.004;self.status=0;self.native_calls=0
        self.s=DpuVisionSchedule(clock=lambda:self.now,yunet_recovery=True,sface_recovery=True)
        self.s.next_primary=self.now+1
        self.engine=DpuSFace.__new__(DpuSFace);self.engine.schedule=self.s
        self.engine.clock=lambda:self.ms;self.engine.source_ttl=1000;self.engine._closed=False
        for n in ('requests','execution_attempts','completed','features_returned','deferred','slot_denials','expired_after_admission'):
            setattr(self.engine,n,0)
        runner=PinnedRunner.__new__(PinnedRunner);self.engine.runner=runner
        runner.owner=SimpleNamespace(ownership=SimpleNamespace(fileno=lambda:1))
        runner.stage_kind='sface';runner.input_fix=7;runner.last_ms=None
        runner.inputs=[SimpleNamespace(dims=[1,112,112,3])]
        runner.outputs=[SimpleNamespace(dims=[1,128],name='feature',get_attr=lambda k:5)]
        runner.metrics=SimpleNamespace(elapsed=lambda *a:None,value=lambda *a:None,optional_diagnostics=None)
        def execute(inputs,outputs):
            self.native_calls+=1;self.now+=self.duration;outputs[0][:]=1;return 7
        runner.runner=SimpleNamespace(execute_async=execute,wait=lambda job:self.status)
        self.source=np.zeros((1,112,112,3),dtype=np.int8)
        self.encode=patch('board.vision.dpu_sface.encode',lambda value,fix:self.source)
        self.feature=patch('board.vision.dpu_sface.sface_feature',self.decode)
        self.encode.start();self.feature.start()

    def decode(self,crop,runner,execute):
        values=execute(crop)
        return None if values is None else values['feature'][0]

    def tearDown(self):self.encode.stop();self.feature.stop()
    def call(self):return self.engine.feature(None,source_mono_ms=10000)
    def fault(self):
        self.duration=.031
        with self.assertRaises(DeferredIdentity):self.call()
        self.duration=.004
        self.assertEqual(self.s.sface_recovery.phase,'COOLDOWN')
    def primary(self,late=False):
        with self.s.primary(self.now+.1):self.now+=.101 if late else .004
    def cool(self):self.now+=10;self.primary()

    def test_three_real_probes_withhold_first_two_then_return_only_after_running(self):
        self.fault();self.cool()
        for count in (1,2):
            with self.assertRaises(DeferredIdentity):self.call()
            self.assertFalse(self.engine.availability()['ready'])
            self.assertEqual(self.s.sface_recovery.probe_successes,count)
            self.assertEqual(self.engine.features_returned,0)
        vector=self.call();self.assertEqual(len(vector),128)
        self.assertTrue(self.engine.availability()['ready']);self.assertEqual(self.s.sface_recovery.recoveries,1)
        self.assertEqual(self.s.sface_recovery.attempts,1);self.assertEqual(self.s.jobs['sface']['overruns'],1)

    def test_cooldown_uses_no_native_and_preserves_counter(self):
        self.fault();calls=self.native_calls
        with self.assertRaises(DeferredIdentity):self.call()
        self.assertEqual(self.native_calls,calls);self.assertEqual(self.s.sface_recovery.attempts,0)

    def test_guard_only_latches_even_below_thirty_ms(self):
        self.s.next_primary=self.now+.0251;self.duration=.021
        with self.assertRaises(DeferredIdentity):self.call()
        self.assertEqual(self.s.sface_recovery.phase,'LATCHED')
        self.assertLess(self.s.jobs['sface']['maximum_ms'],30)

    def test_nonzero_native_completion_does_not_become_success(self):
        self.fault();self.cool();self.status=1
        with self.assertRaises(NativeExecutionError):self.call()
        self.assertEqual(self.s.sface_recovery.phase,'LATCHED')
        self.assertEqual(self.s.sface_recovery.probe_successes,0)

    def test_expired_before_submission_does_not_spend_recovery_attempt(self):
        self.fault();self.cool();calls=self.native_calls
        def mark(phase,status=None):
            if phase=='execute_start':self.ms=11000
        self.engine.runner._diagnostic_mark=mark
        with self.assertRaises(DeferredIdentity):self.call()
        self.assertEqual(self.native_calls,calls);self.assertEqual(self.s.sface_recovery.attempts,0)
        self.assertEqual(self.s.sface_recovery.phase,'COOLDOWN')

    def test_source_expired_on_completion_is_not_probe_success(self):
        self.fault();self.cool()
        def wait(job):self.ms=11000;return 0
        self.engine.runner.runner.wait=wait
        with self.assertRaises(DeferredIdentity):self.call()
        self.assertEqual(self.s.sface_recovery.attempts,1)
        self.assertEqual(self.s.sface_recovery.probe_successes,0)
        self.assertEqual(self.s.sface_recovery.phase,'PROBATION')

    def test_primary_failure_during_probation_latches(self):
        self.fault();self.cool()
        with self.assertRaises(DeferredIdentity):self.call()
        self.primary(late=True)
        self.assertEqual(self.s.sface_recovery.phase,'LATCHED');self.assertTrue(self.s.disabled('sface'))

    def test_yunet_state_and_budget_are_independent(self):
        self.s.yunet_recovery.phase='LATCHED';self.s.yunet_recovery.faults=2
        self.fault();self.cool()
        with self.assertRaises(DeferredIdentity):self.call()
        self.assertEqual(self.s.yunet_recovery.phase,'LATCHED');self.assertEqual(self.s.yunet_recovery.faults,2)

    def test_recovery_budget_exhausts_without_clearing_faults(self):
        self.fault();self.cool()
        for attempt in (1,2):
            self.duration=.031
            with self.assertRaises(DeferredIdentity):self.call()
            self.assertEqual(self.s.sface_recovery.attempts,attempt)
            if attempt==1:self.cool()
        self.assertEqual(self.s.sface_recovery.phase,'LATCHED')
        self.assertEqual(self.s.sface_recovery.faults,3);self.assertEqual(self.s.jobs['sface']['overruns'],3)

    def test_owner_fence_never_allows_probe(self):
        self.fault();self.cool();self.s.owner_fenced=True
        with self.assertRaises(DeferredIdentity):self.call()
        self.assertEqual(self.native_calls,1);self.assertEqual(self.s.sface_recovery.attempts,0)
