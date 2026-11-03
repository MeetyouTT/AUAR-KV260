"""Bounded scheduling retries; synthetic crops/vectors, no device or network."""
import bootstrap
from contextlib import contextmanager
import copy
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from board.identity.deferred import DeferredIdentity
from board.identity.sface_shadow import SFaceShadow,shadow_configuration
from board.vision.dpu_sface import DpuSFace
from test_shadow import configuration,vector,wait_for


class Embedder:
    def __init__(self,denials=2,hook=None):
        self.denials=denials;self.hook=hook;self.calls=0;self.pixels=[];self.closed=False
    def feature(self,crop,**kw):
        self.calls+=1;self.pixels.append(int(crop[0,0,0]))
        if self.hook:self.hook(self.calls)
        if self.calls<=self.denials:raise DeferredIdentity('synthetic slot denial',retryable=True)
        return vector()
    def close(self):self.closed=True
    def health(self):return {'calls':self.calls}


class SlotRetryTests(unittest.TestCase):
    def setUp(self):
        self.config=configuration();self.config['dpu_sface_shadow']['compare_cosine']=False
        self.config['dpu_sface_shadow']['slot_retry']={'backoff_ms':50,'max_retries':2}
        self.now=1000;self.key={'camera_epoch':'synthetic','track_id':1,'track_generation':1}
        self.crop=np.ones((112,112,3),np.uint8)
    def start(self,embedder):
        s=SFaceShadow(self.config,object(),object(),lambda:self.key,clock=lambda:self.now,
            guard_lock=threading.RLock(),embedder_factory=lambda:embedder)
        self.addCleanup(lambda:s.close(1));s.start();wait_for(self,lambda:s.ready)
        self.assertTrue(s.offer(self.crop,1,1000,self.key,None));return s

    def test_bounded_denials_then_one_success_without_waiting_whole_interval(self):
        e=Embedder();started=time.monotonic();s=self.start(e)
        wait_for(self,lambda:s.accepted==1,1)
        self.assertLess(time.monotonic()-started,.45)
        self.assertEqual((e.calls,s.retry_scheduled,s.processed),(3,2,1))

    def test_exhaustion_does_not_spin_or_repeat_native_success(self):
        e=Embedder(denials=100);s=self.start(e)
        wait_for(self,lambda:s.retry_exhausted==1)
        self.assertEqual(e.calls,3);time.sleep(.1);self.assertEqual(e.calls,3)

    def test_retry_absent_preserves_original_one_attempt_behavior(self):
        del self.config['dpu_sface_shadow']['slot_retry']
        e=Embedder(denials=100);s=self.start(e)
        wait_for(self,lambda:s.deferred==1);time.sleep(.12)
        self.assertEqual(e.calls,1);self.assertFalse(s.health()['slot_retry']['enabled'])

    def test_expired_source_is_rechecked_before_retry(self):
        e=Embedder(hook=lambda n:setattr(self,'now',1500));s=self.start(e)
        wait_for(self,lambda:s.stale==1)
        self.assertEqual(e.calls,1);self.assertEqual(s.accepted,0)

    def test_target_changed_is_rechecked_before_retry(self):
        e=Embedder(hook=lambda n:setattr(self,'key',dict(self.key,track_generation=2)))
        s=self.start(e);wait_for(self,lambda:s.stale==1)
        self.assertEqual(e.calls,1);self.assertEqual(s.accepted,0)

    def test_newer_pending_crop_wins_over_denied_old_crop(self):
        e=Embedder(denials=1);s=self.start(e)
        # Offer a newer item during the bounded backoff, not another queue.
        wait_for(self,lambda:s.retry_scheduled==1)
        self.assertTrue(s.offer(self.crop*2,2,1000,self.key,None))
        wait_for(self,lambda:s.accepted==1)
        self.assertEqual(e.pixels,[1,2]);self.assertLessEqual(s.health()['pending_frames'],1)

    def test_close_interrupts_backoff_and_clears_pending_crop(self):
        e=Embedder(denials=100);s=self.start(e)
        wait_for(self,lambda:s.retry_scheduled==1)
        self.assertTrue(s.close(1));calls=e.calls;time.sleep(.1)
        self.assertEqual(e.calls,calls);self.assertIsNone(s.pending);self.assertTrue(e.closed)

    def test_unsafe_configuration_rejected(self):
        for retry in ({'backoff_ms':1,'max_retries':2},{'backoff_ms':100,'max_retries':4},
                {'backoff_ms':True,'max_retries':2},{'backoff_ms':25,'max_retries':True},None):
            with self.subTest(retry=retry):
                c=copy.deepcopy(self.config);c['dpu_sface_shadow']['slot_retry']=retry
                with self.assertRaises(ValueError):shadow_configuration(c)
        self.config['dpu_sface_shadow']['compare_cosine']=True
        with self.assertRaises(ValueError):shadow_configuration(self.config)


class NativeAdmissionRetryTests(unittest.TestCase):
    def engine(self,acquired,*,expire=False,disabled=False):
        e=DpuSFace.__new__(DpuSFace);self.now=1000;e.clock=lambda:self.now;e.source_ttl=500
        e.requests=e.execution_attempts=e.completed=e.features_returned=0
        e.deferred=e.slot_denials=e.expired_after_admission=0
        @contextmanager
        def optional(kind):yield acquired
        e.schedule=SimpleNamespace(disabled=lambda kind:disabled,optional=optional)
        def execute(source,slot):
            with slot as got:
                if not got:return None
                if expire:self.now=1500
                return np.ones((1,128),np.float32)
        e.runner=SimpleNamespace(input_fix=7,execute_encoded=execute)
        return e

    def feature(self,e):
        with patch('board.vision.dpu_sface.encode',side_effect=lambda value,fix:value),patch(
                'board.vision.dpu_sface.sface_feature',side_effect=lambda crop,runner,execute:execute(crop)):
            return e.feature(np.zeros((112,112,3),np.uint8),source_mono_ms=1000)

    def test_denied_uncomputed_fresh_packet_is_retryable(self):
        e=self.engine(False)
        with self.assertRaises(DeferredIdentity) as caught:self.feature(e)
        self.assertTrue(caught.exception.retryable);self.assertEqual(e.execution_attempts,0)

    def test_completed_but_expired_native_job_is_not_retryable(self):
        e=self.engine(True,expire=True)
        with self.assertRaises(DeferredIdentity) as caught:self.feature(e)
        self.assertFalse(caught.exception.retryable);self.assertEqual((e.execution_attempts,e.completed),(1,1))

    def test_disabled_task_is_not_retryable(self):
        e=self.engine(False,disabled=True)
        with self.assertRaises(DeferredIdentity) as caught:self.feature(e)
        self.assertFalse(caught.exception.retryable);self.assertEqual(e.execution_attempts,0)


if __name__=='__main__':unittest.main()
