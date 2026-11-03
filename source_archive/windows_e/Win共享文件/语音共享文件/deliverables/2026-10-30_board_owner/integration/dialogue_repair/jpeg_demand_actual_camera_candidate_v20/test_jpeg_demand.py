"""Public synthetic frames only. No device, socket, image file or model is opened."""
from concurrent.futures import ThreadPoolExecutor
import ast
import gc
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import threading
import types
import unittest
import weakref
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

from board.interaction.ui_contract import validate_snapshot
from board.interaction.ui_services import UiServiceClient
from board.runtime import visual_capture
from board.vision import ui_camera_service as camera
from board.vision.local_preview import MAGIC, PIXELS, PREFIX, TRANSPORT, unpack
from tools.board_camera_preview import CameraPreviewWorker


JPEG = b'\xff\xd8' + b'public-synthetic-payload' * 8 + b'\xff\xd9'
PIXEL_DATA = bytes([20, 60, 120]) * (640 * 480)


class TracedLock:
    def __init__(self):
        self.lock = threading.Lock()
        self.waiting = threading.Event()
        self.timeouts = []

    def acquire(self, *, timeout):
        self.timeouts.append(timeout)
        self.waiting.set()
        return self.lock.acquire(timeout=timeout)

    def release(self):
        self.lock.release()


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.state = camera.CameraState('synthetic-boot', 'synthetic-service', clock=lambda: self.now)
        self.state.raw_preview = True

    def publish(self, fid=1, pixels=PIXEL_DATA, stamp=None):
        stamp = self.now if stamp is None else stamp
        self.state.captured(stamp)
        self.state.publish_preview(fid, stamp, pixels=pixels)

    def get(self, fid=1):
        return self.state.preview(self.state.camera_epoch, fid)

    def http(self, path):
        handler = camera.handler_for(self.state).__new__(camera.handler_for(self.state))
        handler.path = path
        handler.wfile = io.BytesIO()
        result = {'headers': {}}
        handler.send_response = lambda code: result.update(status=code)
        handler.send_header = lambda name, value: result['headers'].update({name: value})
        handler.end_headers = lambda: None
        handler.do_GET()
        result['body'] = handler.wfile.getvalue()
        return result

    def test_no_request_never_encodes_and_reference_stays_compatible(self):
        with patch.object(camera, 'encode_preview') as encode:
            for fid in range(1, 21):
                self.publish(fid)
                value = validate_snapshot(self.state.snapshot(), self.state.boot, self.now)
                self.assertEqual(value['preview'], dict(camera_epoch=self.state.camera_epoch,
                                                       frame_id=fid, captured_mono_ms=self.now))
                self.assertEqual(value['modules']['camera']['preview_transport'], TRANSPORT)
                self.state.health()
            encode.assert_not_called()
        self.assertEqual(list(self.state.frames), list(range(13, 21)))
        self.assertTrue(all(frame.pixels is PIXEL_DATA and frame.jpeg is None
                            for frame in self.state.frames.values()))
        self.assertEqual(self.state.preview_frames, 20)

    def test_old_preencoded_entry_point_is_preserved(self):
        self.state.captured(self.now)
        self.state.publish_preview(1, self.now, JPEG)
        with patch.object(camera, 'encode_preview') as encode:
            self.assertEqual(self.get(), JPEG)
            encode.assert_not_called()

    def test_input_requires_an_immutable_full_sized_payload(self):
        for value in (bytearray(PIXEL_DATA), b'', PIXEL_DATA[:-1], PIXEL_DATA + b'0'):
            with self.subTest(kind=type(value).__name__, size=len(value)):
                with self.assertRaises(ValueError):
                    self.state.publish_preview(1, self.now, pixels=value)
        for kwargs in ({}, {'jpeg': JPEG, 'pixels': PIXEL_DATA}):
            with self.assertRaises(ValueError):
                self.state.publish_preview(1, self.now, **kwargs)
        self.assertEqual(len(self.state.frames), 0)

    def test_old_requested_frame_uses_its_own_overlaid_pixels_and_caches(self):
        other = bytes([120, 60, 20]) * (640 * 480)
        self.publish(1)
        self.publish(2, other)
        with patch.object(camera, 'encode_preview', return_value=JPEG) as encode:
            self.assertEqual(self.get(1), JPEG)
            self.assertEqual(self.get(1), JPEG)
            encode.assert_called_once_with(PIXEL_DATA)
        self.assertIsNone(self.state.frames[1].pixels)
        self.assertIs(self.state.frames[2].pixels, other)

    def test_freshness_edges_future_epoch_camera_error_and_eviction(self):
        for age in (-1, 0, 999, 1000):
            self.state.frames.clear()
            self.publish(stamp=self.now-age)
            with patch.object(camera, 'encode_preview', return_value=JPEG) as encode:
                self.assertEqual(self.get(), JPEG if age in (0, 999) else None)
                self.assertEqual(encode.call_count, int(age in (0, 999)))
        self.publish()
        with patch.object(camera, 'encode_preview') as encode:
            self.assertIsNone(self.state.preview('foreign', 1))
            self.state.camera_error = 'synthetic capture fault'
            self.assertIsNone(self.get())
            self.state.camera_error = ''
            for fid in range(2, 10):
                self.publish(fid)
            self.assertIsNone(self.get(1))
            encode.assert_not_called()

    def test_concurrent_same_frame_is_single_flight(self):
        self.publish()
        entered, release = threading.Event(), threading.Event()

        def encode(pixels):
            entered.set()
            self.assertTrue(release.wait(2))
            return JPEG

        with patch.object(camera, 'encode_preview', side_effect=encode) as mocked:
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = [pool.submit(self.get) for _ in range(8)]
                self.assertTrue(entered.wait(1))
                release.set()
                self.assertEqual([future.result(2) for future in futures], [JPEG] * 8)
            self.assertEqual(mocked.call_count, 1)

    def test_state_reads_raw_publication_and_cached_get_do_not_wait_for_encoder(self):
        self.publish(1)
        self.state.publish_preview(2, self.now, JPEG)
        entered, release = threading.Event(), threading.Event()

        def encode(pixels):
            entered.set()
            self.assertTrue(release.wait(2))
            return JPEG

        with patch.object(camera, 'encode_preview', side_effect=encode):
            with ThreadPoolExecutor(max_workers=2) as pool:
                future = pool.submit(self.get, 1)
                self.assertTrue(entered.wait(1))
                try:
                    def read_and_publish():
                        value = self.state.snapshot()
                        self.state.health()
                        self.publish(3)
                        return value['preview']['frame_id'], self.get(2)
                    self.assertEqual(pool.submit(read_and_publish).result(.5), (2, JPEG))
                finally:
                    release.set()
                self.assertEqual(future.result(1), JPEG)

    def test_wait_budget_is_remaining_original_ttl_and_timeout_returns_no_frame(self):
        self.publish(stamp=1)
        lock = Mock()
        lock.acquire.return_value = False
        self.state.preview_encoding_lock = lock
        with patch.object(camera, 'encode_preview') as encode:
            self.assertIsNone(self.get())
            lock.acquire.assert_called_once_with(timeout=.001)
            lock.release.assert_not_called()
            encode.assert_not_called()

    def test_waiter_does_not_keep_evicted_frame_alive(self):
        self.publish()
        reference = weakref.ref(self.state.frames[1])
        lock = TracedLock()
        self.state.preview_encoding_lock = lock
        lock.lock.acquire()
        with patch.object(camera, 'encode_preview') as encode:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self.get)
                self.assertTrue(lock.waiting.wait(1))
                try:
                    for fid in range(2, 10):
                        self.publish(fid)
                    gc.collect()
                    self.assertIsNone(reference())
                finally:
                    lock.release()
                self.assertIsNone(future.result(1))
            encode.assert_not_called()

    def test_different_frames_share_one_encoder_and_keep_their_own_pixels(self):
        self.publish(1)
        other = bytes(PIXELS)
        self.publish(2, other)
        entered, release = threading.Event(), threading.Event()
        lock = TracedLock()
        self.state.preview_encoding_lock = lock
        seen = []

        def encode(pixels):
            seen.append(pixels)
            if len(seen) == 1:
                entered.set()
                self.assertTrue(release.wait(2))
            return JPEG

        with patch.object(camera, 'encode_preview', side_effect=encode):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(self.get, 1)
                self.assertTrue(entered.wait(1))
                lock.waiting.clear()
                second = pool.submit(self.get, 2)
                try:
                    self.assertTrue(lock.waiting.wait(1))
                    self.assertEqual(seen, [PIXEL_DATA])
                finally:
                    release.set()
                self.assertEqual(first.result(1), JPEG)
                self.assertEqual(second.result(1), JPEG)
        self.assertEqual(seen, [PIXEL_DATA, other])

    def test_actual_nested_producer_paints_once_and_publishes_raw_reference_without_encoding(self):
        import numpy as np
        tree = ast.parse(Path(camera.__file__).read_text('utf-8'))
        run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'run')
        producer = next(node for node in ast.walk(run) if isinstance(node, ast.FunctionDef) and node.name == 'preview')
        block = ast.fix_missing_locations(ast.Module(body=[producer], type_ignores=[]))
        stop = threading.Event()
        source = np.full((480, 640, 3), 25, np.uint8)
        raw = Mock()
        raw.publish.side_effect = lambda *args: stop.set()
        cv = Mock(FONT_HERSHEY_SIMPLEX=0)
        cv.imencode.side_effect = AssertionError('Producer must not encode a JPEG')
        cv.rectangle.side_effect = lambda image, *args: image.__setitem__((0, 0), [1, 2, 3])
        cv.putText.side_effect = lambda image, *args: image.__setitem__((1, 1), [7, 8, 9])
        self.state.captured(self.now)
        self.state.observed(1, self.now, {'target_id': 1, 'tracks': [
            {'track_id': 1, 'generation': 1, 'visible': True, 'confirmed': True,
             'box': (5, 5, 10, 10), 'score': .8}]}, 1.)
        self.state.pipeline_metrics.enabled = True
        namespace = dict(vars(camera), state=self.state, stop=stop, condition=threading.Condition(),
                         latest=[(1, self.now, source)], cv2=cv, raw=raw, millis=lambda: self.now)
        exec(compile(block, camera.__file__, 'exec'), namespace)
        with patch.object(camera, 'encode_preview') as encode:
            namespace['preview']()
            encode.assert_not_called()
        cv.imencode.assert_not_called()
        cv.rectangle.assert_called_once()
        cv.putText.assert_called_once()
        fid, stamp, pixels = raw.publish.call_args.args
        self.assertEqual((fid, stamp), (1, self.now))
        self.assertEqual(pixels[:3], bytes([1, 2, 3]))
        self.assertEqual(pixels[(640 + 1) * 3:(640 + 1) * 3 + 3], bytes([7, 8, 9]))
        self.assertTrue(np.all(source == 25))
        self.assertIs(self.state.frames[1].pixels, pixels)
        self.assertEqual(self.state.snapshot()['preview']['frame_id'], 1)
        metrics = self.state.pipeline_metrics.snapshot()['stages']
        self.assertEqual(metrics['preview.render_encode_publish']['count'], 1)
        self.assertEqual(metrics['preview.publish_source_age']['count'], 1)
        with patch.object(camera, 'encode_preview', return_value=JPEG) as encode:
            self.assertEqual(self.get(), JPEG)
            encode.assert_called_once_with(pixels)

    def invalidate(self, kind):
        if kind == 'expired':
            self.now += 1000
        elif kind == 'future':
            self.now -= 1
        elif kind == 'epoch':
            self.state.camera_epoch = 'replacement-camera'
        elif kind == 'camera_error':
            self.state.camera_error = 'synthetic capture fault'
        elif kind == 'replace':
            self.publish(1, bytes(PIXELS))
        elif kind == 'evict':
            for fid in range(2, 10):
                self.publish(fid)
        else:
            raise AssertionError(kind)

    def test_wait_rechecks_ttl_epoch_error_replacement_and_retirement_before_encode(self):
        for kind in ('expired', 'future', 'epoch', 'camera_error', 'replace', 'evict'):
            with self.subTest(kind=kind):
                self.setUp()
                self.publish()
                lock = TracedLock()
                self.state.preview_encoding_lock = lock
                lock.lock.acquire()
                epoch = self.state.camera_epoch
                with patch.object(camera, 'encode_preview') as encode:
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(self.state.preview, epoch, 1)
                        self.assertTrue(lock.waiting.wait(1))
                        try:
                            self.invalidate(kind)
                        finally:
                            lock.release()
                        self.assertIsNone(future.result(1))
                    encode.assert_not_called()
                    self.assertTrue(0 <= lock.timeouts[0] <= 1)

    def test_encode_completion_rechecks_ttl_epoch_error_replacement_and_retirement(self):
        for kind in ('expired', 'future', 'epoch', 'camera_error', 'replace', 'evict'):
            with self.subTest(kind=kind):
                self.setUp()
                self.publish()
                original = self.state.frames[1]

                def encode(pixels):
                    self.invalidate(kind)
                    return JPEG

                with patch.object(camera, 'encode_preview', side_effect=encode):
                    self.assertIsNone(self.get())
                self.assertIsNone(original.jpeg)
                self.assertFalse(self.state.preview_encoding_lock.locked())

    def test_failed_frame_is_not_reencoded_and_next_frame_recovers(self):
        self.publish()
        with patch.object(camera, 'encode_preview', side_effect=ValueError('synthetic encoder failure')) as encode:
            self.assertIsNone(self.get())
            self.assertIsNone(self.get())
            encode.assert_called_once()
        self.assertEqual(self.state.preview_error, 'synthetic encoder failure')
        self.publish(2)
        self.assertEqual(self.state.preview_error, '')
        with patch.object(camera, 'encode_preview', return_value=JPEG):
            self.assertEqual(self.get(2), JPEG)

    def test_failure_of_old_frame_does_not_poison_newer_publication(self):
        self.publish(1)
        self.publish(2)
        with patch.object(camera, 'encode_preview', side_effect=ValueError('old frame failure')):
            self.assertIsNone(self.get(1))
        self.assertEqual(self.state.preview_error, '')
        self.assertEqual(self.state.snapshot()['preview']['frame_id'], 2)

    def test_http_same_frame_headers_length_mime_and_no_store_are_unchanged(self):
        self.publish()
        path = f'/v1/ui/preview.jpg?camera_epoch={self.state.camera_epoch}&frame_id=1'
        with patch.object(camera, 'encode_preview', return_value=JPEG):
            response = self.http(path)
        self.assertEqual(response['status'], 200)
        self.assertEqual(response['body'], JPEG)
        self.assertEqual(response['headers'], {
            'Content-Type': 'image/jpeg', 'Content-Length': str(len(JPEG)), 'Cache-Control': 'no-store',
            'X-Aura-Boot-Id': self.state.boot, 'X-Aura-Camera-Epoch': self.state.camera_epoch,
            'X-Aura-Frame-Id': '1'})
        self.now += 1000
        self.assertEqual(self.http(path)['status'], 404)
        self.assertEqual(self.http('/v1/ui/preview.jpg')['status'], 404)

    def test_cached_get_never_extends_original_capture_ttl(self):
        self.publish()
        with patch.object(camera, 'encode_preview', return_value=JPEG) as encode:
            self.assertEqual(self.get(), JPEG)
            self.now = 1999
            self.assertEqual(self.get(), JPEG)
            self.now = 2000
            self.state.captured(self.now)
            self.assertIsNone(self.get())
            self.assertNotIn('preview', self.state.snapshot())
            encode.assert_called_once()

    def test_oversized_jpeg_fails_http_without_changing_raw_reference_or_retrying_frame(self):
        self.publish()
        cv = types.ModuleType('cv2')
        cv.IMWRITE_JPEG_QUALITY = 1
        encoded = Mock(nbytes=256 * 1024 + 1)
        cv.imencode = Mock(return_value=(True, encoded))
        path = f'/v1/ui/preview.jpg?camera_epoch={self.state.camera_epoch}&frame_id=1'
        with patch.dict(sys.modules, {'cv2': cv}):
            self.assertEqual(self.http(path)['status'], 404)
            self.assertEqual(self.http(path)['status'], 404)
        cv.imencode.assert_called_once()
        encoded.tobytes.assert_not_called()
        self.assertIn('size limit', self.state.preview_error)
        self.assertEqual(self.state.snapshot()['preview']['frame_id'], 1)
        self.assertIs(self.state.frames[1].pixels, PIXEL_DATA)

    def test_identity_crop_endpoint_is_independent_of_jpeg_encoding(self):
        self.state.identity = types.SimpleNamespace(face_preview=Mock(return_value=b'synthetic-png'))
        path = f'/v1/ui/identity-face.png?camera_epoch={self.state.camera_epoch}&frame_id=5&track_id=2&track_generation=3'
        with patch.object(camera, 'encode_preview') as encode:
            response = self.http(path)
            encode.assert_not_called()
        self.assertEqual(response['status'], 200)
        self.assertEqual(response['headers']['Content-Type'], 'image/png')
        self.assertEqual(response['headers']['X-Aura-Service-Epoch'], self.state.epoch)
        self.state.identity.face_preview.assert_called_once_with(
            dict(camera_epoch=self.state.camera_epoch, track_id=2, track_generation=3), 5)

    def test_unmodified_visual_capture_gets_exact_frame_and_digest(self):
        self.publish(1)
        self.publish(2, bytes(PIXELS))
        calls = []

        def urlopen(url, timeout):
            path = urlsplit(url)
            calls.append(path.path)
            response = self.http(path.path + ('?' + path.query if path.query else ''))
            stream = io.BytesIO(response['body'])
            stream.headers = response['headers']
            return stream

        with patch.object(camera, 'encode_preview', return_value=JPEG) as encode:
            with patch.object(visual_capture.urllib.request, 'urlopen', side_effect=urlopen):
                with patch.object(visual_capture.time, 'monotonic', side_effect=lambda: self.now / 1000):
                    frame, jpeg = visual_capture.current_frame(self.state.boot)
        self.assertEqual(calls, ['/v1/ui/status', '/v1/ui/preview.jpg'])
        self.assertEqual(frame['frame_id'], 2)
        self.assertEqual(frame['sha256'], hashlib.sha256(JPEG).hexdigest())
        self.assertEqual(jpeg, JPEG)
        encode.assert_called_once_with(bytes(PIXELS))

    def test_unmodified_visual_capture_includes_encoding_time_in_750ms_limit(self):
        for elapsed in (749, 750):
            with self.subTest(elapsed=elapsed):
                self.setUp()
                self.publish()

                def urlopen(url, timeout):
                    parsed = urlsplit(url)
                    response = self.http(parsed.path + ('?' + parsed.query if parsed.query else ''))
                    stream = io.BytesIO(response['body'])
                    stream.headers = response['headers']
                    return stream

                def encode(pixels):
                    self.now += elapsed
                    return JPEG

                with patch.object(camera, 'encode_preview', side_effect=encode):
                    with patch.object(visual_capture.urllib.request, 'urlopen', side_effect=urlopen):
                        with patch.object(visual_capture.time, 'monotonic', side_effect=lambda: self.now / 1000):
                            if elapsed == 749:
                                self.assertEqual(visual_capture.current_frame(self.state.boot)[1], JPEG)
                            else:
                                with self.assertRaisesRegex(ValueError, 'Stale visual frame'):
                                    visual_capture.current_frame(self.state.boot)

    def test_raw_wire_owner_layout_and_250ms_limit_are_unchanged(self):
        self.publish()
        owner = dict(board_boot_id=self.state.boot, service_epoch=self.state.epoch,
                     camera_epoch=self.state.camera_epoch)
        header = json.dumps(dict(owner, frame_id=1, captured_mono_ms=self.now)).encode()
        wire = PREFIX.pack(MAGIC, len(header)) + header + PIXEL_DATA
        self.assertEqual(unpack(wire, owner, self.now + 249)[1], PIXEL_DATA)
        for now in (self.now - 101, self.now + 250):
            with self.assertRaises(ValueError):
                unpack(wire, owner, now)
        for key in owner:
            with self.assertRaises(ValueError):
                unpack(wire, dict(owner, **{key: 'foreign'}), self.now)

    def test_native_display_accepts_snapshot_preview_without_a_jpeg(self):
        self.publish()
        snapshot = self.state.snapshot()
        owner = dict(board_boot_id=self.state.boot, service_epoch=self.state.epoch,
                     camera_epoch=self.state.camera_epoch)
        header = dict(owner, frame_id=1, captured_mono_ms=self.now)
        worker = CameraPreviewWorker.__new__(CameraPreviewWorker)
        worker.lock = threading.RLock()
        worker.stop = Mock()
        worker.stop.wait.side_effect = [False, True]
        output = {'pipeline': Mock()}
        output['pipeline'].get_bus.return_value.pop_filtered.return_value = None
        worker.outputs = {'synthetic-display': output}
        worker.Gst = types.SimpleNamespace(MessageType=types.SimpleNamespace(ERROR=1))
        worker.reader_owner = owner
        worker.reader = Mock()
        worker.reader.read.return_value = (header, PIXEL_DATA)
        worker.last_key = None
        worker.services = Mock()
        worker.services.read.return_value = dict(snapshot=snapshot, raw_preview=True, preview=None)
        worker.push, worker.clear = Mock(), Mock()
        with patch.object(camera, 'encode_preview') as encode:
            worker.work()
            encode.assert_not_called()
        worker.push.assert_called_once_with(header, PIXEL_DATA)
        worker.clear.assert_not_called()
        self.assertEqual(worker.error, '')


class EncoderContractTests(unittest.TestCase):
    def test_original_opencv_quality_shape_and_bounded_bytes(self):
        import numpy as np
        for ok, size in ((True, 256 * 1024), (True, 256 * 1024 + 1), (False, 100)):
            with self.subTest(ok=ok, size=size):
                cv = types.ModuleType('cv2')
                cv.IMWRITE_JPEG_QUALITY = 1
                encoded = Mock(nbytes=size)
                encoded.tobytes.return_value = b'encoded'
                cv.imencode = Mock(return_value=(ok, encoded))
                with patch.dict('sys.modules', {'cv2': cv}):
                    if ok and size <= 256 * 1024:
                        self.assertEqual(camera.encode_preview(PIXEL_DATA), b'encoded')
                    else:
                        with self.assertRaises(ValueError):
                            camera.encode_preview(PIXEL_DATA)
                extension, image, parameters = cv.imencode.call_args.args
                self.assertEqual(extension, '.jpg')
                self.assertEqual(image.shape, (480, 640, 3))
                self.assertEqual(image.dtype, np.uint8)
                self.assertEqual(image.tobytes(), PIXEL_DATA)
                self.assertFalse(image.flags.writeable)
                self.assertEqual(parameters, [cv.IMWRITE_JPEG_QUALITY, 72])


class ActualEntryCompositionTests(unittest.TestCase):
    def load(self, name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        self.addCleanup(lambda: sys.modules.pop(name, None))
        spec.loader.exec_module(module)
        return module

    def test_actual_camera_feed_motion_stream_face_source_and_raw_offer_leave_jpeg_route_reachable(self):
        from board.motion import camera_feed
        here = Path(__file__).resolve().parent
        readback = here.parent / 'jpeg_demand_review_v20/actual_camera_source_9d714'
        composed = self.load('synthetic_composed_camera', here / 'after/board/vision/ui_camera_service.py')
        motion = self.load('synthetic_motion_stream', readback / '11_motion_stream.py')
        faces = self.load('synthetic_face_source', readback / '12_face_source.py')
        raw = self.load('synthetic_raw_capture', readback / '6_raw_capture.py')
        preserved = {name: getattr(composed.CameraState, name)
                     for name in ('snapshot', 'preview', 'publish_preview')}
        original_run = composed.run
        fake_faces = types.ModuleType('board.identity.face_targets')
        fake_faces.FaceTargetService = type('SyntheticFaceService', (), {
            '__init__': lambda self, *args, **kwargs: None,
            'offer': lambda self, *args, **kwargs: None,
            'close': lambda self: None})
        with patch.dict(sys.modules, {'board.identity.face_targets': fake_faces}):
            raw.install(faces)
            camera_feed.install(composed)
            motion.install(composed)
            faces.install(composed, interval_ms=100, optical_flow=True)
        for name, function in preserved.items():
            self.assertIs(getattr(composed.CameraState, name), function)
        self.assertIs(composed.run, original_run)
        self.assertTrue(composed._edge_face_raw_capture_v11)
        state = composed.CameraState('synthetic-boot', 'synthetic-service', clock=lambda: 1000)
        state.captured(1000)
        state.observed(1, 1000, {'target_id': None, 'tracks': []}, 1.)
        state.publish_preview(1, 1000, pixels=PIXEL_DATA)
        self.assertEqual(state._motion_revision, 1)
        handler_type = composed.handler_for(state)
        handler = handler_type.__new__(handler_type)
        handler.path = f'/v1/ui/preview.jpg?camera_epoch={state.camera_epoch}&frame_id=1'
        handler.wfile = io.BytesIO()
        codes, headers = [], {}
        handler.send_response = codes.append
        handler.send_header = lambda name, value: headers.update({name: value})
        handler.end_headers = lambda: None
        with patch.object(composed, 'encode_preview', return_value=JPEG) as encode:
            handler.do_GET()
            encode.assert_called_once_with(PIXEL_DATA)
        self.assertEqual(codes, [200])
        self.assertEqual(handler.wfile.getvalue(), JPEG)
        self.assertEqual(headers['X-Aura-Frame-Id'], '1')


if __name__ == '__main__':
    unittest.main()
