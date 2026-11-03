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


if __name__ == '__main__':
    unittest.main()
