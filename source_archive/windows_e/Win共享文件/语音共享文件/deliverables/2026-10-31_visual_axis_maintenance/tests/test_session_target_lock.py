"""Adversarial anonymous-face continuity checks, using only fake registers."""
import copy
import unittest
from test_wide_range import wide_scene


def other_target(scene, center=.86, **changes):
    packet = scene.packet(center)
    packet['target'].update(changes)
    return packet


class SessionTargetLockTests(unittest.TestCase):
    def test_target_change_cannot_rearm_after_controller_reset(self):
        f = wide_scene()
        f.feed([.86] * 4)
        before, arms = len(f.device.commands), f.device.arms
        finishes = f.device.finishes
        for _ in range(8):
            f.session.step(other_target(f, track_id=2))
            f.tick()
        self.assertEqual(len(f.device.commands), before)
        self.assertEqual(f.device.arms, arms)
        self.assertTrue(f.session.fatal)
        self.assertEqual(f.device.status()['flags'], 0)
        self.assertGreater(f.device.finishes, finishes)

    def test_loss_then_replacement_stays_stopped(self):
        f = wide_scene()
        f.feed([.86] * 4)
        f.session.step(f.packet(state='NO_TARGET'))
        before, arms = len(f.device.commands), f.device.arms
        for _ in range(8):
            f.session.step(other_target(f, track_id=2))
            f.tick()
        self.assertEqual((len(f.device.commands), f.device.arms), (before, arms))
        self.assertTrue(f.session.fatal)

    def test_same_track_new_generation_requires_new_session(self):
        f = wide_scene()
        f.feed([.86] * 4)
        f.session.step(f.packet(state='NO_TARGET'))
        before = len(f.device.commands)
        for _ in range(8):
            f.session.step(other_target(f, track_generation=2))
            f.tick()
        self.assertEqual(len(f.device.commands), before)
        self.assertTrue(f.session.fatal)

    def test_camera_and_service_changes_remain_latched_across_loss(self):
        for changes in (dict(camera_epoch='replacement'), dict(service_epoch='replacement')):
            with self.subTest(changes=changes):
                f = wide_scene()
                f.feed([.86] * 4)
                f.session.step(f.packet(state='NO_TARGET'))
                before = len(f.device.commands)
                for _ in range(8):
                    f.session.step(f.packet(.86, **changes))
                    f.tick()
                self.assertEqual(len(f.device.commands), before)
                self.assertTrue(f.session.fatal)

    def test_same_live_target_reconfirms_new_frames_after_short_loss(self):
        f = wide_scene()
        f.feed([.86] * 4)
        f.session.step(f.packet(state='NO_TARGET'))
        before, arms = len(f.device.commands), f.device.arms
        f.session.step(f.packet(.86))
        self.assertEqual(len(f.device.commands), before)
        self.assertEqual(f.device.arms, arms)
        f.tick()
        f.feed([.86] * 5)
        self.assertFalse(f.session.fatal)
        self.assertGreater(f.device.arms, arms)
        self.assertGreater(len(f.device.commands), before)

    def test_old_ready_frame_cannot_rewarm_after_in_zone_loss(self):
        f = wide_scene()
        f.session.step(f.packet(.5))
        f.tick(1)
        f.session.step(f.packet(.5))
        old = copy.deepcopy(f.last)
        f.session.step(f.packet(state='NO_TARGET'))
        f.session.step(old)
        self.assertEqual(f.session.controller.warmup, 0)
        self.assertEqual(f.device.commands, [])

    def test_mutated_frame_is_rejected_even_after_loss_reset(self):
        f = wide_scene()
        f.session.step(f.packet(.5))
        old = copy.deepcopy(f.last)
        f.session.step(f.packet(state='NO_TARGET'))
        old['target']['box'][0] += 1
        f.session.step(old)
        self.assertTrue(f.session.fatal)
        self.assertEqual(f.session.reason, 'SESSION_SOURCE_MUTATED')

    def test_reordered_frame_is_rejected_even_after_loss_reset(self):
        f = wide_scene()
        f.session.step(f.packet(.5))
        f.tick(1)
        f.session.step(f.packet(.5))
        old = copy.deepcopy(f.last)
        f.session.step(f.packet(state='NO_TARGET'))
        old['source_frame_id'] -= 1
        old['source_mono_ms'] -= 1
        old['deadline_mono_ms'] -= 1
        old['face_detection_mono_ms'] -= 1
        f.session.step(old)
        self.assertTrue(f.session.fatal)
        self.assertEqual(f.session.reason, 'SESSION_SOURCE_REORDERED')

    def test_same_target_duplicates_never_renew_a_lease(self):
        f = wide_scene()
        f.feed([.86] * 4)
        old = copy.deepcopy(f.last)
        before = len(f.device.commands)
        for _ in range(4):
            f.session.step(old)
            f.tick(1)
        self.assertEqual(len(f.device.commands), before)

    def test_loss_stops_without_returning_home_or_timer_replay(self):
        f = wide_scene()
        f.feed([.86] * 4)
        f.session.step(f.packet(state='NO_TARGET'))
        stopped = f.device.pulse
        before = len(f.device.commands)
        f.tick(25)
        self.assertEqual(f.device.pulse, stopped)
        self.assertEqual(len(f.device.commands), before)
        self.assertEqual(f.device.status()['flags'], 0)

    def test_changed_camera_in_unconfirmed_packet_requires_new_session(self):
        f = wide_scene()
        f.feed([.86] * 4)
        f.session.step(f.packet(state='UNCONFIRMED', camera_epoch='replacement'))
        self.assertTrue(f.session.fatal)
        self.assertEqual(f.device.status()['flags'], 0)

    def test_expired_source_cannot_extend_original_deadline(self):
        f = wide_scene()
        f.feed([.86] * 4)
        before = len(f.device.commands)
        f.now += .6
        f.session.step(f.last)
        self.assertFalse(f.session.active)
        self.assertEqual(len(f.device.commands), before)

    def test_new_explicit_session_can_acquire_a_different_face(self):
        f = wide_scene()
        for _ in range(6):
            f.session.step(other_target(f, track_id=2))
            f.tick()
        self.assertTrue(f.device.commands)
        self.assertFalse(f.session.fatal)

    def test_target_lock_is_anonymous_and_grants_no_identity(self):
        f = wide_scene()
        f.session.step(f.packet(.5))
        lock = f.session.status()['target_lock']
        self.assertEqual(lock['track_id'], 1)
        self.assertEqual(lock['track_generation'], 1)
        self.assertFalse(lock['identity_authenticated'])
        self.assertFalse(lock['personal_memory_authorized'])

    def test_duplicate_image_still_stops_at_original_anchor_expiry(self):
        f = wide_scene()
        packet = f.packet(.5)
        packet['face_detection_mono_ms'] = round(f.now * 1000) - 499
        f.session.step(packet)
        f.now += .002
        f.session.step(packet)
        self.assertEqual(f.session.reason, 'SOURCE_EXPIRED')
        self.assertFalse(f.session.active)
        self.assertEqual(f.device.commands, [])

    def test_empty_initial_source_does_not_lock_or_arm(self):
        f = wide_scene()
        f.session.step(f.packet(state='NO_TARGET'))
        self.assertFalse(f.session.status()['target_lock']['locked'])
        self.assertEqual(f.device.arms, 0)

    def test_untrusted_fixture_cannot_acquire_a_live_session(self):
        f = wide_scene()
        f.session.allow_fixture = False
        f.session.step(f.packet(.86))
        self.assertTrue(f.session.fatal)
        self.assertEqual(f.session.reason, 'NON_ACTUAL_SOURCE')
        self.assertFalse(f.session.status()['target_lock']['locked'])
        self.assertEqual(f.device.commands, [])

    def test_image_without_admitted_quality_does_not_lock(self):
        f = wide_scene()
        packet = f.packet(.86)
        packet['target']['score'] = .8
        f.session.step(packet)
        self.assertFalse(f.session.status()['target_lock']['locked'])
        self.assertEqual(f.device.arms, 0)

    def test_protocol_fault_context_keeps_immediate_stop_semantics(self):
        for changes, reason in ((dict(board_boot_id='other'), 'BOOT_CHANGED'),
                (dict(mirror_horizontal=False), 'UNREVIEWED_ORIENTATION'),
                (dict(frame_width=800), 'FACE_GEOMETRY_CHANGED')):
            with self.subTest(changes=changes):
                f = wide_scene()
                f.feed([.86] * 4)
                finishes = f.device.finishes
                f.session.step(f.packet(.86, **changes))
                self.assertTrue(f.session.fatal)
                self.assertEqual(f.session.reason, reason)
                self.assertEqual(f.device.finishes, finishes)
                self.assertEqual(f.device.status()['flags'], 0)


if __name__ == '__main__':
    unittest.main()
