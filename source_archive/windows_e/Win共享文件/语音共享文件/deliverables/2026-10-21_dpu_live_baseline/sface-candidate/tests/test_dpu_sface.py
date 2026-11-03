"""Synthetic aligned pixels; numerical/slot contracts, without VART hardware."""
import bootstrap
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from board.identity.deferred import DeferredIdentity
from board.identity.model_store import MODEL_ID, MODEL_SHA256, WINDOWS_MODEL_ID, check_artifact_configuration
from board.vision.dpu_sface import DpuSFace
from board.vision.dpu_vision_runtime import PinnedRunner


class Tensor:
    def __init__(self, name, dims, fix):self.name, self.dims, self.fix = name, dims, fix
    def get_attr(self, name):
        assert name == 'fix_point'
        return self.fix


class Schedule:
    def __init__(self):
        self.active = False
        self.allow = True
        self.is_disabled = False
        self.admitted = self.finished = 0
        self.on_enter = None
    def disabled(self, kind):
        assert kind == 'sface'
        return self.is_disabled
    @contextmanager
    def optional(self, kind):
        assert kind == 'sface'
        if self.on_enter:self.on_enter()
        self.active = self.allow
        self.admitted += 1
        try:yield self.allow
        finally:
            self.active = False
            self.finished += 1


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.schedule = Schedule()
        self.adapter = DpuSFace.__new__(DpuSFace)
        self.adapter.schedule, self.adapter.clock = self.schedule, lambda:self.now
        self.adapter.source_ttl = 500
        self.adapter.requests = self.adapter.execution_attempts = self.adapter.completed = self.adapter.features_returned = 0
        self.adapter.deferred = self.adapter.slot_denials = self.adapter.expired_after_admission = 0
        self.source = None
        self.calls = 0
        self.post_callback = None
        self.lock = tempfile.TemporaryFile()
        self.addCleanup(self.lock.close)
        runner = PinnedRunner.__new__(PinnedRunner)
        runner.owner = SimpleNamespace(ownership=self.lock)
        runner.input_fix = 7
        runner.inputs = [Tensor('input', [1, 112, 112, 3], 7)]
        runner.outputs = [Tensor('output', [1, 128], 5)]
        def execute(inputs, outputs):
            self.assertTrue(self.schedule.active)
            self.source = inputs[0].copy()
            self.calls += 1
            outputs[0].fill(32)
            return (1, 0)
        def wait(job):
            self.assertEqual(job, (1, 0))
            self.assertTrue(self.schedule.active)
            if self.post_callback:self.post_callback()
            return 0
        runner.runner = SimpleNamespace(execute_async=execute, wait=wait)
        runner.last_ms = None
        self.adapter.runner = runner
        self.crop = np.zeros((112, 112, 3), np.uint8)
        self.crop[:] = [0, 128, 255]

    def test_rgb_normalization_and_quantization_match_pinned_contract(self):
        feature = self.adapter.feature(self.crop, source_mono_ms=1000)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.source.shape, (1, 112, 112, 3))
        np.testing.assert_array_equal(self.source[0, 0, 0], [127, 1, -127])
        np.testing.assert_array_equal(feature, np.ones(128, np.float32))
        self.assertFalse(self.schedule.active)

    def test_encode_allocation_and_dequantization_are_outside_dpu_slot(self):
        original_empty = np.empty
        schedule, test = self.schedule, self
        class TracedArray(np.ndarray):
            def astype(self, *args, **kwargs):
                test.assertFalse(schedule.active)
                return super().astype(*args, **kwargs)
        def empty(*args, **kwargs):
            self.assertFalse(self.schedule.active)
            return original_empty(*args, **kwargs).view(TracedArray)
        from board.vision.dpu_vision_runtime import encode
        def encode_outside(*args, **kwargs):
            self.assertFalse(self.schedule.active)
            return encode(*args, **kwargs)
        with patch('board.vision.dpu_sface.encode', encode_outside), patch('numpy.empty', empty):
            self.adapter.feature(self.crop, source_mono_ms=1000)

    def test_busy_and_disabled_slots_never_submit(self):
        self.schedule.allow = False
        with self.assertRaises(DeferredIdentity):self.adapter.feature(self.crop, source_mono_ms=1000)
        self.assertEqual(self.calls, 0)
        self.schedule.is_disabled = True
        self.schedule.allow = True
        with self.assertRaises(DeferredIdentity):self.adapter.feature(self.crop, source_mono_ms=1000)
        self.assertEqual(self.calls, 0)

    def test_expiry_before_submit_and_after_wait_is_rejected(self):
        self.now = 1500
        with self.assertRaises(DeferredIdentity):self.adapter.feature(self.crop, source_mono_ms=1000)
        self.assertEqual(self.calls, 0)
        self.now = 1000
        self.schedule.on_enter = lambda:setattr(self, 'now', 1500)
        with self.assertRaises(DeferredIdentity):self.adapter.feature(self.crop, source_mono_ms=1000)
        self.assertEqual(self.calls, 0)
        self.assertFalse(self.schedule.active)
        self.assertEqual(self.adapter.health()['expired_after_admission'], 1)
        self.assertEqual(self.adapter.health()['execution_attempts'], 0)
        self.assertEqual(self.adapter.health()['completed'], 0)
        self.now = 1000
        self.schedule.on_enter = None
        self.post_callback = lambda:setattr(self, 'now', 1500)
        with self.assertRaises(DeferredIdentity):self.adapter.feature(self.crop, source_mono_ms=1000)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.adapter.health()['completed'], 1)
        self.assertEqual(self.adapter.health()['features_returned'], 0)

    def test_unaligned_or_wrong_dtype_crop_never_submits(self):
        for crop in (np.zeros((111,112,3),np.uint8), self.crop.astype(np.float32)):
            with self.assertRaises(ValueError):self.adapter.feature(crop, source_mono_ms=1000)
        self.assertEqual(self.calls, 0)


class ArtifactContractTests(unittest.TestCase):
    def test_configuration_check_reads_actual_artifacts_without_runner_or_database_creation(self):
        previous = Path(os.environ['AURA_PREVIOUS_DELIVERABLE'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fallback = root/'windows.json'
            fallback.write_text(json.dumps({'schema_version':'aura-camera-identity-1',
                'model_id':WINDOWS_MODEL_ID, 'database':str(root/'windows.sqlite3'),
                'feature_backend':{'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}}))
            model = previous/'artifacts/sface/sface_public_int8.xmodel'
            manifest = previous/'artifacts/sface/compiler-manifest.json'
            config = {'model_id':MODEL_ID, 'database':str(root/(MODEL_ID+'.sqlite3')), 'result_ttl_ms':1500,
                'feature_backend':{'kind':'dpu_sface', 'model':str(model),'manifest':str(manifest),
                    'model_sha256':MODEL_SHA256, 'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
                    'fallback_config':str(fallback),'max_source_age_ms':500}}
            with patch('board.vision.dpu_sface.PinnedRunner', side_effect=AssertionError('runner created')):
                result = check_artifact_configuration(config)
            self.assertEqual(result['status'], 'CONFIG_VALIDATED_NOT_RUNTIME_TESTED')
            self.assertFalse(result['runner_created'])
            self.assertFalse(Path(config['database']).exists())
            self.assertFalse((root/'windows.sqlite3').exists())

    def test_actual_compiled_hash_and_malformed_tensor_are_checked(self):
        previous = Path(os.environ['AURA_PREVIOUS_DELIVERABLE'])
        model = previous/'artifacts/sface/sface_public_int8.xmodel'
        manifest = previous/'artifacts/sface/compiler-manifest.json'
        config = {'model_id':MODEL_ID, 'feature_backend':{'model':str(model),'manifest':str(manifest),
            'model_sha256':MODEL_SHA256, 'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'max_source_age_ms':500}}
        good = SimpleNamespace(input_fix=7, inputs=[Tensor('input',[1,112,112,3],7)],
            outputs=[Tensor('output',[1,128],5)], close=lambda:None)
        with patch('board.vision.dpu_sface.PinnedRunner', return_value=good):
            adapter = DpuSFace(config, Schedule(), object(), lambda:1000)
            self.assertEqual(adapter.model_id, MODEL_ID)
        good.outputs[0].fix = 4
        with patch('board.vision.dpu_sface.PinnedRunner', return_value=good):
            with self.assertRaises(ValueError):DpuSFace(config, Schedule(), object(), lambda:1000)
        config['feature_backend']['model_sha256'] = '0'*64
        with self.assertRaises(ValueError):DpuSFace(config, Schedule(), object(), lambda:1000)

    def test_camera_extractor_selects_local_dpu_without_fp32_network(self):
        from board.identity.camera_faces import CameraFaceExtractor
        from board.vision.reference_faces import SFaceCompat
        schedule, owner, clock = object(), object(), lambda:1000
        embedder = SimpleNamespace(feature=lambda *_args, **_kwargs:np.ones(128,np.float32), close=lambda:None)
        config = {'feature_backend':{'kind':'dpu_sface'}, 'minimum_face_pixels':48,
            'minimum_face_score':.9, 'minimum_blur_variance':0}
        key = {'camera_epoch':'epoch', 'track_id':1, 'track_generation':1}
        face = [0,0,112,112,38.2946,51.6963,73.5318,51.5014,56.0252,71.7366,
                41.5493,92.3655,70.7299,92.2041,.99]
        with patch('board.vision.dpu_sface.DpuSFace', return_value=embedder) as factory, \
                patch.object(SFaceCompat, '__init__', side_effect=AssertionError('FP32 network loaded')):
            extractor = CameraFaceExtractor(config, face_targets=True, schedule=schedule, owner=owner, clock=clock)
            result, reason = extractor.extract(np.zeros((112,112,3),np.uint8),
                {'target_kind':'face','face':face,'face_target':key,'captured_mono_ms':1000}, key)
            self.assertEqual(result.shape, (128,))
            self.assertEqual(reason, '')
            factory.assert_called_once_with(config,schedule,owner,clock)
            extractor.close()


if __name__ == '__main__':unittest.main()
