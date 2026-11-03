"""Identity transactions, attribution and UI contract; synthetic embeddings only."""
import copy
from pathlib import Path
import tempfile
import unittest

from board.identity.camera_faces import face_for_target
from board.identity.live import IdentityService
from board.identity.store import IdentityStore
from board.interaction.ui_contract import identity_completion, validate_snapshot
from board.vision.ui_camera_service import CameraState


class Extractor:
    def __init__(self, vector=(1., 0., 0., 0.), reason=''):
        self.vector, self.reason = vector, reason

    def extract(self, *_):
        return self.vector, self.reason


class LiveIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'identities.sqlite3'
        self.now = 1000
        self.state = CameraState('boot', 'service', clock=lambda: self.now)
        self.store = IdentityStore(self.path, 'synthetic-test', 4, .85, .1, allow_cross_thread=True)
        self.service = IdentityService(self.store, lambda: Extractor(), self.state.identity_target,
                                       lock=self.state.lock, clock=lambda: self.now)
        self.service.ready = True  # This test's injected extractor is already initialized.
        self.state.identity = self.service
        self.addCleanup(self.service.close)
        self.frame()

    def frame(self, tid=1, generation=1, fid=1, visible=True):
        self.state.captured(self.now)
        self.observation = {'target_id': tid, 'tracks': [
            {'track_id': tid, 'generation': generation, 'box': (0, 0, 100, 200),
             'visible': visible, 'confirmed': True}]}
        self.state.observed(fid, self.now, self.observation, 1.)

    def infer(self, extractor=None, fid=1):
        self.service.offer(None, fid, self.now, self.observation, self.state.camera_epoch)
        packet, self.service.pending = self.service.pending, None
        if packet:
            self.service.process(packet, extractor or Extractor())

    def command(self, action, params, cid='one'):
        value = self.state.snapshot()
        return {'protocol_version': 'aura-ui-1', 'board_boot_id': 'boot', 'service_epoch': 'service',
                'command_id': cid, 'ui_epoch': 'ui', 'ui_generation': 0, 'context': value['context'],
                'snapshot_sequence': value['sequence'], 'issued_mono_ms': self.now,
                'deadline_mono_ms': self.now+2500, 'action': action, 'params': params}

    def enrollment(self, name='测试访客', cid='enroll'):
        params = {'target': self.state.identity_target(), 'display_name': name, 'confirmed': True}
        return self.command('identity_enroll', params, cid)

    def delete(self, person_id, revision, cid='delete'):
        return self.command('identity_delete', {'person_id': person_id, 'db_version': revision,
                                               'confirmed': True}, cid)

    def test_unknown_enroll_known_then_delete_and_unknown(self):
        self.infer()
        value = validate_snapshot(self.state.snapshot(), 'boot', self.now)
        self.assertEqual(value['modules']['identity']['state'], 'UNKNOWN')
        self.assertTrue(value['capabilities']['identity_enroll'])
        self.assertTrue(self.state.command(self.enrollment())['accepted'])
        identity = self.state.snapshot()['modules']['identity']
        self.assertEqual(identity['state'], 'KNOWN')
        self.assertEqual(identity['display_name'], '测试访客')
        self.assertEqual(identity['last_operation']['state'], 'COMMITTED')
        self.assertTrue(self.state.command(self.delete(identity['person_id'], identity['db_version']))['accepted'])
        self.assertEqual(self.state.snapshot()['modules']['identity']['people'], [])
        self.infer()
        self.assertEqual(self.state.snapshot()['modules']['identity']['state'], 'UNKNOWN')

    def test_no_auto_enrollment_or_photos_written(self):
        self.infer()
        self.assertEqual(self.store.people(), [])
        self.assertEqual([p.name for p in Path(self.temp.name).iterdir()], ['identities.sqlite3'])

    def test_unknown_cannot_enroll_without_current_face(self):
        self.assertFalse(self.state.command(self.enrollment())['accepted'])
        self.assertEqual(self.store.revision, 0)

    def test_enrollment_requires_explicit_confirmation(self):
        self.infer()
        command = self.enrollment()
        command['params']['confirmed'] = False
        self.assertFalse(self.state.command(command)['accepted'])
        self.assertEqual(self.store.people(), [])

    def test_blank_name_rejected_without_database_change(self):
        self.infer()
        self.assertFalse(self.state.command(self.enrollment('   '))['accepted'])
        self.assertEqual(self.store.revision, 0)

    def test_duplicate_command_commits_once_and_mutation_rejected(self):
        self.infer()
        command = self.enrollment()
        ack = self.state.command(command)
        self.assertTrue(ack['accepted'])
        self.assertEqual(self.state.command(command), ack)
        changed = copy.deepcopy(command)
        changed['params']['display_name'] = '不同访客'
        self.assertFalse(self.state.command(changed)['accepted'])
        self.assertEqual(self.store.revision, 1)

    def test_target_generation_change_cannot_enroll_old_face(self):
        self.infer()
        command = self.enrollment()
        self.frame(generation=2, fid=2)
        self.assertFalse(self.state.command(command)['accepted'])
        self.assertFalse(self.state.snapshot()['capabilities']['identity_enroll'])

    def test_target_change_hides_known_name_immediately(self):
        self.infer();self.state.command(self.enrollment())
        self.frame(tid=2, fid=2)
        identity = self.state.snapshot()['modules']['identity']
        self.assertEqual(identity['state'], 'UNKNOWN')
        self.assertEqual(identity['display_name'], '')

    def test_lost_target_clears_known_name(self):
        self.infer();self.state.command(self.enrollment())
        self.frame(visible=False, fid=2)
        self.assertEqual(self.state.snapshot()['modules']['identity']['display_name'], '')

    def test_camera_freeze_and_detector_error_clear_known_name(self):
        self.infer();self.state.command(self.enrollment())
        self.now += 751
        self.assertEqual(self.state.snapshot()['modules']['identity']['display_name'], '')
        self.frame(fid=2);self.infer(fid=2)
        self.assertEqual(self.state.snapshot()['modules']['identity']['state'], 'KNOWN')
        self.state.detector_error = 'failed'
        self.assertEqual(self.state.snapshot()['modules']['identity']['display_name'], '')

    def test_pending_target_selection_hides_old_identity(self):
        self.infer();self.state.command(self.enrollment())
        self.state.requested_target = 2
        self.assertEqual(self.state.snapshot()['modules']['identity']['display_name'], '')

    def test_bad_face_clears_previous_match_and_disables_enrollment(self):
        self.infer();self.state.command(self.enrollment())
        self.infer(Extractor(None, '人脸模糊'))
        view = self.state.snapshot()
        self.assertEqual(view['modules']['identity']['display_name'], '')
        self.assertEqual(view['modules']['identity']['detail'], '人脸模糊')
        self.assertFalse(view['capabilities']['identity_enroll'])

    def test_face_job_finishing_after_target_change_is_discarded(self):
        owner = self
        class ChangedTarget:
            def extract(self, *_):
                owner.frame(tid=2, fid=2)
                return (1, 0, 0, 0), ''
        self.infer(ChangedTarget())
        self.assertEqual(self.service.discarded, 1)
        self.assertIsNone(self.service.result)

    def test_face_job_finishing_after_expiry_is_discarded(self):
        owner = self
        class Delayed:
            def extract(self, *_):
                owner.now += 1500
                owner.frame(fid=2)
                return (1, 0, 0, 0), ''
        self.infer(Delayed())
        self.assertIsNone(self.service.result)

    def test_face_job_finishing_after_delete_does_not_restore_identity(self):
        self.infer();self.state.command(self.enrollment())
        p = self.store.people()[0]['person_id']
        owner = self
        class Deleted:
            def extract(self, *_):
                self.result = owner.state.command(owner.delete(p, owner.store.revision))
                return (1, 0, 0, 0), ''
        extractor = Deleted()
        self.infer(extractor)
        self.assertTrue(extractor.result['accepted'])
        self.assertIsNone(self.service.result)
        self.assertEqual(self.store.people(), [])

    def test_stale_database_delete_is_rejected(self):
        self.infer();self.state.command(self.enrollment())
        p = self.store.people()[0]['person_id']
        self.assertFalse(self.state.command(self.delete(p, 0))['accepted'])
        self.assertEqual(len(self.store.people()), 1)

    def test_same_person_reenters_under_new_track_and_is_recognized(self):
        self.infer();self.state.command(self.enrollment())
        self.frame(tid=11, generation=3, fid=2)
        self.infer(fid=2)
        identity = self.state.snapshot()['modules']['identity']
        self.assertEqual(identity['display_name'], '测试访客')
        self.assertEqual(identity['target']['track_id'], 11)

    def test_different_person_remains_unknown(self):
        self.infer();self.state.command(self.enrollment())
        self.frame(tid=2, fid=2)
        self.infer(Extractor((0, 1, 0, 0)), fid=2)
        self.assertEqual(self.state.snapshot()['modules']['identity']['state'], 'UNKNOWN')

    def test_ambiguous_match_cannot_be_enrolled(self):
        for key in ('a', 'b'):
            self.store.enroll(key, key, (1, 0, 0, 0), consent=True)
        self.infer()
        view = self.state.snapshot()
        self.assertEqual(view['modules']['identity']['state'], 'UNKNOWN')
        self.assertFalse(view['capabilities']['identity_enroll'])

    def test_latest_only_input_is_bounded(self):
        for fid in range(1, 100):
            self.service.offer(None, fid, self.now, self.observation, self.state.camera_epoch)
        self.assertEqual(self.service.pending[1], 99)
        self.assertEqual(self.service.health()['pending_frames'], 1)

    def test_health_does_not_claim_motion(self):
        self.assertTrue(self.state.health()['identity_recognition'])
        self.assertFalse(self.state.health()['motion_command_emitted'])

    def test_capacity_rejection_is_transactional(self):
        self.service.max_people = 1
        self.store.enroll('a', '已有', (0, 1, 0, 0), consent=True)
        self.infer()
        self.assertFalse(self.state.command(self.enrollment())['accepted'])
        self.assertEqual(self.store.revision, 1)

    def test_store_revision_compare_and_delete_is_atomic(self):
        self.store.enroll('a', '已有', (1, 0, 0, 0), consent=True)
        second = IdentityStore(self.path, 'synthetic-test', 4, .85, .1)
        self.addCleanup(second.close)
        old_revision = second.revision
        self.store.enroll('b', '另一位', (0, 1, 0, 0), consent=True)
        with self.assertRaises(ValueError):
            second.delete('a', expected_revision=old_revision)
        self.assertEqual(len(second.people()), 2)

    def test_ui_shows_completion_only_for_matching_committed_transaction(self):
        self.infer()
        command = self.enrollment()
        ack = self.state.command(command)
        result = dict(ack, action='identity_enroll')
        identity = self.state.snapshot()['modules']['identity']
        self.assertEqual(identity_completion(result, identity), '已登记“测试访客”')
        for mutate in (lambda v: v['last_operation'].update(command_id='old'),
                       lambda v: v['last_operation'].update(state='ACCEPTED'),
                       lambda v: v.update(db_version=100)):
            value = copy.deepcopy(identity);mutate(value)
            self.assertEqual(identity_completion(result, value), '')


class FaceOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.key = {'camera_epoch': 'camera', 'track_id': 1, 'track_generation': 1}
        self.track = {'track_id': 1, 'generation': 1, 'visible': True, 'confirmed': True,
                      'box': (0, 0, 100, 200)}
        self.face = [20, 20, 50, 50]+[30, 30, 50, 30, 40, 40, 30, 55, 50, 55]+[.99]

    def test_one_face_one_owner(self):
        face, reason = face_for_target([self.face], [self.track], self.key)
        self.assertEqual(face, self.face)
        self.assertEqual(reason, '')

    def test_overlapping_people_reject_instead_of_assigning(self):
        other = dict(self.track, track_id=2)
        face, reason = face_for_target([self.face], [self.track, other], self.key)
        self.assertIsNone(face)
        self.assertIn('多个人体', reason)

    def test_unconfirmed_overlapping_person_also_blocks_ownership(self):
        other = dict(self.track, track_id=2, confirmed=False)
        self.assertIsNone(face_for_target([self.face], [self.track, other], self.key)[0])

    def test_multiple_faces_in_target_rejected(self):
        self.assertIsNone(face_for_target([self.face, self.face], [self.track], self.key)[0])

    def test_tiny_low_score_nonfinite_and_outside_faces_rejected(self):
        for index, value in [(2, 10), (14, .2), (4, float('nan')), (0, 200)]:
            face = list(self.face);face[index] = value
            self.assertIsNone(face_for_target([face], [self.track], self.key)[0])

    def test_wrong_generation_or_invisible_target_rejected(self):
        for changed in (dict(self.track, generation=2), dict(self.track, visible=False)):
            self.assertIsNone(face_for_target([self.face], [changed], self.key)[0])


if __name__ == '__main__':
    unittest.main()
