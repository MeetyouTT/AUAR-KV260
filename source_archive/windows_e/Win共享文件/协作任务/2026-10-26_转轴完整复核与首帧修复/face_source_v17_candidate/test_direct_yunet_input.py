"""Compare against pinned production preprocess and complete detector decode."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'face_source_v16_candidate'))
sys.path.insert(0, str(HERE))
import direct_yunet_input as direct


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = Path('/home/ghmd/aura-native-live-20261024/r4/candidate/aura/board/vision')
reference = load('direct_reference_faces', BASE / 'reference_faces.py')
runtime = load('direct_reference_runtime', BASE / 'dpu_vision_runtime.py')


def measured(name, function, *args, **kwargs):
    return function(*args, **kwargs)


def heads(seed, faces=True):
    rng = np.random.RandomState(seed)
    result = {}
    for i, shape in enumerate([(5, 5, 51), (10, 10, 34), (40, 40, 51), (20, 20, 34)]):
        value = rng.uniform(-.5, .5, (1,) + shape).astype(np.float32)
        row = value.reshape(-1, 17)
        row[:, 14] = 4
        row[:, 15] = -4
        row[:, 16] = .5
        if faces:
            indices = np.arange(min(12, len(row))) * max(1, len(row) // 13)
            row[indices, 14] = -4
            row[indices, 15] = 4
            row[indices, 16] = 1
        result['head' + str(i)] = value
    return result


def make_adapter(values):
    class Adapter:
        def __init__(self, native=True):
            self.native_critical = native
            self.runner = types.SimpleNamespace(input_fix=7,
                inputs=[types.SimpleNamespace(dims=[1, 320, 320, 3])])
            self._admission_check = lambda: None
            self.inputs = []
            self.guards = []
            with patch.object(reference, 'checked_net', return_value=None):
                self.detector = reference.YuNetCompat('unused')
            self.detector.net = runtime.YuNetNetwork(self.runner, self.old_execute)

        def old_execute(self, source):
            self.inputs.append(runtime.encode(source, 7).copy())
            return values

        def _native_scheduled(self, source, check):
            self.guards.append(check)
            check()
            self.inputs.append(source.copy())
            return values
    return Adapter


class DirectTests(unittest.TestCase):
    def test_all_256_values_equal_original_rounding(self):
        image = np.resize(np.arange(256, dtype=np.uint8), (320, 320, 3))
        old = runtime.encode(np.ascontiguousarray(cv2.dnn.blobFromImage(image).transpose(0, 2, 3, 1) / 256.), 7)
        new = direct.encode_bgr(image)
        np.testing.assert_array_equal(old, new)
        self.assertEqual(new.dtype, np.int8)
        self.assertTrue(new.flags.c_contiguous)
        self.assertEqual(new.shape, (1, 320, 320, 3))
        self.assertEqual(int(new.max()), 127)

    def test_complete_detect_output_and_input_equal(self):
        rng = np.random.RandomState(73)
        for with_faces in (False, True):
            for shape in ((480, 640, 3), (333, 517, 3), (720, 1280, 3)):
                for reversed_view in (False, True):
                    image = rng.randint(0, 256, shape, dtype=np.uint8)
                    if reversed_view:
                        image = image[:, ::-1]
                    Adapter = make_adapter(heads(31, with_faces))
                    old = Adapter()
                    direct.install(Adapter, runtime.yunet_outputs, measured,
                                   reference.YuNetCompat, reference.bgr_image)
                    new = Adapter()
                    guard = new._admission_check
                    a = old.detector.detect(image)
                    b = new.detector.detect(image)
                    np.testing.assert_array_equal(a, b)
                    np.testing.assert_array_equal(old.inputs[-1], new.inputs[-1])
                    self.assertIs(new.guards[-1], guard)

    def test_invalid_bgr_rejected_without_native_call(self):
        Adapter = make_adapter(heads(2))
        direct.install(Adapter, runtime.yunet_outputs, measured,
                       reference.YuNetCompat, reference.bgr_image)
        adapter = Adapter()
        for image in (np.zeros((32, 32, 3), np.float32), np.zeros((32, 32), np.uint8),
                      np.zeros((0, 32, 3), np.uint8), 'invalid'):
            with self.assertRaises(ValueError):
                adapter.detector.detect(image)
        self.assertEqual(adapter.inputs, [])

    def test_guard_cancellation_propagates_without_result(self):
        Adapter = make_adapter(heads(3))
        direct.install(Adapter, runtime.yunet_outputs, measured,
                       reference.YuNetCompat, reference.bgr_image)
        adapter = Adapter()
        def cancel():
            raise RuntimeError('original admission cancelled')
        adapter._admission_check = cancel
        with self.assertRaisesRegex(RuntimeError, 'original admission cancelled'):
            adapter.detector.detect(np.zeros((480, 640, 3), np.uint8))
        self.assertEqual(adapter.inputs, [])

    def test_non_native_keeps_original_detector(self):
        Adapter = make_adapter(heads(4))
        direct.install(Adapter, runtime.yunet_outputs, measured,
                       reference.YuNetCompat, reference.bgr_image)
        adapter = Adapter(native=False)
        self.assertIsInstance(adapter.detector.net, runtime.YuNetNetwork)
        self.assertNotIn('detect', adapter.detector.__dict__)

    def test_invalid_output_layout_propagates(self):
        Adapter = make_adapter({'bad': np.zeros((1, 1, 1, 1), np.float32)})
        direct.install(Adapter, runtime.yunet_outputs, measured,
                       reference.YuNetCompat, reference.bgr_image)
        with self.assertRaisesRegex(ValueError, 'four unique'):
            Adapter().detector.detect(np.zeros((480, 640, 3), np.uint8))

    def test_skipped_slot_is_not_an_empty_face_result(self):
        sys.path.insert(0, str(BASE.parents[1]))
        Adapter = make_adapter(None)
        direct.install(Adapter, runtime.yunet_outputs, measured,
                       reference.YuNetCompat, reference.bgr_image)
        with self.assertRaisesRegex(RuntimeError, 'skipped'):
            Adapter().detector.detect(np.zeros((480, 640, 3), np.uint8))

    def test_real_adapter_fallback_and_recovery_selection_unchanged(self):
        sys.path.insert(0, str(BASE.parents[1]))
        actual = load('direct_actual_dpu', BASE / 'dpu_yunet.py')
        Adapter = make_adapter(heads(9))
        Adapter.detect = actual.DpuYuNet.detect
        direct.install(Adapter, runtime.yunet_outputs, measured,
                       reference.YuNetCompat, reference.bgr_image)
        adapter = Adapter()
        import threading
        adapter._health_lock = threading.Lock()
        adapter.fallback_calls = adapter.fallback_failures = 0
        adapter.fallback_total_ms = 0.
        fallback_result = np.zeros((1, 15), np.float32)
        with patch.object(adapter, 'fallback', create=True,
                          new=types.SimpleNamespace(detect=lambda image: fallback_result)):
            adapter.schedule = types.SimpleNamespace(disabled=lambda task: True,
                recovery_ready=lambda task: False, optional_status=lambda task: {})
            result = adapter.detect(np.zeros((480, 640, 3), np.uint8))
            self.assertIs(result, fallback_result)
            self.assertEqual(adapter.inputs, [])
            self.assertEqual(adapter.fallback_calls, 1)
            adapter.schedule.recovery_ready = lambda task: True
            adapter.detect(np.zeros((480, 640, 3), np.uint8))
            self.assertEqual(len(adapter.inputs), 1)
            self.assertEqual(adapter.fallback_calls, 1)
            self.assertEqual(adapter.kind, 'DPU_YUNET_INT8')

    def test_direct_stage_ledger_has_no_duplicate_resize_or_float_input(self):
        stage = load('direct_stage_ledger', HERE.parent / 'face_source_v16_candidate/stage_timing.py')
        Adapter = make_adapter(heads(11))
        direct.install(Adapter, runtime.yunet_outputs, stage.measured,
                       reference.YuNetCompat, reference.bgr_image)
        stage._local.record = {'stages': {}}
        try:
            with patch.object(cv2.dnn, 'blobFromImage', side_effect=AssertionError('float round trip')):
                Adapter().detector.detect(np.zeros((480, 640, 3), np.uint8))
            rows = stage._local.record['stages']
            for name in ('compat_resize', 'direct_bgr_encode', 'compat_detect', 'compat_nms', 'fast_network_forward'):
                self.assertEqual(rows[name]['calls'], 1)
            self.assertNotIn('compat_blob', rows)
            self.assertNotIn('fast_input_encode', rows)
        finally:
            stage._local.record = None


if __name__ == '__main__':
    unittest.main()
