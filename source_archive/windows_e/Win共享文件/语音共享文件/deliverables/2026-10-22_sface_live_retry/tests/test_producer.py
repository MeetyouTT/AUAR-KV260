"""Synthetic frames only: independent supply, target cancellation and lifecycle."""
import bootstrap
import copy
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import cv2
import numpy as np
from board.identity.camera_faces import CameraFaceExtractor
from board.identity.live import IdentityService
from board.identity.sface_producer import SFaceProducer, producer_configuration
from board.identity.sface_shadow import SFaceShadow
from board.vision.reference_faces import SFaceCompat
from test_shadow import configuration, Embedder, wait_for


class ProducerTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration()
        self.config['dpu_sface_shadow']['compare_cosine'] = False
        self.config['dpu_sface_producer'] = {'enabled': True, 'interval_ms': 500}
        self.key = {'camera_epoch': 'epoch', 'track_id': 1, 'track_generation': 1}
        self.now = 1000
        self.lock = threading.RLock()
        self.image = np.zeros((480, 640, 3), np.uint8)
        self.crop = np.zeros((112, 112, 3), np.uint8)
        self.face = (10, 10, 100, 100, 35, 40, 85, 40, 60, 65, 40, 90, 80, 90, .99)

    def make(self, align=None, observer=None, block_embedder=False):
        embedder = Embedder(block=block_embedder)
        shadow = SFaceShadow(self.config, object(), object(), lambda:self.key, clock=lambda:self.now,
            guard_lock=self.lock, embedder_factory=lambda:embedder, result_observer=observer)
        producer = SFaceProducer(self.config, shadow, lambda:self.key, clock=lambda:self.now,
            guard_lock=self.lock, align_crop=align or (lambda *_:self.crop), cv2=cv2)
        self.addCleanup(lambda:shadow.close(.2))
        self.addCleanup(lambda:producer.close(.2))
        self.addCleanup(embedder.release.set)
        shadow.start()
        wait_for(self, lambda:shadow.ready)
        return producer, shadow, embedder

    def offer(self, producer, fid=1, **changes):
        args = dict(image=self.image, face=self.face, fid=fid, stamp=1000, key=copy.deepcopy(self.key))
        args.update(changes)
        return producer.offer_face(**args)

    def test_configuration_default_off_and_rejects_reference_mode(self):
        self.assertIsNone(producer_configuration({}))
        self.assertIsNone(producer_configuration({'dpu_sface_producer':{'enabled':False}}))
        for change in ({'enabled':True,'interval_ms':499}, {'enabled':True,'interval_ms':True},
                       {'enabled':False,'interval_ms':500}):
            cfg = copy.deepcopy(self.config);cfg['dpu_sface_producer'] = change
            with self.assertRaises(ValueError):producer_configuration(cfg)
        cfg = copy.deepcopy(self.config);cfg['dpu_sface_shadow']['compare_cosine'] = True
        with self.assertRaises(ValueError):producer_configuration(cfg)

    def test_callback_does_not_align_copy_or_wait_for_preparation_lock(self):
        producer, _, _ = self.make(align=lambda *_:self.fail('callback aligned'))
        entered, release = threading.Event(), threading.Event()
        def hold():
            with producer.condition:
                entered.set();release.wait(2)
        thread = threading.Thread(target=hold);thread.start();entered.wait(1)
        try:
            start = time.monotonic()
            self.assertFalse(self.offer(producer))
            self.assertLess(time.monotonic()-start, .1)
        finally:
            release.set();thread.join(1)
        self.assertTrue(self.offer(producer))
        self.assertIs(producer.pending[0], self.image)

    def test_latest_only_replaces_and_none_face_cancels(self):
        producer, _, _ = self.make()
        for n in range(1,101):self.assertTrue(self.offer(producer,n))
        self.assertEqual(producer.pending[2],100)
        self.assertEqual(producer.health()['replaced'],99)
        self.assertFalse(self.offer(producer,101,key=None,face=None))
        self.assertIsNone(producer.pending)

    def test_multiface_callback_never_prepares_and_formal_result_clears(self):
        producer, _, _ = self.make(align=lambda *_:self.fail('ambiguous target aligned'))
        service = IdentityService(SimpleNamespace(), lambda:None, lambda:self.key, lock=self.lock)
        service.extractor = SimpleNamespace(producer=producer)
        service.pending = service.result = object()
        service.offer_face(self.image, None, 2, 1000, None)
        self.assertIsNone(service.pending);self.assertIsNone(service.result)
        self.assertIsNone(producer.pending)

    def test_target_generation_and_ttl_rechecked_after_alignment(self):
        for change in ('generation','ttl','cancel_return'):
            with self.subTest(change=change):
                entered, release = threading.Event(), threading.Event()
                def align(*_):
                    entered.set();release.wait(2);return self.crop
                producer, shadow, _ = self.make(align)
                self.assertTrue(self.offer(producer));producer.start();self.assertTrue(entered.wait(1))
                if change == 'generation':self.key['track_generation'] += 1
                elif change == 'ttl':self.now += 500
                else:
                    producer.offer_face(self.image,None,2,1000,None)
                    self.offer(producer,3)
                release.set();wait_for(self,lambda:producer.stale >= 1)
                # Cancel queued replacement before its next 500ms preparation.
                producer.close(.2)
                self.assertEqual(shadow.offered,0)
                self.now = 1000

    def test_expired_or_old_camera_epoch_rejected_before_alignment(self):
        producer, shadow, _ = self.make(align=lambda *_:self.fail('stale aligned'))
        self.assertFalse(self.offer(producer,stamp=500))
        key = dict(self.key,camera_epoch='previous')
        self.assertTrue(self.offer(producer,key=key));producer.start()
        wait_for(self,lambda:producer.stale == 1)
        self.assertEqual(shadow.offered,0)

    def test_quality_pose_reaches_existing_calibration_ticket(self):
        class Observer:
            def __init__(self):self.quality=None;self.accepted=threading.Event()
            def ticket(self, fid, stamp, key, *, quality):self.quality=quality;return 'ticket'
            def observe_target(self,key):pass
            def accept(self,*_):self.accepted.set()
            def close(self):pass
        observer=Observer();producer,shadow,_=self.make(observer=observer)
        producer.start();wait_for(self,lambda:self.offer(producer))
        self.assertTrue(observer.accepted.wait(1))
        self.assertEqual(observer.quality['yaw'],0)
        self.assertEqual(observer.quality['roll'],0)
        self.assertEqual(observer.quality['pixels'],100)
        self.assertEqual(shadow.accepted,1)

    def test_busy_preparation_bounded_and_close_waits_for_inflight(self):
        entered,release=threading.Event(),threading.Event()
        def align(*_):entered.set();release.wait(2);return self.crop
        producer,shadow,_=self.make(align)
        self.assertTrue(self.offer(producer));producer.start();self.assertTrue(entered.wait(1))
        for n in range(2,102):self.assertTrue(self.offer(producer,n))
        self.assertEqual(producer.health()['inflight_frames'],1)
        self.assertEqual(producer.health()['pending_frames'],1)
        self.assertFalse(producer.close(.01))
        self.assertFalse(producer.health()['closed'])
        self.assertIsNone(producer.pending)
        release.set();self.assertTrue(producer.stopped.wait(1))
        self.assertEqual(shadow.offered,0)
        self.assertFalse(self.offer(producer,103))

    def test_preparation_exception_does_not_break_formal_offer(self):
        def bad(*_):raise RuntimeError('synthetic')
        producer,_,_=self.make(bad);producer.start()
        service=IdentityService(SimpleNamespace(),lambda:None,lambda:self.key,lock=self.lock)
        service.extractor=SimpleNamespace(producer=producer)
        def delivered():
            service.offer_face(self.image,self.face,1,1000,self.key)
            return producer.enqueued >= 1
        wait_for(self,delivered)
        wait_for(self,lambda:producer.failures == 1)
        self.assertEqual(service.pending[1],1)
        self.assertEqual(service.reason,'')

    def test_windows_blocking_supply_advances_without_duplicate_extractor_offer(self):
        embedder=Embedder();entered,release=threading.Event(),threading.Event()
        def remote(*_):entered.set();release.wait(3);raise TimeoutError('synthetic windows timeout')
        remote_module=SimpleNamespace(RemoteFaceFeatures=lambda _:SimpleNamespace(feature=remote))
        with patch.dict(sys.modules,{'board.identity.remote_features':remote_module}), \
             patch.object(SFaceShadow,'_make_embedder',lambda _:embedder), \
             patch.object(SFaceCompat,'align_crop',lambda *_:self.crop):
            extractor=CameraFaceExtractor(self.config,face_targets=True,schedule=object(),owner=object(),
                current_target=lambda:self.key,clock=lambda:self.now,guard_lock=self.lock)
            extractor.remote.feature=remote
            store=SimpleNamespace(revision=1,dimension=128,close=lambda:None)
            service=IdentityService(store,lambda:extractor,lambda:self.key,lock=self.lock,clock=lambda:self.now)
            service.start()
            try:
                wait_for(self,lambda:service.ready and extractor.shadow.ready)
                service.offer_face(self.image,self.face,1,1000,self.key)
                self.assertTrue(entered.wait(1))
                wait_for(self,lambda:extractor.producer.submitted >= 1)
                for fid in (2,3):
                    time.sleep(.51)
                    service.offer_face(self.image,self.face,fid,1000,self.key)
                    wait_for(self,lambda:extractor.producer.submitted >= fid)
                self.assertEqual(extractor.shadow.offered,3)
                self.assertEqual(service.processed,0)
                self.assertEqual(service.interval,500)
                release.set();wait_for(self,lambda:service.processed >= 1)
                self.assertIn('synthetic windows timeout',service.reason)
                self.assertEqual(extractor.shadow.offered,3)
            finally:
                release.set();service.close()
            self.assertTrue(extractor.shutdown_ready())
            self.assertTrue(embedder.closed.is_set())


if __name__ == '__main__':unittest.main()
