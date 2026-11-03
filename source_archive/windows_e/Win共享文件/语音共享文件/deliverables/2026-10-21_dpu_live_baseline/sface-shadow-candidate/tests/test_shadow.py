"""Synthetic pixels/vectors and temporary FP32 stores; never hardware/network."""
import bootstrap
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from board.identity.camera_faces import CameraFaceExtractor
from board.identity.deferred import DeferredIdentity
from board.identity.live import IdentityService
from board.identity.model_store import MODEL_SHA256, WINDOWS_MODEL_ID
from board.identity.sface_shadow import SFaceShadow, shadow_configuration
from board.identity.store import IdentityStore


def vector(axis=0):return tuple(1. if n == axis else 0. for n in range(128))


def configuration():
    return {'model_id':WINDOWS_MODEL_ID, 'result_ttl_ms':1500,
        'feature_backend':{'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650},
        'minimum_face_score':.9,'minimum_face_pixels':48,'minimum_blur_variance':0,
        'dpu_sface_shadow':{'enabled':True,'model':'/test/sface.xmodel','manifest':'/test/manifest.json',
            'model_sha256':MODEL_SHA256,'manifest_sha256':'a'*64,'max_source_age_ms':500,
            'interval_ms':500,'compare_cosine':True}}


def wait_for(test, predicate, timeout=2):
    until = time.monotonic()+timeout
    result = predicate()
    while not result and time.monotonic() < until:
        time.sleep(.005)
        result = predicate()
    test.assertTrue(result, 'condition not reached within bounded test wait')


class Embedder:
    def __init__(self, block=False, error=None, value=None):
        self.entered, self.release, self.closed = threading.Event(), threading.Event(), threading.Event()
        if not block:self.release.set()
        self.error = error
        self.value = value or vector()
        self.calls = 0
        self.times = []
        self.last_first_pixel = None
        self.was_readonly = False
    def feature(self, crop, **_):
        self.calls += 1
        self.times.append(time.monotonic())
        self.last_first_pixel = tuple(int(v) for v in crop[0,0])
        self.was_readonly = not crop.flags.writeable
        self.entered.set()
        if not self.release.wait(2):raise RuntimeError('test release timeout')
        if self.error is not None:raise self.error
        return self.value
    def close(self):self.closed.set()
    def health(self):return {'completed':self.calls if self.error is None else 0}


class ShadowTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration()
        self.key = {'camera_epoch':'epoch','track_id':1,'track_generation':1}
        self.now = 1000
        self.crop = np.zeros((112,112,3),np.uint8)
        self.crop[:] = [1,2,3]

    def shadow(self, embedder=None, factory=None):
        embedder = embedder or Embedder()
        service = SFaceShadow(self.config, object(), object(), lambda:self.key, clock=lambda:self.now,
            guard_lock=threading.RLock(), embedder_factory=factory or (lambda:embedder))
        self.addCleanup(lambda:service.close(.1))
        self.addCleanup(embedder.release.set)
        return service, embedder

    def offer(self, service, fid=1):return service.offer(self.crop,fid,1000,copy.deepcopy(self.key),vector())

    def enqueue(self, service, fid=1):wait_for(self,lambda:self.offer(service,fid))

    def test_default_disabled_and_windows_only_contract(self):
        self.assertIsNone(shadow_configuration({}))
        self.assertIsNone(shadow_configuration({'dpu_sface_shadow':{'enabled':False}}))
        for field,value in (('model_id','other'),('feature_backend',{'kind':'dpu_sface'})):
            config = copy.deepcopy(self.config)
            config[field] = value
            with self.assertRaises(ValueError):shadow_configuration(config)
        for field,value in (('interval_ms',100),('max_source_age_ms',1501),('compare_cosine',1)):
            config = copy.deepcopy(self.config)
            config['dpu_sface_shadow'][field] = value
            with self.assertRaises(ValueError):shadow_configuration(config)

    def test_latest_pending_is_bounded_and_copy_is_immutable(self):
        construct_release = threading.Event()
        embedder = Embedder()
        def factory():
            construct_release.wait(2)
            return embedder
        service,_ = self.shadow(embedder, factory)
        service.start()
        self.addCleanup(construct_release.set)
        for fid in range(1,101):self.assertTrue(self.offer(service,fid))
        self.assertEqual(service.health()['pending_frames'],1)
        self.assertEqual(service.health()['replaced'],99)
        self.assertEqual(service.pending['fid'],100)
        self.crop[:] = 255
        construct_release.set()
        wait_for(self,lambda:service.health()['accepted']==1)
        self.assertEqual(embedder.last_first_pixel,(1,2,3))
        self.assertTrue(embedder.was_readonly)
        self.assertEqual(service.health()['same_crop_cosine']['mean'],1.)
        self.assertEqual(service.health()['identity_decisions_from_shadow'],0)
        self.assertEqual(service.health()['templates_written'],0)

    def test_one_inflight_plus_one_pending_and_rate_limit(self):
        service,embedder = self.shadow(Embedder(block=True))
        service.start()
        self.enqueue(service)
        self.assertTrue(embedder.entered.wait(1))
        for fid in range(2,20):self.assertTrue(self.offer(service,fid))
        self.assertEqual(service.health()['pending_frames'],1)
        self.assertEqual(service.health()['inflight_frames'],1)
        embedder.release.set()
        wait_for(self,lambda:service.health()['processed']==2)
        self.assertEqual(embedder.calls,2)
        self.assertGreaterEqual(embedder.times[1]-embedder.times[0],.49)

    def test_stale_or_changed_target_before_execution_is_not_computed(self):
        for kind in ('stale','target'):
            service,embedder = self.shadow()
            self.enqueue(service)
            if kind == 'stale':self.now=1500
            else:self.key['track_generation']=2
            service.start()
            wait_for(self,lambda:service.health()['stale']==1)
            self.assertEqual(embedder.calls,0)
            self.assertEqual(service.health()['accepted'],0)
            self.assertEqual(service.health()['same_crop_cosine']['count'],0)
            service.close()
            self.now=1000
            self.key['track_generation']=1

    def test_stale_or_changed_target_after_execution_publishes_no_metrics(self):
        for kind in ('stale','target'):
            service,embedder = self.shadow(Embedder(block=True))
            service.start()
            self.enqueue(service)
            self.assertTrue(embedder.entered.wait(1))
            if kind == 'stale':self.now=1500
            else:self.key['track_generation']=2
            embedder.release.set()
            wait_for(self,lambda:service.health()['processed']==1)
            health = service.health()
            self.assertEqual(health['execution']['completed'],1)
            self.assertEqual(health['accepted'],0)
            self.assertEqual(health['same_crop_cosine']['count'],0)
            self.assertEqual(health['accepted_latency_ms']['count'],0)
            self.assertEqual(health['stale'],1)
            service.close()
            self.now=1000
            self.key['track_generation']=1

    def test_busy_failure_and_initialization_failure_stay_auxiliary(self):
        for error,counter in ((DeferredIdentity('busy'),'deferred'),(RuntimeError('synthetic'),'failures')):
            service,embedder = self.shadow(Embedder(error=error))
            service.start()
            self.enqueue(service)
            wait_for(self,lambda:service.health()[counter]==1)
            self.assertEqual(service.health()['accepted'],0)
            self.assertEqual(service.health()['same_crop_cosine']['count'],0)
            service.close()
        def fail():raise RuntimeError('synthetic init')
        service,_ = self.shadow(factory=fail)
        service.start()
        self.assertTrue(service.stopped.wait(1))
        self.assertEqual(service.health()['failures'],1)
        self.assertFalse(self.offer(service))

    def test_producer_never_waits_for_shadow_lock(self):
        service,_ = self.shadow()
        held,release = threading.Event(),threading.Event()
        def hold():
            with service.condition:
                held.set()
                release.wait(1)
        thread = threading.Thread(target=hold)
        thread.start()
        self.assertTrue(held.wait(1))
        try:self.assertFalse(self.offer(service))
        finally:
            release.set()
            thread.join(1)
        self.assertEqual(service.health()['producer_dropped'],1)

    def test_close_discards_pending_closes_own_runner_and_preserves_owner(self):
        owner_closed = threading.Event()
        service,embedder = self.shadow(Embedder(block=True))
        service.owner = SimpleNamespace(close=owner_closed.set)
        service.start()
        self.enqueue(service)
        self.assertTrue(embedder.entered.wait(1))
        self.offer(service,2)
        self.assertFalse(service.close(.01))
        self.assertEqual(service.health()['pending_frames'],0)
        self.assertFalse(service.health()['closed'])
        self.assertTrue(service.health()['stop_requested'])
        self.assertFalse(embedder.closed.is_set())
        embedder.release.set()
        self.assertTrue(service.stopped.wait(1))
        self.assertTrue(embedder.closed.is_set())
        self.assertFalse(owner_closed.is_set())
        self.assertEqual(service.health()['accepted'],0)
        self.assertFalse(self.offer(service,3))

    def test_parent_close_reports_incomplete_shutdown_until_worker_has_stopped(self):
        stopped=threading.Event()
        extractor=SimpleNamespace(close=lambda:False,shutdown_ready=stopped.is_set)
        store=IdentityStore(':memory:',WINDOWS_MODEL_ID,128,.9,.1,allow_cross_thread=True)
        parent=IdentityService(store,lambda:extractor,lambda:None)
        parent.start()
        with self.assertRaisesRegex(RuntimeError,'keep the shared DPU owner open'):parent.close()
        self.assertTrue(parent.shutdown_incomplete)
        self.assertEqual(store.revision,0)
        stopped.set()
        parent.close()
        self.assertFalse(parent.shutdown_incomplete)


class PrimaryIsolationTests(unittest.TestCase):
    def setUp(self):
        self.config=configuration()
        self.key={'camera_epoch':'epoch','track_id':1,'track_generation':1}
        self.primary=vector(0)
        self.observation={'target_kind':'face','face_target':self.key,'frame_id':1,'captured_mono_ms':1000,
            'face':[0,0,112,112,38.2946,51.6963,73.5318,51.5014,56.0252,71.7366,
                    41.5493,92.3655,70.7299,92.2041,.99]}
        self.image=np.zeros((112,112,3),np.uint8)
        remote=SimpleNamespace(RemoteFaceFeatures=lambda config:SimpleNamespace(feature=lambda *_:self.primary))
        self.patch=patch.dict('sys.modules',{'board.identity.remote_features':remote})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def extractor(self, embedder):
        with patch.object(SFaceShadow,'_make_embedder',return_value=embedder):
            extractor=CameraFaceExtractor(self.config,face_targets=True,schedule=object(),owner=object(),
                clock=lambda:1000,current_target=lambda:self.key,guard_lock=threading.RLock())
        self.addCleanup(extractor.close)
        self.addCleanup(embedder.release.set)
        wait_for(self,lambda:extractor.shadow.health()['ready'])
        return extractor

    def test_blocked_shadow_cannot_delay_primary_or_change_old_database(self):
        embedder=Embedder(block=True,value=vector(1))
        extractor=self.extractor(embedder)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'windows.sqlite3'
            store=IdentityStore(path,WINDOWS_MODEL_ID,128,.9,.1)
            store.enroll('one','synthetic',self.primary,consent=True)
            original=hashlib.sha256(path.read_bytes()).hexdigest()
            service=IdentityService(store,lambda:extractor,lambda:self.key,clock=lambda:1000,
                backend='WINDOWS_CPU_SFACE_ORT')
            service.ready=True
            try:
                result,reason=extractor.extract(self.image,self.observation,self.key)
                self.assertIs(result,self.primary)
                self.assertEqual(reason,'')
                self.assertTrue(embedder.entered.wait(1))
                self.assertFalse(embedder.release.is_set())
                service.process((self.image,1,1000,self.observation,self.key),extractor)
                self.assertEqual(service.result['match'].state,'KNOWN')
                self.assertEqual(service.result['match'].identity_id,'one')
                self.assertEqual(service.store.model_id,WINDOWS_MODEL_ID)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),original)
                self.assertEqual(store.revision,1)
                # Stopping only the auxiliary worker does not stop identity.
                embedder.release.set()
                self.assertTrue(extractor.shadow.close())
                service.process((self.image,2,1000,self.observation,self.key),extractor)
                self.assertEqual(service.result['match'].state,'KNOWN')
                self.assertEqual(service.result['match'].identity_id,'one')
                self.assertEqual(service.error,'')
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),original)
            finally:
                embedder.release.set()
                extractor.close()
                service.close()
            self.assertEqual([p.name for p in Path(directory).iterdir()],['windows.sqlite3'])

    def test_shadow_failure_and_busy_never_replace_primary_vector(self):
        for error in (RuntimeError('synthetic'),DeferredIdentity('busy')):
            embedder=Embedder(error=error,value=vector(1))
            extractor=self.extractor(embedder)
            result,_=extractor.extract(self.image,self.observation,self.key)
            self.assertIs(result,self.primary)
            wait_for(self,lambda:sum(extractor.shadow.health()[k] for k in ('failures','deferred'))==1)
            result,_=extractor.extract(self.image,self.observation,self.key)
            self.assertIs(result,self.primary)
            extractor.close()

    def test_shadow_offer_health_and_close_exceptions_do_not_escape_primary(self):
        class BrokenShadow:
            def offer(self,*_):raise RuntimeError('synthetic')
            def health(self):raise RuntimeError('synthetic')
            def close(self,**_):raise RuntimeError('synthetic')
        config=copy.deepcopy(self.config)
        config.pop('dpu_sface_shadow')
        extractor=CameraFaceExtractor(config,face_targets=True)
        extractor.shadow=BrokenShadow()
        result,_=extractor.extract(self.image,self.observation,self.key)
        self.assertIs(result,self.primary)
        self.assertEqual(extractor.health()['auxiliary_error'],'RuntimeError')
        extractor.close()

    def test_disabled_shadow_creates_no_thread_or_adapter(self):
        self.config['dpu_sface_shadow']={'enabled':False}
        with patch('board.identity.sface_shadow.SFaceShadow',side_effect=AssertionError('shadow created')):
            extractor=CameraFaceExtractor(self.config,face_targets=True)
        result,_=extractor.extract(self.image,self.observation,self.key)
        self.assertIs(result,self.primary)
        self.assertIsNone(extractor.shadow)
        self.assertIsNone(extractor.health())

    def test_no_cosine_shadow_runs_when_remote_raises_and_preserves_original_exception(self):
        self.config['dpu_sface_shadow']['compare_cosine']=False
        embedder=Embedder(value=vector(1))
        extractor=self.extractor(embedder)
        failure=OSError('synthetic remote unavailable')
        def unavailable(*_):raise failure
        extractor.remote.feature=unavailable
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'windows.sqlite3'
            store=IdentityStore(path,WINDOWS_MODEL_ID,128,.9,.1)
            store.enroll('one','synthetic',self.primary,consent=True)
            original=hashlib.sha256(path.read_bytes()).hexdigest()
            try:
                with self.assertRaises(OSError) as caught:
                    extractor.extract(self.image,self.observation,self.key)
                self.assertIs(caught.exception,failure)
                wait_for(self,lambda:extractor.shadow.health()['accepted']==1)
                health=extractor.shadow.health()
                self.assertEqual(health['offered'],1)
                self.assertEqual(health['enqueued'],1)
                self.assertEqual(health['execution']['completed'],1)
                self.assertEqual(health['accepted_latency_ms']['count'],1)
                self.assertEqual(health['same_crop_cosine']['count'],0)
                self.assertEqual(health['templates_written'],0)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),original)
                self.assertEqual(store.revision,1)
            finally:store.close()
            self.assertEqual([p.name for p in Path(directory).iterdir()],['windows.sqlite3'])

    def test_cosine_shadow_does_not_offer_when_remote_raises(self):
        extractor=self.extractor(Embedder())
        failure=OSError('synthetic remote unavailable')
        def unavailable(*_):raise failure
        extractor.remote.feature=unavailable
        with self.assertRaises(OSError) as caught:
            extractor.extract(self.image,self.observation,self.key)
        self.assertIs(caught.exception,failure)
        self.assertEqual(extractor.shadow.health()['offered'],0)
        self.assertEqual(extractor.shadow.health()['same_crop_cosine']['count'],0)
        self.assertEqual(extractor.shadow.health()['execution']['completed'],0)

    def test_successful_primary_offers_exactly_once_in_either_mode(self):
        for compare in (False,True):
            self.config['dpu_sface_shadow']['compare_cosine']=compare
            extractor=self.extractor(Embedder())
            result,reason=extractor.extract(self.image,self.observation,self.key)
            self.assertIs(result,self.primary)
            self.assertEqual(reason,'')
            wait_for(self,lambda:extractor.shadow.health()['accepted']==1)
            health=extractor.shadow.health()
            self.assertEqual(health['offered'],1)
            self.assertEqual(health['enqueued'],1)
            self.assertEqual(health['same_crop_cosine']['count'],int(compare))
            extractor.close()


if __name__ == '__main__':unittest.main()
