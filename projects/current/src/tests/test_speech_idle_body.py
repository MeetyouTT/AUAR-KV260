"""Real idle frames, tracked facial layers, and continuous live recovery."""
from pathlib import Path
import bisect
import sys
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from board.interaction.avatar_player import AvatarPlayer
from board.interaction.avatar_timing import idle_offsets
from tools.demo_script import create_demo_core
from tools.facial_layers import BlinkLayer, MouthBank, warp
from tools.idle_body_compositor import BLINK, eye_centres, mouth_patch, composite_idle_mouth
from tools.realtime_controller import RealtimeController
from tools.realtime_facials import RealtimeFacials
from tools.selected_voice_demo import warm_script_assets


class IdleSpeechTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = create_demo_core('reuse')
        warm_script_assets(cls.core)
        cls.mouths = MouthBank(cls.core)
        cls.eyes = BlinkLayer()

    def setUp(self):
        self.core.idle_gain = 0
        self.core.defer_portrait_offsets = False
        self.core.speech_gain = 1
        self.core.fsm.reset()
        self.core.reset_playback()

    def reference(self):
        player = AvatarPlayer(sprite_root=self.core.sprite_root)
        player.idle_gain = 0
        sequence = self.core.sequence('IDLE')
        player._seq_cache[('IDLE', sequence[3])] = sequence
        player._sop_cache[('IDLE', sequence[3])] = self.core.sop('IDLE')
        return player

    def test_body_is_pixel_identical_to_production_idle_through_state_changes(self):
        reference = self.reference()
        for i in range(301):
            t = i / 30
            state = ('IDLE' if t < 1 else 'SPEAKING_NEUTRAL' if t < 4
                     else 'SPEAKING' if t < 7 else 'SPEAKING_LOW' if t < 9 else 'IDLE')
            meta = self.core.frame_at(state, t)
            expected = reference.frame_at('IDLE', t)
            self.assertEqual(meta['body_asset'], 'idle_normal')
            self.assertAlmostEqual(meta['body_source_position'], expected['source_position'])
            self.assertTrue(np.array_equal(np.asarray(meta['idle_body_image']), np.asarray(expected['image'])))
        self.assertGreater(meta['body_source_position'], 28)

    def test_five_mouth_sets_only_change_the_tracked_mouth_region(self):
        for state, assets in self.core.REUSE_POOLS.items():
            for asset in assets:
                with self.subTest(asset=asset):
                    self.core.reset_playback()
                    self.core._asset_of[state] = asset
                    self.core.frame_at(state, 0)
                    for t in (.25, .7, 1.1, 1.43, 2.75, 4.5):
                        meta = self.core.frame_at(state, t)
                        source = self.mouths.image(asset, 1, 1)
                        body = meta['idle_body_image']
                        image = composite_idle_mouth(body, source, meta['mouth_matrix'], 1)
                        patch, (x, y) = mouth_patch(source, meta['mouth_matrix'], 1)
                        support = np.zeros((body.height, body.width), dtype=bool)
                        support[y:y+patch.height, x:x+patch.width] = np.asarray(patch)[:, :, 3] > 0
                        actual, original = np.asarray(image), np.asarray(body)
                        self.assertTrue(np.array_equal(actual[~support], original[~support]))
                        self.assertTrue(np.array_equal(actual[:, :, 3], original[:, :, 3]))
                        self.assertTrue(np.array_equal(actual[165:], original[165:]))
                        self.assertGreater(np.count_nonzero(actual[:, :, :3] != original[:, :, :3]), 10)
                        self.assertIs(composite_idle_mouth(body, source, meta['mouth_matrix'], 0), body)

    def test_emotional_mouths_are_registered_to_current_idle_face(self):
        track = self.core._idle_body
        profile = self.eyes.profile
        bounds = profile['bounds']
        centres = {name: eye_centres(BLINK / data['layers'][3]['file'], bounds)
                   for name, data in profile['targets'].items() if name in track.to_idle}
        self.core.frame_at('IDLE', 0)
        for t in (.4, 1.43, 3.2):
            meta = self.core.frame_at('IDLE', t)
            face = np.asarray(meta['body_face_matrix'])
            target = np.column_stack((centres['idle_normal'], [1, 1])) @ face.T
            for asset, family in track.FAMILIES.items():
                matrix = np.asarray(track.mouth_matrix(asset, face))
                registered = np.column_stack((centres[family], [1, 1])) @ matrix.T
                self.assertLess(np.max(np.abs(registered-target)), 1e-8, asset)

    def test_live_silence_equals_idle_and_body_keeps_moving(self):
        facials = RealtimeFacials(self.core)
        self.core.idle_gain = 1
        self.core.frame_at('IDLE', 0)
        results = []
        for t in (2, 3):
            meta = self.core.frame_at('SPEAKING_NEUTRAL', t)
            quiet = facials.apply(meta, t, 0, 0)
            loud = facials.apply(meta, t, 1, 1)
            expected = self.eyes.apply(dict(meta, image=meta['idle_body_image']), t, self.core)
            self.assertTrue(np.array_equal(np.asarray(quiet['image']), np.asarray(expected['image'])))
            self.assertTrue(np.array_equal(np.asarray(quiet['image'])[170:], np.asarray(loud['image'])[170:]))
            results.append(np.asarray(quiet['image']))
        self.assertGreater(np.abs(results[0][170:].astype(float)-results[1][170:]).mean(), .1)

    def test_blink_tracks_fractional_idle_pose_and_preserves_alpha_and_mouth(self):
        self.core.defer_portrait_offsets = True
        self.core.frame_at('IDLE', 0)
        for state in self.core.REUSE_POOLS:
            meta = self.core.frame_at(state, 1.43)
            base = composite_idle_mouth(meta['idle_body_image'], self.mouths.image(meta['asset'], 1, 1), meta['mouth_matrix'], 1)
            phase = self.eyes.schedule.phase(1.43)
            times = self.eyes.profile['times']
            left = bisect.bisect_right(times, phase)-1
            right = left+1
            fraction = (phase-times[left])/(times[right]-times[left])
            source = Image.new('RGBA', (464, 480))
            source.paste(Image.blend(self.eyes.images['idle_normal'][left],
                self.eyes.images['idle_normal'][right], fraction), self.eyes.profile['bounds'][:2])
            expected_layer = warp(source, meta['body_face_matrix'])
            expected = Image.alpha_composite(base, expected_layer)
            expected.putalpha(base.getchannel('A'))
            result = self.eyes.apply(dict(meta, image=base), 1.43, self.core)
            actual = np.asarray(result['image'])
            self.assertTrue(result['blink_active'])
            self.assertTrue(np.array_equal(actual, np.asarray(expected)))
            self.assertTrue(np.array_equal(actual[160:], np.asarray(base)[160:]))
            self.assertTrue(np.array_equal(actual[:, :, 3], np.asarray(base)[:, :, 3]))
            self.core.idle_gain = 1
            shifted = self.eyes.apply(dict(meta, image=base), 1.43, self.core)
            self.assertTrue(np.array_equal(np.asarray(shifted['image']),
                np.asarray(self.core._apply_offsets(expected, idle_offsets(1.43)))))
            self.core.idle_gain = 0

    def test_local_eye_warp_matches_original_full_canvas_sampling(self):
        for name, data in self.eyes.profile['targets'].items():
            source = Image.new('RGBA', (464, 480))
            source.paste(self.eyes.images[name][3], self.eyes.profile['bounds'][:2])
            for index in (0, 8, 18, 28, 38):
                matrix = data['poses'][index]['matrix']
                a, b, c = matrix[0]; d, e, f = matrix[1]
                det = a*e-b*d
                inverse = (e/det, -b/det, (b*f-e*c)/det,
                           -d/det, a/det, (d*c-a*f)/det)
                expected = source.transform(source.size, Image.Transform.AFFINE,
                                            inverse, Image.Resampling.BICUBIC)
                self.assertTrue(np.array_equal(np.asarray(warp(source, matrix)), np.asarray(expected)), (name, index))

    def test_body_cursor_survives_pool_rotation_stop_and_replay(self):
        reference = self.reference()
        assets = set()
        for i in range(271):
            t = i / 30
            state = 'IDLE' if i == 0 or t >= 8 else 'SPEAKING_NEUTRAL'
            meta = self.core.display_frame(state, t)
            assets.add(meta['asset'])
            self.assertAlmostEqual(meta['body_source_position'], reference.frame_at('IDLE', t)['source_position'])
        self.assertTrue(set(self.core.REUSE_POOLS['SPEAKING_NEUTRAL']) <= assets)
        self.assertEqual(meta['display_state'], 'IDLE')
        self.core.reset_playback()
        restarted = self.core.frame_at('IDLE', 100)
        self.assertEqual(restarted['body_source_position'], 0)
        self.assertTrue(np.array_equal(np.asarray(restarted['image']), np.asarray(self.core.sequence('IDLE')[0][0])))

    def test_live_pause_and_cancel_preserve_idle_cursor(self):
        clock = [100.0]

        class Jobs:
            root = Path('.')
            def submit(self, *args): return {'id': 'speech'}
            def get(self, key):
                return {'status': 'COMPLETE', 'result': {
                    'key': 'cache', 'sha256': 'fixture', 'cache_hit': True,
                    'duration_seconds': 20, 'envelope': {
                        'hop_seconds': .01, 'gains': [1] * 2000, 'levels': [.8] * 2000}}}
            def cancel(self, key): pass

        class Output:
            active = paused = False
            duration = 20
            def play(self, *args, **kwargs):
                self.active = True; self.start = clock[0]; self.saved = 0
            def stop(self): self.active = False; self.paused = False
            def position(self):
                return self.saved if self.paused else clock[0]-getattr(self, 'start', clock[0])
            def finished(self): return False
            def pause(self, value):
                if value: self.saved = self.position()
                else: self.start = clock[0]-self.saved
                self.paused = value

        output = Output()
        controller = RealtimeController(self.core, Jobs(), output, clock=lambda: clock[0])
        reference = self.reference()
        controller.tick(); reference.frame_at('IDLE', 0)
        controller.submit('Test.'); controller.tick()
        clock[0] += 2
        before = controller.tick()
        controller.toggle_pause(); clock[0] += 20
        paused = controller.tick()
        self.assertEqual(before['body_source_position'], paused['body_source_position'])
        self.assertTrue(np.array_equal(np.asarray(before['image']), np.asarray(paused['image'])))
        controller.toggle_pause(); clock[0] += .1
        resumed = controller.tick()
        self.assertNotEqual(resumed['body_source_position'], paused['body_source_position'])
        controller.cancel()
        for elapsed in (0, .1, .2, .24):
            clock[0] = 122.1 + elapsed
            ended = controller.tick()
            self.assertAlmostEqual(ended['body_source_position'],
                reference.frame_at('IDLE', controller.now())['source_position'])
        self.assertFalse(output.active)
        self.assertEqual(self.core.fsm.state.label, 'IDLE')
        self.assertEqual(ended['display_state'], 'IDLE')
        self.assertEqual(ended['speech_gain'], 0)
        self.assertEqual(self.core.fsm.rejected_count, 0)

    def test_accepted_baseline_keeps_original_fixed_body(self):
        baseline = create_demo_core('reuse', idle_body=False)
        baseline.idle_gain = 0
        baseline.speech_gain = 0
        for state in baseline.REUSE_POOLS:
            for t in (0, .5, 2):
                meta = baseline.frame_at(state, t)
                self.assertNotIn('idle_body_image', meta)
                self.assertTrue(np.array_equal(np.asarray(meta['image']),
                    np.asarray(baseline._reuse_anchors[meta['asset']])))


if __name__ == '__main__':
    unittest.main()
