import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(1, '/home/ghmd/aura-native-live-20261024/r4/candidate/aura')
from face_flow import FaceFlow
from face_observation import observation


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.gray = np.zeros((240, 320), np.uint8)
        self.gray[60:150, 100:190] = np.random.RandomState(3).randint(0, 256, (90, 90), dtype=np.uint8)
        self.key = dict(camera_epoch='camera', track_id=1, track_generation=1)
        self.face = SimpleNamespace(lock=threading.RLock(), ready=True, error='', closed=False,
                                    fault_latched=False, count=1, key=dict(self.key), stamp=1000,
                                    ttl=1000, tracker=SimpleNamespace(last_frame=1, tracks={}))
        self.detect(1, 1000)
        self.flow = FaceFlow(self.face, start=False)
        self.face._edge_flow = self.flow
        self.now = 1001
        self.face.clock = lambda: self.now
        self.state = SimpleNamespace(lock=threading.RLock(), identity=SimpleNamespace(face_targets=self.face),
                                     clock=lambda: self.now, boot='boot', epoch='service', camera_epoch='camera',
                                     capture_stamp=1000, camera_error='')

    def detect(self, fid, stamp, *, count=1, key=None, box=None):
        self.face.count, self.face.stamp = count, stamp
        self.face.tracker.last_frame = fid
        self.face.key = dict(key or self.key) if count == 1 else None
        if count == 1:
            self.face.continuity_key = dict(self.face.key)
        elif count > 1:
            self.face.continuity_key = None
        self.face.tracker.tracks = {self.face.key['track_id']: dict(visible=True, confirmed=True,
            frame_id=fid, observed_time=stamp/1000, box=box or [200., 120., 180., 180.], score=.97)} if count == 1 else {}

    @staticmethod
    def image(gray):
        return cv2.cvtColor(cv2.resize(gray, (640, 480), interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)

    def frame(self, fid, stamp, gray=None):
        image = self.image(self.gray if gray is None else gray)
        self.flow.offer(image, fid, stamp)
        value, reason = self.flow.measure(image, fid, stamp, self.flow.detector_snapshot())
        self.flow.value, self.flow.reason = value, reason
        self.state.capture_stamp, self.now = stamp, stamp+1
        return value

    def moved(self, dx=8, dy=-3):
        return cv2.warpAffine(self.gray, np.float32([[1, 0, dx], [0, 1, dy]]), (320, 240))

    def test_translation_measures_new_pixels(self):
        self.frame(1, 1000)
        value = self.frame(2, 1050, self.moved())
        self.assertAlmostEqual(value['box'][0], 216., delta=1.)
        self.assertAlmostEqual(value['box'][1], 114., delta=1.)
        self.assertEqual(value['stamp'], 1050)
        self.assertEqual(observation(self.state)['state'], 'READY')

    def test_detector_miss_does_not_discard_current_pixels(self):
        self.frame(1, 1000)
        self.detect(2, 1100, count=0)
        value = self.frame(3, 1150, self.moved())
        self.assertIsNotNone(value)
        result = observation(self.state)
        self.assertEqual(result['state'], 'READY')
        self.assertTrue(result['detection_miss'])
        self.assertEqual(result['source_frame_id'], 3)
        self.assertEqual(result['source_mono_ms'], 1150)
        self.assertEqual(result['face_detection_mono_ms'], 1000)
        self.assertIsNone(self.face.key)
        self.assertEqual(self.face.count, 0)

    def test_each_new_miss_requires_new_pixel_measurement(self):
        self.frame(1, 1000)
        self.detect(2, 1100, count=0)
        self.now, self.state.capture_stamp = 1101, 1100
        self.assertEqual(observation(self.state)['state'], 'UNCONFIRMED')

    def legacy_observation(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('frozen_v9_observation',
            '/home/ghmd/aura-pan-follow-shadow-20261024/face_source_v9/face_observation.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module.observation(self.state)

    def test_delayed_miss_publication_does_not_hide_same_image_already_measured(self):
        self.frame(1,1000)
        value=self.frame(2,1100,self.moved())
        self.assertEqual(value['detector_frame_id'],1)
        self.detect(2,1100,count=0)
        self.assertEqual(self.legacy_observation()['state'],'UNCONFIRMED')
        result=observation(self.state)
        self.assertEqual(result['state'],'READY')
        self.assertTrue(result['detection_miss'])
        self.assertEqual(result['source_frame_id'],2)
        self.assertEqual(result['source_mono_ms'],1100)
        self.assertEqual(result['deadline_mono_ms'],1350)

    def test_delayed_miss_publication_accepts_already_measured_newer_image(self):
        self.frame(1,1000)
        self.frame(3,1150,self.moved())
        self.detect(2,1100,count=0)
        self.assertEqual(self.legacy_observation()['state'],'UNCONFIRMED')
        result=observation(self.state)
        self.assertEqual(result['state'],'READY')
        self.assertEqual(result['source_frame_id'],3)
        self.assertEqual(result['source_mono_ms'],1150)

    def test_miss_requires_pixel_time_and_frame_both_not_older(self):
        for fid,stamp in [(3,1100),(2,1151),(4,1160)]:
            self.setUp();self.frame(1,1000);self.frame(2,1150,self.moved())
            self.detect(fid,stamp,count=0)
            self.now=max(1151,stamp+1);self.state.capture_stamp=self.now-1
            self.assertEqual(observation(self.state)['state'],'UNCONFIRMED')

    def test_delayed_miss_never_borrows_wrong_continuity_or_expired_pixels(self):
        self.frame(1,1000);self.frame(3,1150,self.moved());self.detect(2,1100,count=0)
        self.face.continuity_key=dict(self.key,track_generation=9)
        self.assertEqual(observation(self.state)['state'],'UNCONFIRMED')
        self.face.continuity_key=dict(self.key)
        self.now=1400;self.state.capture_stamp=1399
        self.assertEqual(observation(self.state)['state'],'EXPIRED')
        self.assertEqual(self.flow.value['stamp'],1150)

    def test_equal_identity_skips_only_redundant_anchor_ncc(self):
        self.frame(1,1000);self.detect(2,1100)
        calls=[];step=self.flow.step
        def counted(*args):calls.append(args);return step(*args)
        self.flow.step=counted
        value=self.frame(2,1100)
        self.assertEqual(value['key'],self.key)
        self.assertEqual(len(calls),0)
        self.assertEqual(self.flow.continuity_match_skips,1)
        self.frame(3,1150,self.moved())
        self.assertEqual(len(calls),1)
        self.assertEqual(self.flow.continuity_match_calls,0)

    def test_key_churn_still_needs_real_old_pixel_continuity_ncc(self):
        self.frame(1,1000)
        other=dict(self.key,track_generation=7)
        self.detect(2,1100,key=other)
        value=self.frame(2,1100)
        self.assertEqual(value['key'],self.key)
        self.assertEqual(self.flow.continuity_match_skips,0)
        self.assertEqual(self.flow.continuity_match_calls,1)

    def test_expired_or_invalid_binding_never_uses_identity_shortcut(self):
        self.frame(1,1000);self.detect(2,1500)
        self.frame(2,1500)
        self.assertEqual(self.flow.continuity_match_skips,0)
        self.setUp();self.frame(1,1000)
        self.assertIsNone(self.frame(2,1050,np.zeros_like(self.gray)))
        self.detect(3,1100)
        self.frame(3,1100)
        self.assertEqual(self.flow.continuity_match_skips,0)

    def test_missing_face_and_unrelated_texture_fail_immediately(self):
        for gray in (np.zeros_like(self.gray), np.random.RandomState(30).randint(0, 256, self.gray.shape, dtype=np.uint8)):
            self.setUp()
            self.frame(1, 1000)
            self.detect(2, 1100, count=0)
            self.assertIsNone(self.frame(3, 1150, gray))
            self.assertEqual(observation(self.state)['state'], 'UNCONFIRMED')

    def test_failed_match_cannot_blindly_reacquire_from_old_anchor(self):
        self.frame(1, 1000)
        self.assertIsNone(self.frame(2, 1050, np.zeros_like(self.gray)))
        self.assertIsNone(self.frame(3, 1100))
        self.detect(4, 1150)
        self.assertIsNotNone(self.frame(4, 1150))

    def test_detection_miss_never_renews_500ms_anchor(self):
        self.frame(1, 1000)
        self.detect(2, 1400, count=0)
        self.assertIsNotNone(self.frame(3, 1498))
        self.assertEqual(observation(self.state)['state'], 'READY')
        self.assertIsNone(self.frame(4, 1500))
        self.assertEqual(self.flow.reason, 'FACE_ANCHOR_EXPIRED')

    def test_motion_ttl_stays_250ms_and_polling_cannot_refresh_it(self):
        self.frame(1, 1000)
        self.now, self.state.capture_stamp = 1249, 1249
        self.assertEqual(observation(self.state)['state'], 'READY')
        self.now, self.state.capture_stamp = 1250, 1250
        self.assertEqual(observation(self.state)['state'], 'EXPIRED')
        self.assertEqual(self.flow.value['stamp'], 1000)

    def test_old_frame_ids_and_equal_or_old_stamps_are_rejected(self):
        self.frame(1, 1000)
        image = self.image(self.gray)
        for fid, stamp in ((1, 1100), (2, 1000), (3, 999)):
            self.flow.offer(image, fid, stamp)
            self.assertEqual(self.flow.latest[:2], (1, 1000))
            value, reason = self.flow.measure(image, fid, stamp, self.flow.detector_snapshot())
            self.assertIsNone(value)
            self.assertEqual(reason, 'NON_NEW_IMAGE')

    def test_multiface_invalidates_before_worker_runs(self):
        self.frame(1, 1000)
        self.detect(2, 1100, count=2)
        self.assertEqual(observation(self.state)['state'], 'MULTIPLE_FACES')
        self.assertIsNone(self.frame(3, 1150))
        self.detect(4, 1200, count=0)
        self.assertIsNone(self.frame(5, 1250))

    def test_key_churn_preserves_motion_key_only_on_same_face_pixels(self):
        self.frame(1, 1000)
        self.frame(2, 1050, self.moved())
        other_key = dict(self.key, track_id=9, track_generation=7)
        self.detect(3, 1100, key=other_key, box=[216., 114., 180., 180.])
        value = self.frame(3, 1100, self.moved())
        self.assertEqual(value['key'], self.key)
        self.assertEqual(value['detector_key'], other_key)
        self.assertEqual(self.face.key, other_key)
        result = observation(self.state)
        self.assertEqual(result['state'], 'READY')
        self.assertEqual(result['target']['track_id'], 1)

    def test_new_unrelated_face_does_not_inherit_motion_key(self):
        self.frame(1, 1000)
        gray = np.zeros_like(self.gray)
        gray[60:150, 190:280] = np.random.RandomState(31).randint(0, 256, (90, 90), dtype=np.uint8)
        other_key = dict(self.key, track_id=9, track_generation=7)
        self.detect(2, 1100, key=other_key, box=[380., 120., 180., 180.])
        self.assertEqual(self.frame(2, 1100, gray)['key'], other_key)

    def test_single_unconfirmed_detection_invalidates_binding(self):
        self.frame(1, 1000)
        self.detect(2, 1100)
        self.face.key = None
        self.assertIsNone(self.frame(3, 1150))
        self.assertEqual(self.flow.reason, 'UNCONFIRMED_DETECTION')

    def test_missed_intermediate_multiface_cannot_reuse_motion_binding(self):
        self.frame(1, 1000)
        self.detect(2, 1100, count=2)
        self.detect(3, 1150, count=0)
        self.assertIsNone(self.frame(4, 1200))
        self.assertEqual(self.flow.reason, 'FACE_CONTINUITY_LOST')

    def test_visible_clipping_accepts_small_edge_crossing(self):
        gray = np.zeros_like(self.gray)
        gray[60:150, 6:96] = self.gray[60:150, 100:190]
        box = [6., 60., 90., 90.]
        moved = cv2.warpAffine(gray, np.float32([[1, 0, -12], [0, 1, 0]]), (320, 240))
        measured, _ = FaceFlow.step(gray, moved, FaceFlow.seed(gray, box), box)
        self.assertAlmostEqual(measured[0], -6, delta=.5)
        self.assertEqual(FaceFlow.clipped(measured, moved.shape)[0], 0.)
        self.assertIsNone(FaceFlow.clipped([-60., 60., 90., 90.], moved.shape))

    def legacy_step(self,current,state,box):
        import importlib.util
        spec=importlib.util.spec_from_file_location('frozen_v10_flow',
            '/home/ghmd/aura-pan-follow-shadow-20261024/face_source_v10/face_flow.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module.FaceFlow.step(None,current,state,box)

    def edge_fixture(self,side,shift=46):
        gray=np.zeros_like(self.gray)
        x=6 if side<0 else 224
        gray[60:150,x:x+90]=self.gray[60:150,100:190]
        box=[float(x),60.,90.,90.]
        state=FaceFlow.seed(gray,box)
        current=cv2.warpAffine(gray,np.float32([[1,0,side*shift],[0,1,0]]),(320,240))
        return gray,current,state,box

    def test_legitimate_55_percent_face_clip_has_fixed_patch_matches(self):
        for side in [-1,1]:
            with self.subTest(side=side):
                _,current,state,box=self.edge_fixture(side)
                self.assertIsNone(self.legacy_step(current,state,box))
                measured=FaceFlow.step(None,current,state,box)
                self.assertIsNotNone(measured)
                updated,new_state=measured
                self.assertAlmostEqual(updated[0],box[0]+side*46,delta=1.)
                self.assertAlmostEqual(updated[1],box[1],delta=1.)
                self.assertEqual(new_state['method'],'FACE_TEMPLATE_PARTIAL_FIXED_ANCHOR')
                self.assertEqual(new_state['partial_patch_count'],2)
                self.assertIs(new_state['template'],state['template'])
                self.assertEqual(new_state['offset'],state['offset'])
                self.assertGreaterEqual(new_state['match_score'],.8)
                self.assertAlmostEqual(FaceFlow.clipped(updated,current.shape)[2]/90.,50./90.,delta=.02)

    def test_too_much_occlusion_still_rejects_original_face_quality(self):
        for side in [-1,1]:
            _,current,state,box=self.edge_fixture(side,shift=54)
            self.assertIsNone(FaceFlow.step(None,current,state,box))

    def test_one_partial_patch_or_inconsistent_patch_motion_never_suffices(self):
        _,current,state,box=self.edge_fixture(-1)
        th,tw=state['template'].shape;ox,oy=state['offset']
        new_x=box[0]-46+ox+tw//2;new_y=box[1]+oy
        one_patch=current.copy()
        one_patch[int(new_y)+th//2:int(new_y)+th,int(new_x):int(new_x)+tw-tw//2]=0
        self.assertIsNone(FaceFlow.step(None,one_patch,state,box))
        inconsistent=current.copy()
        y0,y1=int(new_y)+th//2,int(new_y)+th
        x0,x1=int(new_x),int(new_x)+tw-tw//2
        patch=inconsistent[y0:y1,x0:x1].copy()
        inconsistent[y0:y1,x0:x1]=0
        inconsistent[y0:y1,x0+5:x1+5]=patch
        self.assertIsNone(FaceFlow.step(None,inconsistent,state,box))

    def test_partial_fallback_rejects_missing_face_and_moving_random_background(self):
        _,current,state,box=self.edge_fixture(-1)
        for frame in [np.zeros_like(current),np.random.RandomState(882).randint(0,256,current.shape,dtype=np.uint8)]:
            self.assertIsNone(FaceFlow.step(None,frame,state,box))

    def test_partial_fixed_anchor_cannot_roll_into_an_occluder(self):
        _,current,state,box=self.edge_fixture(-1)
        updated,partial=FaceFlow.step(None,current,state,box)
        bad=np.random.RandomState(883).randint(0,256,current.shape,dtype=np.uint8)
        self.assertIsNone(FaceFlow.step(None,bad,partial,updated))
        self.assertIs(partial['template'],state['template'])

    def test_moving_background_does_not_move_face(self):
        rng = np.random.RandomState(32)
        background = rng.randint(0, 128, self.gray.shape, dtype=np.uint8)
        previous = background.copy()
        previous[60:150, 100:190] = self.gray[60:150, 100:190]
        current = cv2.warpAffine(background, np.float32([[1, 0, 12], [0, 1, 0]]), (320, 240))
        current[60:150, 100:190] = previous[60:150, 100:190]
        measured, _ = FaceFlow.step(previous, current, FaceFlow.seed(previous, [100., 60., 90., 90.]), [100., 60., 90., 90.])
        self.assertAlmostEqual(measured[0], 100., delta=.5)

    def test_camera_fault_or_stale_capture_rejects_fresh_template(self):
        self.frame(1, 1000)
        self.state.camera_error = 'test camera fault'
        self.assertEqual(observation(self.state)['state'], 'FACE_ERROR')
        self.state.camera_error = ''
        self.state.capture_stamp = 700
        self.assertEqual(observation(self.state)['state'], 'EXPIRED')

    def test_worker_uses_real_async_offer_and_stops(self):
        self.face._edge_signal = threading.Condition()
        self.face._edge_revision = 0
        flow = FaceFlow(self.face)
        try:
            flow.offer(self.image(self.gray), 1, 1000)
            with self.face._edge_signal:
                self.assertTrue(self.face._edge_signal.wait_for(lambda: self.face._edge_revision > 0, timeout=2))
            value, error = flow.snapshot()
            self.assertEqual(error, '')
            self.assertEqual(value['stamp'], 1000)
        finally:
            flow.close()
        self.assertFalse(flow.thread.is_alive())
        self.assertIsNone(flow.snapshot()[0])

    def test_actual_face_target_service_miss_contract(self):
        from board.identity.face_targets import FaceTargetService
        service = FaceTargetService(lambda: None, lambda *args: None, 'camera', clock=lambda: self.now)
        service.ready = True
        self.face = service
        self.state.identity.face_targets = service
        self.flow = FaceFlow(service, start=False)
        service._edge_flow = self.flow
        row = [200., 120., 180., 180., 240., 170., 320., 170., 280., 205., 250., 250., 310., 250., .97]
        detector = SimpleNamespace(detect=lambda image: [row])
        for fid, stamp in ((1, 1000), (2, 1100)):
            self.now = stamp+1
            image = self.image(self.gray)
            service.process((image, fid, stamp), detector)
            self.frame(fid, stamp)
        self.assertEqual(observation(self.state)['state'], 'READY')
        key = dict(service.key)
        self.now = 1201
        service.process((self.image(self.gray), 3, 1200), SimpleNamespace(detect=lambda image: []))
        self.assertEqual(service.count, 0)
        self.assertIsNone(service.key)
        self.assertEqual(service.continuity_key, key)
        self.frame(4, 1250, self.moved())
        result = observation(self.state)
        self.assertEqual(result['state'], 'READY')
        self.assertEqual(result['source_mono_ms'], 1250)
        self.assertEqual(result['face_detection_mono_ms'], 1100)

    def test_raw_offer_reaches_flow_before_blocking_detector_offer(self):
        from raw_capture import raw_first_offer
        entered, release = threading.Event(), threading.Event()
        calls = []
        image = self.image(self.gray)
        def original(face, actual_image, fid, stamp):
            calls.append((face, actual_image, fid, stamp))
            entered.set()
            release.wait(timeout=2)
            return 'original-result'
        result = []
        thread = threading.Thread(target=lambda: result.append(raw_first_offer(original)(self.face, image, 1, 1000)))
        try:
            thread.start()
            self.assertTrue(entered.wait(timeout=2))
            self.assertEqual(self.flow.offered, 1)
            self.assertIs(self.flow.latest[2], image)
            self.assertEqual(self.flow.latest[:2], (1, 1000))
            self.assertIs(calls[0][1], image)
            self.assertEqual(calls[0][2:], (1, 1000))
        finally:
            release.set()
            thread.join(timeout=2)
        self.assertEqual(result, ['original-result'])
        self.assertEqual(len(calls), 1)

    def test_worker_reselects_latest_capture_after_detector_lock_wait(self):
        self.face._edge_signal = threading.Condition()
        self.face._edge_revision = 0
        flow = FaceFlow(self.face, start=False)
        entered, release = threading.Event(), threading.Event()
        original_snapshot = flow.detector_snapshot
        def snapshot():
            entered.set()
            release.wait(timeout=2)
            return original_snapshot()
        flow.detector_snapshot = snapshot
        flow.thread = threading.Thread(target=flow.work, daemon=True)
        try:
            flow.offer(self.image(self.gray), 1, 1000)
            flow.thread.start()
            self.assertTrue(entered.wait(timeout=2))
            self.now = 1051
            flow.offer(self.image(self.moved()), 2, 1050)
            release.set()
            with self.face._edge_signal:
                self.assertTrue(self.face._edge_signal.wait_for(lambda: self.face._edge_revision > 0, timeout=2))
            value, error = flow.snapshot()
            self.assertEqual(error, '')
            self.assertEqual(value['frame_id'], 2)
            self.assertEqual(value['stamp'], 1050)
            self.assertEqual(flow.diagnostics()['source_age_at_start_ms'], 1)
        finally:
            release.set()
            flow.close()

    def test_server_anchor_age_is_strictly_below_500ms(self):
        self.frame(1, 1000)
        self.detect(2, 1400, count=0)
        self.frame(3, 1490)
        self.now = 1499
        result = observation(self.state)
        self.assertEqual(result['state'], 'READY')
        self.assertEqual(result['evaluated_mono_ms'], 1499)
        self.assertEqual(result['face_detection_age_ms'], 499)
        self.now = 1500
        self.assertEqual(observation(self.state)['state'], 'EXPIRED')

    def test_raw_offer_diagnostics_record_capture_and_arrival_gaps(self):
        self.now = 1010
        self.flow.offer(self.image(self.gray), 1, 1000)
        self.now = 1175
        self.flow.offer(self.image(self.gray), 2, 1055)
        diagnostics = self.flow.diagnostics()
        self.assertEqual(diagnostics['offer_source_age_ms'], 120)
        self.assertEqual(diagnostics['offer_gap_ms'], 55)
        self.assertEqual(diagnostics['offer_arrival_gap_ms'], 165)

    def test_install_wraps_existing_source_without_duplicate_flow_offer(self):
        import importlib.util
        from raw_capture import install
        from board.identity.face_targets import FaceTargetService
        spec = importlib.util.spec_from_file_location('v11_test_original_source',
            '/home/ghmd/aura-pan-follow-shadow-20261024/face_edge_v5/face_source.py')
        source = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(source)
        saved = {name: getattr(FaceTargetService, name) for name in ('__init__', 'offer', 'close')}
        camera = SimpleNamespace(handler_for=lambda state: object)
        service = None
        try:
            install(source)
            source.install(camera, interval_ms=100, optical_flow=True)
            wrapped = FaceTargetService.offer
            source.install(camera, interval_ms=100, optical_flow=True)
            self.assertIs(wrapped, FaceTargetService.offer)
            service = FaceTargetService(lambda: None, lambda *args: None, 'camera', clock=lambda: self.now)
            calls = []
            real_offer = service._edge_flow.offer
            def counted(image, fid, stamp):
                calls.append((image, fid, stamp))
                real_offer(image, fid, stamp)
            service._edge_flow.offer = counted
            image = self.image(self.gray)
            service.offer(image, 1, 1000)
            self.assertEqual(len(calls), 1)
            self.assertIs(calls[0][0], image)
            self.assertIs(service.pending[0], image)
            self.assertEqual(service.pending[1:], (1, 1000))
        finally:
            if service is not None:
                service.close()
            for name, value in saved.items():
                setattr(FaceTargetService, name, value)


if __name__ == '__main__':
    unittest.main()
