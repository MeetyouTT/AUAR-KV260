"""Windows harness checks with explicit encoder/raw/RSS fixtures, not CPU evidence."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('jpeg_public_worker', HERE / 'worker.py')
worker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = worker
spec.loader.exec_module(worker)
if sys.platform == 'win32':
    fcntl = types.ModuleType('fcntl')
    fcntl.LOCK_EX, fcntl.LOCK_NB = 2, 4
    sys.modules['fcntl'] = fcntl  # Import-only. No flock operation is emulated.


class FixtureCv(types.ModuleType):
    IMWRITE_JPEG_QUALITY = 1
    FONT_HERSHEY_SIMPLEX = 0

    def __init__(self):
        super().__init__('cv2')

    def rectangle(self, image, *args):
        image[0, 0] = [0, 190, 255]

    def putText(self, image, *args):
        image[1, 1] = [40, 220, 60]

    def imencode(self, extension, image, parameters):
        if extension != '.jpg' or parameters != [self.IMWRITE_JPEG_QUALITY, 72]:
            raise AssertionError('Original JPEG parameters changed')
        # Markers/hash provide a protocol fixture, not a decodable JPEG image.
        data = b'\xff\xd8' + hashlib.sha256(image.tobytes()).hexdigest().encode() * 3 + b'\xff\xd9'
        return True, types.SimpleNamespace(nbytes=len(data), tobytes=lambda: data)


class WorkerTests(unittest.TestCase):
    def test_public_sources_match_and_unexpected_model_imports_are_blocked(self):
        self.assertEqual(len(worker.checked_sources()), 14)
        guard = worker.CpuOnlyImports()
        for name in ('gi', 'xir', 'vart', 'torch', 'onnxruntime', 'board.vision.dpu_yunet',
                     'board.vision.native_startup', 'board.identity.camera_faces'):
            with self.assertRaises(RuntimeError):
                guard.find_spec(name, None)
        self.assertIsNone(guard.find_spec('board.vision.native_errors', None))

    def test_public_ram_directory_has_no_non_shm_fallback(self):
        with patch.object(worker.Path, 'is_dir', return_value=False):
            with patch.object(worker.tempfile, 'mkdtemp') as make:
                with self.assertRaisesRegex(RuntimeError, 'no storage fallback'):
                    worker.public_directory()
                make.assert_not_called()

    def test_io_guard_refuses_real_media_private_db_models_and_network(self):
        for path in ('/dev/video0', '/dev/uio0', '/dev/dri/card0', '/run/aura-camera-ui-live.frame',
                     '/home/root/.local/share/aura/identities.sqlite3', '/some/model.onnx', '/some/model.xmodel'):
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                worker.cpu_only_io('open', (path, 'rb', 0))
        with self.assertRaises(RuntimeError):
            worker.cpu_only_io('socket.connect', (None, ('127.0.0.1', 8790)))
        with self.assertRaises(RuntimeError):
            worker.cpu_only_io('sqlite3.connect', (':memory:',))
        worker.cpu_only_io('open', ('/dev/shm/aura-jpeg-public-test/public.frame', 'wb', 0))

    def test_get_densities_are_explicit_and_never_paced_as_actual_capture(self):
        counts = {mode: sum(worker.wants_get(fid, mode, 15) for fid in range(1, 61)) for mode in worker.MODES}
        self.assertEqual(counts, {'no_get': 0, 'low_get': 2, 'legacy_get': 7})
        self.assertEqual(sum(worker.wants_get(fid, 'legacy_get', 30) for fid in range(1, 61)), 4)

    def test_describe_does_not_execute_arm_worker(self):
        out = io.StringIO()
        with patch.object(sys, 'argv', [str(HERE / 'worker.py'), '--describe']):
            with patch.object(worker, 'child') as child, patch('sys.stdout', out):
                self.assertEqual(worker.main(), 0)
                child.assert_not_called()
        report = json.loads(out.getvalue())
        self.assertEqual(report['total_measured_frames'], 360)

    def test_actual_producer_and_http_logic_with_explicit_public_fixtures(self):
        import numpy as np
        before, after = worker.load_camera('before'), worker.load_camera('after')
        from board.vision import local_preview
        stores = {}

        class MemoryRaw:
            def __init__(self, owner, directory):
                self.owner = dict(owner)
                self.key = (directory, owner['camera_epoch'])
                stores[self.key] = self

            def publish(self, frame_id, stamp, pixels):
                header = json.dumps(dict(self.owner, frame_id=frame_id, captured_mono_ms=stamp)).encode()
                self.wire = local_preview.PREFIX.pack(local_preview.MAGIC, len(header)) + header + pixels

            def close(self):
                stores.pop(self.key)

        class MemoryReader:
            def __init__(self, owner, directory):
                self.owner = dict(owner)
                self.key = (directory, owner['camera_epoch'])

            def read(self, now):
                return local_preview.unpack(stores[self.key].wire, self.owner, now)

        cv = FixtureCv()
        arms = []
        with patch.dict(sys.modules, {'cv2': cv}):
            with patch.object(local_preview, 'RawFrameStore', MemoryRaw), patch.object(local_preview, 'RawFrameReader', MemoryReader):
                with patch.object(worker, 'rss_bytes', return_value=1000):
                    for mode in worker.MODES:
                        for version, module in (('before', before), ('after', after)):
                            result = worker.phase(module, cv, np, Path('PUBLIC_IN_MEMORY_ONLY'), 6, mode, 2)
                            arms.append(dict(result, version=version, mode=mode))
                            expected_gets = sum(worker.wants_get(fid, mode, 2) for fid in range(1, 7))
                            self.assertEqual(result['encode_calls'], 6 if version == 'before' else expected_gets)
                            self.assertEqual(result['first_get_requests'], expected_gets)
                            self.assertEqual(result['cache_probe_requests'], expected_gets)
                            self.assertEqual(result['cache_max_entries'], 6)
                            self.assertLessEqual(result['cache_max_payload_bytes'], 8 * worker.PIXELS)
        self.assertFalse(stores)
        self.assertEqual(set(worker.compare(arms, 6)), set(worker.MODES))
        corrupted = copy.deepcopy(arms)
        corrupted[-1]['frame_digests'][0]['raw_sha256'] = '0' * 64
        with self.assertRaisesRegex(AssertionError, 'raw frame differs'):
            worker.compare(corrupted, 6)
        corrupted = copy.deepcopy(arms)
        corrupted[-1]['frame_digests'][0]['jpeg_sha256'] = '0' * 64
        with self.assertRaisesRegex(AssertionError, 'JPEG differs'):
            worker.compare(corrupted, 6)


if __name__ == '__main__':
    output = io.StringIO()
    started = time.monotonic()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WorkerTests))
    report = dict(status='PASS' if result.wasSuccessful() else 'FAIL', tests=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), seconds=time.monotonic() - started,
                  scope='PUBLIC_HARNESS_FIXTURES_ONLY_NOT_ARM_CPU_EVIDENCE',
                  opencv_executed=False, raw_files_opened=False, devices_accessed=False,
                  worker_sha256=worker.digest(HERE / 'worker.py'), test_sha256=worker.digest(Path(__file__)))
    (HERE / 'LOCAL_WORKER_TEST.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (HERE / 'LOCAL_WORKER_TEST.log').write_text(output.getvalue(), encoding='utf-8')
    print(json.dumps(report))
    if not result.wasSuccessful():
        print(output.getvalue())
    raise SystemExit(0 if result.wasSuccessful() else 1)
