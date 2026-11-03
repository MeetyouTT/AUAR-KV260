"""Independent fault injection: actual scheduler, adapter and pinned runner; fake VART."""
import bootstrap
import copy
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import unittest
import numpy as np

from board.identity.deferred import DeferredIdentity
from board.identity.live import IdentityService
from board.identity.store import IdentityStore
from board.vision.dpu_sface import DpuSFace
from board.vision.dpu_vision_schedule import DpuVisionSchedule
from board.vision.dpu_vision_runtime import PinnedRunner, NativeExecutionError
import test_protection_handoff as handoff_fixtures


class Clock:
    def __init__(self): self.now=1000.
    def __call__(self): return self.now
    def advance(self,x): self.now+=x


class RecoveryIndependentTests(unittest.TestCase):
    def setUp(self):
        self.clock=Clock()
        self.s=DpuVisionSchedule(clock=self.clock,yunet_recovery=True,sface_recovery=True)
        self.s.next_primary=self.clock()+1.
        self.e=DpuSFace.__new__(DpuSFace);self.e.schedule=self.s
        self.e.clock=lambda:int(round(self.clock()*1000));self.e.source_ttl=100
        self.e._closed=False
        for k in ('requests','execution_attempts','completed','features_returned','deferred','slot_denials','expired_after_admission'):
            setattr(self.e,k,0)
        self.native_duration=.004;self.status=0;self.raise_native=False;self.native_calls=0
        self.mark_delay=0.
        r=PinnedRunner.__new__(PinnedRunner)
        r.input_fix=7;r.last_ms=None;r.stage_kind='sface'
        r.inputs=[SimpleNamespace(dims=[1,112,112,3])]
        r.outputs=[SimpleNamespace(name='out',dims=[1,128],get_attr=lambda key:0)]
        r.owner=SimpleNamespace(ownership=SimpleNamespace(fileno=lambda:7))
        r.metrics=SimpleNamespace(optional_diagnostics=None,elapsed=lambda *a:None,value=lambda *a:None)
        def execute(inputs,outputs):
            self.native_calls+=1
            if self.raise_native:raise RuntimeError('fake native failure')
            outputs[0].fill(1);self.clock.advance(self.native_duration);return (7,0)
        r.runner=SimpleNamespace(execute_async=execute,wait=lambda job:self.status)
        def mark(phase,status=None):
            if phase=='execute_start' and self.mark_delay:self.clock.advance(self.mark_delay)
        r._diagnostic_mark=mark
        self.e.runner=r;self.crop=np.zeros((112,112,3),dtype=np.uint8)

    def feature(self,age=0):return self.e.feature(self.crop,source_mono_ms=self.e.clock()-age)
    def phase(self):return self.s.sface_recovery.phase
    def fault(self):
        self.native_duration=.031
        with self.assertRaises(DeferredIdentity):self.feature()
        self.native_duration=.004
        self.assertEqual(self.phase(),'COOLDOWN')
    def cooled(self):
        self.clock.advance(10.01)
        with self.s.primary(self.clock()+1):self.clock.advance(.004)
    def probe(self):
        with self.assertRaises(DeferredIdentity):self.feature()

    def test_three_probes_first_two_defer_and_only_third_returns(self):
        self.fault();self.cooled()
        self.probe();self.assertFalse(self.e.availability()['ready'])
        self.assertEqual(self.s.sface_recovery.probe_successes,1)
        self.probe();self.assertFalse(self.e.availability()['ready'])
        self.assertEqual(self.s.sface_recovery.probe_successes,2)
        result=self.feature()
        self.assertEqual(len(result),128);self.assertTrue(self.e.availability()['ready'])
        self.assertEqual(self.e.features_returned,1)
        self.assertEqual(self.s.sface_recovery.recoveries,1)
        self.assertEqual(self.s.jobs['sface']['overruns'],1)
        self.assertEqual(self.s.sface_recovery.attempts,1)

    def test_guard_only_latches_even_below_hardcap(self):
        self.s.next_primary=self.clock()+.026;self.native_duration=.022
        with self.assertRaises(DeferredIdentity):self.feature()
        self.assertEqual(self.phase(),'LATCHED');self.assertLess(self.s.jobs['sface']['maximum_ms'],30)
        self.cooled();self.assertFalse(self.s.recovery_probe_allowed('sface'))

    def test_both_guard_and_hardcap_latch(self):
        self.s.next_primary=self.clock()+.026;self.native_duration=.031
        with self.assertRaises(DeferredIdentity):self.feature()
        self.assertEqual(self.phase(),'LATCHED')

    def test_status_nonzero_and_exception_fence_owner(self):
        for mode in ('nonzero','exception'):
            with self.subTest(mode=mode):
                self.setUp();self.status=1 if mode=='nonzero' else 0;self.raise_native=mode=='exception'
                with self.assertRaises(NativeExecutionError):self.feature()
                self.assertTrue(self.s.owner_fenced);self.assertEqual(self.phase(),'LATCHED')
                self.assertIsNone(self.s.active);self.assertEqual(self.e.completed,0)

    def test_unknown_completion_cannot_recover(self):
        with self.s.optional('sface') as got:
            self.assertTrue(got);self.clock.advance(.031)
        self.assertEqual(self.phase(),'LATCHED')

    def test_expired_before_entry_does_not_spend_attempt(self):
        self.fault();self.cooled();calls=self.native_calls
        with self.assertRaises(DeferredIdentity):self.feature(age=100)
        self.assertEqual(self.s.sface_recovery.attempts,0);self.assertEqual(self.native_calls,calls)

    def test_expired_after_slot_before_native_does_not_spend_attempt(self):
        self.fault();self.cooled();calls=self.native_calls;self.mark_delay=.002
        with self.assertRaises(DeferredIdentity):self.feature(age=99)
        self.assertEqual(self.s.sface_recovery.attempts,0);self.assertEqual(self.native_calls,calls)
        self.assertEqual(self.phase(),'COOLDOWN');self.assertTrue(self.s.disabled('sface'))

    def test_expired_in_native_is_completion_but_not_success(self):
        self.fault();self.cooled();before=self.e.completed
        with self.assertRaises(DeferredIdentity):self.feature(age=99)
        self.assertEqual(self.s.sface_recovery.attempts,1)
        self.assertEqual(self.s.sface_recovery.probe_successes,0)
        self.assertEqual(self.e.completed,before+1)
        self.assertEqual(self.phase(),'PROBATION');self.assertFalse(self.e.availability()['ready'])

    def test_slot_denial_does_not_spend_attempt(self):
        self.fault();self.cooled();self.s.next_primary=self.clock()+.01
        self.probe();self.assertEqual(self.s.sface_recovery.attempts,0)
        self.assertEqual(self.phase(),'COOLDOWN')

    def test_primary_overrun_in_probation_latches(self):
        self.fault();self.cooled();self.probe()
        with self.s.primary(self.clock()+.001):self.clock.advance(.002)
        self.assertEqual(self.phase(),'LATCHED');self.assertFalse(self.e.availability()['ready'])

    def test_owner_fence_blocks_recovery_without_clearing_it(self):
        self.fault();self.cooled();self.s.owner_fenced=True
        self.probe();self.assertTrue(self.s.owner_fenced)
        self.assertEqual(self.s.sface_recovery.attempts,0)

    def test_yunet_latch_and_budget_unchanged_by_sface_recovery(self):
        self.s.jobs['yunet']={'calls':17,'disabled':True,'overruns':3}
        p=self.s.yunet_recovery;p.phase='LATCHED';p.reason='fixture guard';p.faults=3
        p.attempt_times.append(self.clock()-1);p.attempts=1
        before=copy.deepcopy(p.__dict__);job=copy.deepcopy(self.s.jobs['yunet'])
        self.fault();self.cooled();self.probe();self.probe();self.feature()
        self.assertEqual(p.__dict__,before);self.assertEqual(self.s.jobs['yunet'],job)

    def test_two_failed_probe_rounds_exhaust_budget(self):
        self.fault()
        for _ in range(2):
            self.cooled();self.native_duration=.031
            self.probe();self.native_duration=.004
        self.assertEqual(self.phase(),'LATCHED')
        self.assertEqual(self.s.sface_recovery.attempts,2)
        self.assertEqual(self.s.sface_recovery.faults,3)

    def test_first_two_probes_do_not_publish_match_or_allow_enrollment(self):
        self.fault();self.cooled()
        key={'camera_epoch':'fixture','track_id':1,'track_generation':1}
        store=IdentityStore(':memory:',self.e.model_id,128,.5,.1)
        service=IdentityService(store,None,lambda:key,clock=self.e.clock,multi_frame=True)
        service.ready=True
        extractor=SimpleNamespace(feature_status=self.e.availability,
            extract=lambda image,obs,k:(tuple(float(v) for v in self.e.feature(self.crop,source_mono_ms=obs['captured_mono_ms'])),''))
        service.extractor=extractor
        try:
            for i in range(2):
                stamp=self.e.clock();packet=(None,i,stamp,{'captured_mono_ms':stamp},key)
                service.process(packet,extractor)
                self.assertIsNone(service.result);self.assertEqual(sum(service.match_counts.values()),0)
                self.assertFalse(service.health()['ready'])
                with self.assertRaises(ValueError):service.enroll({'target':key,'display_name':'fake','confirmed':True},'x')
                with self.assertRaises(ValueError):service.sample_start({'target':key},'x')
            stamp=self.e.clock();service.process((None,3,stamp,{'captured_mono_ms':stamp},key),extractor)
            self.assertIsNotNone(service.result);self.assertEqual(sum(service.match_counts.values()),1)
            self.assertTrue(service.health()['ready']);self.assertEqual(service.deferred,2)
        finally:store.close()

    def test_same_thread_slot_completion_proof_required(self):
        with self.assertRaisesRegex(RuntimeError,'own'):self.s.native_completed('sface')


class HandoffIndependentTests(unittest.TestCase):
    # Extend existing synthetic seed fixture, not production state.
    seed=handoff_fixtures.HandoffTests.seed
    restore=handoff_fixtures.HandoffTests.restore
    def test_inherited_features_and_yunet_state_survive_three_native_successes(self):
        import tempfile
        seed=self.seed()
        with tempfile.TemporaryDirectory() as temp:
            s,info=self.restore(temp,seed)
            self.assertEqual(s.inherited_sface_counters,seed['feature_inference'])
            before=copy.deepcopy(s.yunet_recovery.__dict__)
            with s.primary(111.):pass
            for _ in range(3):
                with s.optional('sface') as got:
                    self.assertTrue(got);self.assertTrue(s.native_starting('sface'));s.native_completed('sface')
            self.assertEqual(s.sface_recovery.phase,'RUNNING')
            self.assertEqual(s.jobs['sface']['overruns'],1)
            self.assertEqual(s.yunet_recovery.__dict__,before)
            self.assertTrue(s.jobs['yunet']['disabled'])

