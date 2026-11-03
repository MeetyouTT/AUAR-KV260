"""Meaningful regression checks for output ordering, quantization and expiry."""
import unittest
from unittest.mock import patch
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import cv2
import numpy as np
from dpu_vision_runtime import encode, yunet_outputs, YuNetNetwork, SlotUnavailable, PinnedRunner, tensor_meta
from reconstruct_yunet import cpu_outputs


class RuntimeTests(unittest.TestCase):
    def test_buffers_follow_vart_ports_when_xir_order_differs(self):
        class Tensor:
            dtype = 'xint8'
            def __init__(self, name, dims, fix):
                self.name, self.dims, self.fix = name, dims, fix
            def has_attr(self, key):
                return key == 'fix_point'
            def get_attr(self, key):
                assert key == 'fix_point'
                return self.fix
        source = Tensor('input', [1, 2, 2, 3], 7)
        small = Tensor('small', [1, 1, 1, 3], 3)
        large = Tensor('large', [1, 4, 4, 3], 4)
        class FakeRunner:
            def get_input_tensors(self):
                return [source]
            def get_output_tensors(self):
                return [large, small]
            def execute_async(self, inputs, outputs):
                for i, (buffer, tensor) in enumerate(zip(outputs, self.get_output_tensors())):
                    # The previous bug put a 3-byte array at the 48-byte port.
                    self_test.assertEqual(list(buffer.shape), tensor.dims)
                    buffer.fill(16 + i)
                return (1, 0)
            def wait(self, job):
                return 0
        self_test = self
        sub = SimpleNamespace(has_attr=lambda k: k in ('device', 'dpu_fingerprint'),
            get_attr=lambda k: 'DPU' if k == 'device' else int('101000056010407', 16),
            get_input_tensors=lambda: [source], get_output_tensors=lambda: [small, large])
        graph = SimpleNamespace(get_root_subgraph=lambda: SimpleNamespace(toposort_child_subgraph=lambda: [sub]))
        modules = {'xir': SimpleNamespace(Graph=SimpleNamespace(deserialize=lambda _: graph)),
                   'vart': SimpleNamespace(Runner=SimpleNamespace(create_runner=lambda *_: FakeRunner()))}
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryFile() as lock:
            root = Path(directory)
            model = root / 'model.xmodel'
            model.write_bytes(b'fixture')
            manifest = {'sha256': hashlib.sha256(b'fixture').hexdigest(),
                'partitions': [{'device': 'DPU', 'fingerprint': '0x101000056010407',
                    'inputs': [tensor_meta(source)], 'outputs': [tensor_meta(small), tensor_meta(large)]}]}
            (root / 'manifest.json').write_text(json.dumps(manifest))
            with patch.dict(sys.modules, modules):
                runner = PinnedRunner(model, root / 'manifest.json',
                    SimpleNamespace(fingerprint='0x101000056010407', ownership=lock))
                result = runner.execute(np.zeros(source.dims, np.float32))
                self.assertTrue(np.all(result['large'] == 1.))
                self.assertTrue(np.all(result['small'] == 17 / 8))
                runner.close()

    def test_shuffled_heads_match_original_onnx_layout(self):
        rng = np.random.RandomState(42)
        shapes = [(1, 40, 40, 51), (1, 20, 20, 34), (1, 10, 10, 34), (1, 5, 5, 51)]
        heads = [rng.normal(size=s).astype(np.float32) for s in shapes]
        reference = cpu_outputs([x.transpose(0, 3, 1, 2) for x in heads])
        actual = yunet_outputs({str(i): heads[i] for i in (3, 0, 2, 1)})
        for a, b in zip(actual, reference):
            np.testing.assert_array_equal(a, b)

    def test_wrong_head_geometry_rejected(self):
        with self.assertRaises(ValueError):
            yunet_outputs({'x': np.zeros((1, 40, 40, 51), np.float32)})

    def test_fixpoint_rounding_and_saturation(self):
        data = np.array([-2, -1, -127.5 / 128, 0, .5 / 128, 127.5 / 128, 2], np.float32)
        np.testing.assert_array_equal(encode(data, 7), [-128, -128, -127, 0, 1, 127, 127])
        with self.assertRaises(ValueError):
            encode([np.nan], 7)

    def test_skipped_slot_is_not_a_missing_face_observation(self):
        net = YuNetNetwork(None, lambda _: None)
        net.setInput(cv2.dnn.blobFromImage(np.zeros((320, 320, 3), np.uint8)))
        with self.assertRaises(SlotUnavailable):
            net.forward(['loc', 'conf', 'iou'])


if __name__ == '__main__':
    unittest.main()
