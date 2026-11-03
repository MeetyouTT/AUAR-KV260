import json
import threading
import time
import unittest

import cv2
import numpy as np

from preview_motion import BackgroundMotion, CachedPreviewFetcher, PreviewMotionObserver, background_mask


def scene():
    rng = np.random.RandomState(43)
    return cv2.GaussianBlur(rng.randint(0, 256, (480, 640), dtype=np.uint8), (5, 5), 1.)


def meta(frame):
    return dict(board_boot_id='test-boot', camera_epoch='test-camera', frame_id=frame,
                captured_mono_ms=1000 + frame * 250, sample_mono_s=10. + frame * .25)


def shifted(gray, dx, dy):
    return cv2.warpAffine(gray, np.float32([[1, 0, dx], [0, 1, dy]]), (640, 480), borderMode=cv2.BORDER_REFLECT)


class PreviewMotionTests(unittest.TestCase):
    def setUp(self): cv2.setNumThreads(1)

    def test_known_translation_and_return_use_first_fixed_reference(self):
        image = scene()
        m = BackgroundMotion()
        self.assertEqual(m.process(image, meta(1))['state'], 'BASELINE_READY')
        for frame, dx, dy in ((2, 8, -4), (3, 16, 6), (4, 0, 0)):
            result = m.process(shifted(image, dx, dy), meta(frame))
            self.assertEqual(result['state'], 'MEASURED_BACKGROUND_SHIFT')
            self.assertAlmostEqual(result['dx_px'], dx, delta=.7)
            self.assertAlmostEqual(result['dy_px'], dy, delta=.7)
            self.assertEqual(result['reference_frame_id'], 1)

    def test_moving_central_foreground_does_not_replace_background_shift(self):
        image = scene()
        m = BackgroundMotion()
        before = image.copy();before[100:470, 224:416] = 0
        self.assertEqual(m.process(before, meta(1))['state'], 'BASELINE_READY')
        after = shifted(image, 10, 0);after[70:450, 224:416] = 255
        result = m.process(after, meta(2))
        self.assertEqual(result['state'], 'MEASURED_BACKGROUND_SHIFT')
        self.assertAlmostEqual(result['dx_px'], 10, delta=.7)

    def test_face_area_features_alone_cannot_be_background_measurement(self):
        image = np.full((480, 640), 127, np.uint8)
        image[100:180, 40:120] = scene()[100:180, 40:120]
        result = BackgroundMotion().process(image, meta(1), [[40, 100, 80, 80]])
        self.assertEqual(result['state'], 'UNMEASURABLE')
        self.assertIsNone(result['dx_px'])
        mask = background_mask((240, 320), [[40, 100, 80, 80]])
        self.assertEqual(mask[60, 40], 0)
        self.assertEqual(mask[30, 280], 255)

    def test_textureless_and_foreground_only_are_unmeasurable_not_zero_motion(self):
        for foreground in (False, True):
            image = np.full((480, 640), 127, np.uint8)
            if foreground: image[80:470, 224:416] = scene()[80:470, 224:416]
            m = BackgroundMotion()
            self.assertEqual(m.process(image, meta(1))['state'], 'UNMEASURABLE')
            result = m.process(image, meta(2))
            self.assertEqual(result['state'], 'UNMEASURABLE')
            self.assertIsNone(result['dx_px'])

    def test_duplicate_and_changed_context_never_claim_new_zero_displacement(self):
        m = BackgroundMotion();image = scene();m.process(image, meta(1))
        self.assertEqual(m.process(image, meta(1))['reason'], 'DUPLICATE_FRAME')
        changed = meta(2);changed['camera_epoch'] = 'other-camera'
        result = m.process(image, changed)
        self.assertEqual(result['state'], 'UNMEASURABLE')
        self.assertIsNone(result['dx_px'])

    def test_fetcher_pairs_requested_cached_jpeg_headers_and_original_timestamp(self):
        fetch = CachedPreviewFetcher('http://127.0.0.1:8790')
        status = dict(board_boot_id='test-boot', observed_mono_ms=1300,
                      preview=dict(camera_epoch='test-camera', frame_id=7, captured_mono_ms=1250))
        encoded = cv2.imencode('.jpg', scene())[1].tobytes()
        headers = {'x-aura-boot-id':'test-boot','x-aura-camera-epoch':'test-camera','x-aura-frame-id':'7'}
        paths = []
        def get(path, limit):
            paths.append(path)
            if path == '/v1/ui/status': return json.dumps(status).encode(), {}
            if path.startswith('/v1/ui/preview.jpg?'): return encoded, headers
            return b'{"state":"NO_TARGET"}', {}
        fetch.get = get
        image, metadata, boxes = fetch()
        self.assertEqual(image.shape, (480, 640))
        self.assertEqual(metadata['captured_mono_ms'], 1250)
        self.assertIn('camera_epoch=test-camera&frame_id=7', paths[1])
        headers['x-aura-frame-id'] = '8'
        with self.assertRaisesRegex(ValueError, 'MISMATCH'): fetch()

    def test_observer_numeric_only_join_requires_stop_and_finishes(self):
        image = scene();counter = [0]
        def fetch():
            counter[0] += 1
            return image, meta(counter[0]), []
        observer = PreviewMotionObserver(duration_s=.6, interval_s=.2, fetch=fetch).start()
        self.assertTrue(observer.wait_baseline(1.))
        with self.assertRaises(ValueError): observer.close_after_stop({'flags':15,'lease_left_ms':100})
        time.sleep(.22)
        result = observer.close_after_stop({'flags':0,'lease_left_ms':0,'reason':0})
        self.assertFalse(result['observer_alive'])
        self.assertFalse(result['images_saved'])
        self.assertFalse(result['actuator_access'])
        self.assertGreaterEqual(len(result['samples']), 2)
        json.dumps(result)  # No image array or identity object can enter the report.

    def test_join_is_bounded_and_reports_thread_still_alive(self):
        release = threading.Event()
        def fetch():
            release.wait(2)
            return scene(), meta(1), []
        observer = PreviewMotionObserver(duration_s=.3, fetch=fetch).start()
        began = time.monotonic()
        result = observer.close_after_stop({'flags':0,'lease_left_ms':0}, timeout_s=.01)
        self.assertLess(time.monotonic() - began, .2)
        self.assertTrue(result['observer_alive'])
        release.set();observer.thread.join(1.)


if __name__ == '__main__': unittest.main()
