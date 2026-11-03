"""No extra test dependency: motion, layer registration and live cancellation."""
import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from board.runtime.events import EventType as E
from board.interaction.avatar_timing import idle_offsets
from tools.demo_script import create_demo_core
from tools.facial_layers import BlinkLayer, MouthBank
from tools.realtime_controller import RealtimeController
from tools.realtime_facials import RealtimeFacials
from tools.speech_body_motion import NEUTRAL, SpeechBodyMotion, transform_body


class MotionTests(unittest.TestCase):
    def test_smooth_entry_release_and_pause(self):
        motion = SpeechBodyMotion()
        self.assertEqual(motion.sample(2, active=True), NEUTRAL)
        poses = [motion.sample(2 + i / 30, active=True) for i in range(1, 301)]
        self.assertGreater(max(abs(p.dx) for p in poses), 1)
        self.assertLess(max(abs(p.dx) for p in poses), 2.8)
        self.assertLess(max(abs(p.dy) for p in poses), .91)
        self.assertLess(max(abs(p.tilt_deg) for p in poses), .39)
        before = motion.sample(12, active=True)
        self.assertEqual(motion.sample(12, active=True), before)
        self.assertEqual(motion.sample(12, active=True, releasing=True), before)
        self.assertEqual(motion.sample(12.2, active=True, releasing=True), NEUTRAL)
        self.assertEqual(motion.sample(0, active=True), NEUTRAL)
        self.assertEqual(motion.sample(4, active=False), NEUTRAL)

    def test_pose_is_sampling_independent_and_does_not_restart_at_pool_rotation(self):
        dense, sparse = SpeechBodyMotion(), SpeechBodyMotion()
        dense.sample(0, active=True); sparse.sample(0, active=True)
        for i in range(1, 241):
            pose = dense.sample(i / 30, active=True)
            if i % 30 == 0:
                self.assertEqual(pose, sparse.sample(i / 30, active=True))
        # The pool changes around six seconds; target/phase stays continuous.
        self.assertEqual(dense.start, 0)
        self.assertLess(abs(dense.sample(8 + 1/30, active=True).dx - pose.dx), .12)


class VisualAndLiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = create_demo_core('reuse')
        cls.mouths = MouthBank(cls.core)

    def setUp(self):
        self.core.idle_gain = 1
        self.core.body_motion_enabled = True
        self.core.defer_portrait_offsets = False
        self.core.fsm.reset(); self.core.reset_playback()

    def test_all_five_mouths_move_upper_body_but_preserve_lower_body_and_jaw(self):
        motion = SpeechBodyMotion(); motion.sample(0, active=True)
        first, second = (motion.sample(t, active=True) for t in (2, 4))
        for name in self.mouths.keys:
            anchor = self.core._reuse_anchors[name]
            still = np.asarray(anchor)
            a = np.asarray(transform_body(anchor, first))
            b = np.asarray(transform_body(anchor, second))
            self.assertTrue(np.array_equal(a[300:], still[300:]), name)
            self.assertTrue(np.array_equal(b[300:], still[300:]), name)
            self.assertGreater(np.abs(a[:130].astype(float) - b[:130]).mean(), .2, name)
            opened = np.asarray(transform_body(self.mouths.image(name, 1, 1), first))
            # A moving jaw is valid; a mouth patch changing that jaw is not.
            self.assertTrue(np.array_equal(opened[170:], a[170:]), name)
            self.assertGreater(np.abs(opened[130:170].astype(float) - a[130:170]).mean(), .1, name)

    def test_live_mouth_recomposition_keeps_body_motion_during_quiet_gap(self):
        facials = RealtimeFacials(self.core)
        self.core.frame_at('SPEAKING_NEUTRAL', 0)
        meta = self.core.frame_at('SPEAKING_NEUTRAL', 2)
        quiet = facials.apply(meta, 2, 0, 0)
        loud = facials.apply(meta, 2, 1, 1)
        q, l = np.asarray(quiet['image']), np.asarray(loud['image'])
        self.assertTrue(np.array_equal(q[:125], l[:125]))
        later = facials.apply(self.core.frame_at('SPEAKING_NEUTRAL', 4), 4, 0, 0)
        self.assertGreater(np.abs(q[:125].astype(float) - np.asarray(later['image'])[:125]).mean(), .2)

    def test_eye_overlay_uses_same_pose_and_keeps_mouth_and_jaw(self):
        eyes = BlinkLayer()
        # Use zero global affine motion to isolate the new registration path.
        self.core.idle_gain = 0
        motion = SpeechBodyMotion(); motion.sample(0, active=True)
        pose = motion.sample(1.43, active=True)
        for name in self.mouths.keys:
            base = transform_body(self.mouths.image(name, 1, 1), pose)
            meta = {'image': base, 'asset': name, 'index': 0, 'speech_body_pose': pose}
            result = eyes.apply(meta, 1.43, self.core)
            actual, original = np.asarray(result['image']), np.asarray(base)
            self.assertTrue(result['blink_active'])
            self.assertTrue(np.array_equal(actual[155:], original[155:]), name)
            self.assertTrue(np.array_equal(actual[:, :, 3], original[:, :, 3]), name)
            layer, _ = eyes.overlay(name, 1.43)
            expected = transform_body(layer, pose)
            changed = np.any(actual[:, :, :3] != original[:, :, :3], axis=2)
            self.assertTrue(changed.any(), name)
            self.assertTrue(np.all(np.asarray(expected)[:, :, 3][changed] > 0), name)

        # The actual preview defers breathing too: compose eyes before one warp.
        self.core.idle_gain = 1
        for name in self.mouths.keys:
            raw = self.mouths.image(name, 1, 1)
            meta = {'image': raw, 'asset': name, 'index': 0,
                    'speech_body_pose': pose, 'portrait_offsets_deferred': True}
            result = eyes.apply(meta, 1.43, self.core)
            base = np.asarray(transform_body(raw, pose, offsets=idle_offsets(1.43)))
            actual = np.asarray(result['image'])
            self.assertFalse(result['portrait_offsets_deferred'])
            self.assertTrue(np.array_equal(actual[155:], base[155:]), name)
            self.assertTrue(np.array_equal(actual[:, :, 3], base[:, :, 3]), name)

    def test_live_pause_freezes_body_and_cancel_finishes_recovery(self):
        clock = [100.0]
        core = self.core

        class Jobs:
            root = Path('.')
            def submit(self, *args):
                return {'id': 'speech'}
            def get(self, key):
                return {'status': 'COMPLETE', 'result': {
                    'key': 'cache', 'sha256': 'fixture', 'cache_hit': True,
                    'duration_seconds': 20, 'envelope': {
                        'hop_seconds': .01, 'gains': [1] * 2000,
                        'levels': [.8] * 2000}}}
            def cancel(self, key): pass

        class Output:
            active = paused = False
            duration = 20
            def play(self, *args, **kwargs):
                self.active = True; self.start = clock[0]; self.saved = 0
            def stop(self): self.active = False; self.paused = False
            def position(self):
                return self.saved if self.paused else clock[0] - getattr(self, 'start', clock[0])
            def finished(self): return False
            def pause(self, value):
                if value: self.saved = self.position()
                else: self.start = clock[0] - self.saved
                self.paused = value

        output = Output()
        controller = RealtimeController(core, Jobs(), output, clock=lambda: clock[0])
        controller.tick(); controller.submit('Test.'); controller.tick()
        clock[0] += 2; before = controller.tick()
        controller.toggle_pause(); clock[0] += 20; paused = controller.tick()
        self.assertEqual(before['speech_body_pose'], paused['speech_body_pose'])
        self.assertTrue(np.array_equal(np.asarray(before['image']), np.asarray(paused['image'])))
        controller.toggle_pause(); clock[0] += .1; resumed = controller.tick()
        self.assertNotEqual(resumed['speech_body_pose'], paused['speech_body_pose'])
        controller.cancel(); controller.tick()
        clock[0] += .2; ended = controller.tick()
        self.assertFalse(output.active)
        self.assertEqual(ended['speech_body_pose'], NEUTRAL)
        self.assertEqual(core.fsm.state.label, 'IDLE')

    def test_historical_baseline_switch_and_reset_disable_extra_motion(self):
        self.core.body_motion_enabled = False
        for t in (0, 1, 4):
            self.assertEqual(self.core.frame_at('SPEAKING_NEUTRAL', t)['speech_body_pose'], NEUTRAL)
        self.core.body_motion_enabled = True
        self.core.reset_playback()
        self.assertEqual(self.core.frame_at('SPEAKING_NEUTRAL', 4)['speech_body_pose'], NEUTRAL)
        self.assertNotEqual(self.core.frame_at('SPEAKING_NEUTRAL', 5)['speech_body_pose'], NEUTRAL)


if __name__ == '__main__':
    unittest.main()
