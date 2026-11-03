"""Independent synthetic behavior checks; no assets, native library or devices."""
import os
import ctypes as C
from collections import OrderedDict
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SHARED = Path(os.environ.get('AURA_SHARED_SOURCE', '/home/ghmd/Win共享文件/语音共享文件/aura'))
sys.path[:0] = [str(ROOT/'candidate/aura'), str(ROOT/'baseline/aura'), str(SHARED)]
import tools
tools.__path__[:0] = [str(ROOT/'candidate/aura/tools'), str(ROOT/'baseline/aura/tools')]
import board.interaction
board.interaction.__path__.insert(0, str(ROOT/'baseline/aura/board/interaction'))

import numpy as np
from PIL import Image
from tools.facial_layers import BlinkLayer
from tools.idle_body_compositor import IdleBodyTrack
from tools.realtime_facials import RealtimeFacials
from tools.native_pixels import NativePixels
import tools.realtime_facials as facials_module


class FakeNative:
    def __init__(self):
        self.lazy_calls = self.materialized_calls = self.materialize_calls = 0
        self.exact_calls = 0
        self.pose_received_lazy = []
        self.pose_received_exact = []

    def blend(self, first, second, alpha):
        self.lazy_calls += 1
        proxy = first._new(first.im)
        proxy._native_blend = (first, second, alpha)
        return proxy

    def materialize_blend(self, first, second, alpha):
        self.materialized_calls += 1
        return Image.blend(first, second, alpha)

    def blend_exact(self, first, second, alpha):
        self.exact_calls += 1
        if alpha <= 0:
            return first
        if alpha >= 1:
            return second
        proxy = self.blend(first, second, alpha)
        proxy._native_blend_exact = True
        return proxy

    def materialize(self, image):
        self.materialize_calls += 1
        value = getattr(image, '_native_blend', None)
        return Image.blend(*value) if value is not None else image

    def pose(self, image, offsets):
        self.pose_received_lazy.append(hasattr(image, '_native_blend'))
        self.pose_received_exact.append(getattr(image, '_native_blend_exact', False))
        return self.materialize(image).convert('RGB')


class FakeBody:
    def __init__(self, native):
        self.native = native
        self.first = Image.new('RGBA', (12, 10), (20, 40, 60, 255))
        self.second = Image.new('RGBA', (12, 10), (100, 120, 140, 255))
        self.calls = []

    def sample(self, now, *, defer_blend=False):
        self.calls.append(defer_blend)
        image = (self.native.blend_exact(self.first, self.second, .25) if defer_blend else
                 self.native.materialize_blend(self.first, self.second, .25))
        return {'image': image, 'asset': 'idle-body', 'index': 7, 'source_position': 7.25}, np.eye(2, 3)

    def mouth_matrix(self, *args):
        return [[1., 0., 0.], [0., 1., 0.]]


class SelectionTests(unittest.TestCase):
    def facials(self, *, deferred=True, gain=1., native_present=True, blink=False):
        native = FakeNative()
        core = SimpleNamespace(defer_portrait_offsets=deferred, idle_gain=gain,
                               _apply_offsets=native.pose, native_pixels=native if native_present else None)
        body = FakeBody(native)
        eyes = BlinkLayer.__new__(BlinkLayer)
        eyelid = Image.new('RGBA', (12, 10), (0, 0, 0, 0))
        if blink:
            eyelid.putpixel((3, 4), (8, 9, 10, 255))
        eyes.overlay = lambda *args, **kwargs: (eyelid, .12) if blink else (None, None)
        value = RealtimeFacials.__new__(RealtimeFacials)
        value.core, value.body, value.eyes = core, body, eyes
        value.mouths = SimpleNamespace(keys={'mouth-asset'}, image=Mock(return_value=eyelid))
        value.last_gain = value.last_level = 0.
        value.last_asset = None
        return value, body, native

    def meta(self, state='IDLE', asset='idle-asset'):
        return {'asset': asset, 'display_state': state, 'image': Image.new('RGBA', (12, 10)),
                'index': 2, 'source_position': 2.5, 'transitioning': True}

    def test_only_native_idle_with_deferred_final_pose_uses_lazy_body(self):
        value, body, native = self.facials()
        result = value.apply(self.meta(), 1., 0., 0.)
        self.assertEqual(body.calls, [True])
        self.assertEqual(native.pose_received_lazy, [True])
        self.assertEqual(native.pose_received_exact, [True])
        self.assertEqual(result['image'].mode, 'RGB')
        self.assertEqual(result['image'].getpixel((0, 0)), (40, 60, 80))

    def test_effects_off_never_returns_unmaterialized_body_to_plain_pil_consumers(self):
        value, body, native = self.facials(gain=0.)
        result = value.apply(self.meta(), 1., 0., 0.)
        self.assertEqual(body.calls, [False])
        self.assertFalse(hasattr(result['image'], '_native_blend'))
        self.assertEqual(native.pose_received_lazy, [])

    def test_non_deferred_offset_path_preserves_materialization(self):
        value, body, native = self.facials(deferred=False)
        result = value.apply(self.meta(), 1., 0., 0.)
        self.assertEqual(body.calls, [False])
        self.assertFalse(hasattr(result['image'], '_native_blend'))

    def test_non_native_path_preserves_materialization(self):
        value, body, native = self.facials(native_present=False)
        result = value.apply(self.meta(), 1., 0., 0.)
        self.assertEqual(body.calls, [False])
        self.assertFalse(hasattr(result['image'], '_native_blend'))

    def test_speaking_and_mouth_assets_never_send_lazy_body_to_mouth_composite(self):
        for state in ('SPEAKING', 'SPEAKING_NEUTRAL', 'IDLE'):
            for gain in (0., .8):
                with self.subTest(state=state, gain=gain):
                    value, body, native = self.facials()
                    def composite(image, *args):
                        self.assertFalse(hasattr(image, '_native_blend'))
                        return image
                    with patch.object(facials_module, 'composite_idle_mouth', side_effect=composite) as merged:
                        value.apply(self.meta(state, 'mouth-asset'), 1., gain, .7)
                    self.assertEqual(body.calls, [False])
                    merged.assert_called_once()

    def test_other_states_do_not_sample_idle_body_or_change_metadata(self):
        for state in ('LISTENING', 'THINKING', 'ACK_NOD', 'DENY_SHAKE', 'AWAKE', 'PUZZLED'):
            with self.subTest(state=state):
                value, body, native = self.facials()
                meta = self.meta(state, 'action-asset')
                result = value.apply(meta, 1., 0., 0.)
                self.assertEqual(body.calls, [])
                self.assertEqual(result['asset'], meta['asset'])
                self.assertEqual(result['index'], meta['index'])
                self.assertEqual(result['source_position'], meta['source_position'])
                self.assertTrue(result['transitioning'])

    def test_existing_blink_layer_materializes_lazy_body_before_alpha_composite(self):
        value, body, native = self.facials(blink=True)
        original_first = body.first.tobytes()
        original_second = body.second.tobytes()
        result = value.apply(self.meta(), 1., 0., 0.)
        self.assertEqual(body.calls, [True])
        self.assertTrue(result['blink_active'])
        # This is the real BlinkLayer.apply body; it must hand a real composite to pose.
        self.assertEqual(native.pose_received_lazy, [False])
        self.assertEqual(native.pose_received_exact, [False])
        self.assertEqual(result['image'].getpixel((3, 4)), (8, 9, 10))
        self.assertEqual(result['image'].getpixel((0, 0)), (40, 60, 80))
        self.assertEqual(body.first.tobytes(), original_first)
        self.assertEqual(body.second.tobytes(), original_second)

    def test_body_replacement_preserves_tracking_and_core_metadata(self):
        value, body, native = self.facials()
        original = self.meta()
        result = value.apply(original, 1., 0., 0.)
        self.assertEqual(result['index'], original['index'])
        self.assertEqual(result['source_position'], original['source_position'])
        self.assertEqual(result['body_asset'], 'idle-body')
        self.assertEqual(result['body_index'], 7)
        self.assertEqual(result['body_source_position'], 7.25)
        self.assertTrue(np.array_equal(result['body_face_matrix'], np.eye(2, 3)))
        self.assertNotIn('body_asset', original)


class BodySamplingTests(unittest.TestCase):
    def track(self, native=True):
        instance = IdleBodyTrack.__new__(IdleBodyTrack)
        pixels = FakeNative()
        instance.core = SimpleNamespace(native_pixels=pixels if native else None)
        instance.poses = [{'matrix': [[1., 0., 0.], [0., 1., 0.]]},
                          {'matrix': [[1., 0., 2.], [0., 1., 4.]]}]
        first, second = Image.new('RGBA', (2, 2), (20, 40, 60, 255)), Image.new('RGBA', (2, 2), (100, 120, 140, 255))
        player = SimpleNamespace(_seq_cache={'fixture': True}, blend_frames=Image.blend)
        player.frame_at = lambda *args: {'image': player.blend_frames(first, second, .25), 'source_position': .25}
        instance.player = player
        return instance, pixels

    def test_default_sample_remains_materialized(self):
        track, pixels = self.track()
        meta, matrix = track.sample(1.)
        self.assertEqual(pixels.materialized_calls, 1)
        self.assertEqual(pixels.lazy_calls, 0)
        self.assertFalse(hasattr(meta['image'], '_native_blend'))
        self.assertTrue(np.array_equal(matrix, [[1., 0., .5], [0., 1., 1.]]))

    def test_explicit_defer_and_next_default_call_select_their_own_blend_mode(self):
        track, pixels = self.track()
        lazy, first_matrix = track.sample(1., defer_blend=True)
        materialized, second_matrix = track.sample(2.)
        self.assertTrue(hasattr(lazy['image'], '_native_blend'))
        self.assertTrue(lazy['image']._native_blend_exact)
        self.assertFalse(hasattr(materialized['image'], '_native_blend'))
        self.assertEqual((pixels.lazy_calls, pixels.materialized_calls), (1, 1))
        self.assertEqual(pixels.exact_calls, 1)
        self.assertTrue(np.array_equal(first_matrix, second_matrix))

    def test_non_native_defer_request_still_uses_existing_real_pixel_blend(self):
        track, pixels = self.track(native=False)
        meta, _ = track.sample(1., defer_blend=True)
        self.assertFalse(hasattr(meta['image'], '_native_blend'))
        self.assertEqual(meta['image'].getpixel((0, 0)), (40, 60, 80, 255))
        self.assertEqual(pixels.lazy_calls, 0)


class NativeDispatchTests(unittest.TestCase):
    """Exercise actual candidate NativePixels methods with an in-memory fake C ABI."""
    def setUp(self):
        self.first = Image.new('RGBA', (2, 2), (20, 40, 60, 255))
        self.second = Image.new('RGBA', (2, 2), (100, 120, 140, 255))
        native = NativePixels.__new__(NativePixels)
        native.owner = 1
        native.size = (2, 2)
        native.background = (255, 255, 255)
        native.inputs = OrderedDict()
        native.cached_bytes = 0
        native.limit = 4096
        native.output = C.create_string_buffer(12)
        self.native = native
        def write_output(color):
            def execute(*arguments):
                C.memmove(arguments[-1], bytes(color) * 4, 12)
                return 0
            return execute
        def materialize(first, second, output, count, alpha):
            mixed = bytes(int(a + alpha * (b - a)) for a, b in zip(first, second))
            C.memmove(output, mixed, count)
            return 0
        native.lib = SimpleNamespace(
            aura_pose=Mock(side_effect=write_output((9, 10, 11))),
            aura_pose_blend=Mock(side_effect=write_output((3, 4, 5))),
            aura_pose_blend_exact=Mock(side_effect=write_output((6, 7, 8))),
            aura_blend=Mock(side_effect=materialize))
        self.offsets = SimpleNamespace(tilt_deg=0., scale_y=1., dx=0., dy=0.)

    def test_new_exact_proxy_only_marks_its_own_wrapper_and_routes_exact_api(self):
        before = self.first.tobytes(), self.second.tobytes()
        proxy = self.native.blend_exact(self.first, self.second, .25)
        self.assertIsNot(proxy, self.first)
        self.assertEqual(proxy._native_blend, (self.first, self.second, .25))
        self.assertTrue(proxy._native_blend_exact)
        self.assertFalse(hasattr(self.first, '_native_blend_exact'))
        self.assertFalse(hasattr(self.second, '_native_blend_exact'))
        image = self.native.pose(proxy, self.offsets)
        self.native.lib.aura_pose_blend_exact.assert_called_once()
        self.native.lib.aura_pose_blend.assert_not_called()
        self.native.lib.aura_pose.assert_not_called()
        self.assertEqual(image.getpixel((0, 0)), (6, 7, 8))
        self.assertEqual((self.first.tobytes(), self.second.tobytes()), before)

    def test_ordinary_blend_still_routes_legacy_api_after_an_exact_blend(self):
        self.native.blend_exact(self.first, self.second, .25)
        proxy = self.native.blend(self.first, self.second, .25)
        self.assertFalse(hasattr(proxy, '_native_blend_exact'))
        image = self.native.pose(proxy, self.offsets)
        self.native.lib.aura_pose_blend.assert_called_once()
        self.native.lib.aura_pose_blend_exact.assert_not_called()
        self.assertEqual(image.getpixel((0, 0)), (3, 4, 5))

    def test_materializing_exact_proxy_removes_flag_and_pose_uses_plain_api(self):
        proxy = self.native.blend_exact(self.first, self.second, .25)
        materialized = self.native.materialize(proxy)
        self.assertFalse(hasattr(materialized, '_native_blend'))
        self.assertFalse(hasattr(materialized, '_native_blend_exact'))
        self.assertTrue(proxy._native_blend_exact)
        self.assertEqual(materialized.getpixel((0, 0)), (40, 60, 80, 255))
        image = self.native.pose(materialized, self.offsets)
        self.native.lib.aura_blend.assert_called_once()
        self.native.lib.aura_pose.assert_called_once()
        self.native.lib.aura_pose_blend_exact.assert_not_called()
        self.assertEqual(image.getpixel((0, 0)), (9, 10, 11))

    def test_endpoints_return_plain_original_without_custom_attributes(self):
        before = dict(self.first.__dict__), dict(self.second.__dict__)
        self.assertIs(self.native.blend_exact(self.first, self.second, 0.), self.first)
        self.assertIs(self.native.blend_exact(self.first, self.second, 1.), self.second)
        self.assertEqual((self.first.__dict__, self.second.__dict__), before)

    def test_endpoints_do_not_convert_existing_legacy_proxy_into_exact_proxy(self):
        legacy = self.native.blend(self.first, self.second, .25)
        for alpha, first, second in ((0., legacy, self.second), (1., self.first, legacy)):
            with self.subTest(alpha=alpha):
                before = dict(legacy.__dict__)
                self.assertIs(self.native.blend_exact(first, second, alpha), legacy)
                self.assertEqual(legacy.__dict__, before)
                self.assertFalse(getattr(legacy, '_native_blend_exact', False))

    def test_nested_blends_materialize_without_tagging_original_exact_proxy(self):
        first = self.native.blend_exact(self.first, self.second, .25)
        before = dict(first.__dict__)
        nested = self.native.blend_exact(first, self.second, .5)
        self.assertEqual(first.__dict__, before)
        self.assertFalse(hasattr(nested, '_native_blend'))
        self.assertFalse(hasattr(nested, '_native_blend_exact'))
        self.assertEqual(nested.getpixel((0, 0)), (70, 90, 110, 255))

    def test_blink_materializes_exact_proxy_before_plain_pose(self):
        proxy = self.native.blend_exact(self.first, self.second, .25)
        eyes = BlinkLayer.__new__(BlinkLayer)
        overlay = Image.new('RGBA', (2, 2))
        overlay.putpixel((0, 0), (8, 9, 10, 255))
        eyes.overlay = lambda *args, **kwargs: (overlay, .12)
        core = SimpleNamespace(native_pixels=self.native, idle_gain=1., _apply_offsets=self.native.pose)
        meta = {'asset': 'idle', 'image': proxy, 'portrait_offsets_deferred': True}
        result = eyes.apply(meta, 1.4, core)
        self.assertTrue(result['blink_active'])
        self.native.lib.aura_blend.assert_called_once()
        self.native.lib.aura_pose.assert_called_once()
        self.native.lib.aura_pose_blend_exact.assert_not_called()
        self.assertFalse(hasattr(result['image'], '_native_blend_exact'))


if __name__ == '__main__':
    unittest.main()
