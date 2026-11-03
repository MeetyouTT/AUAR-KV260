import bootstrap
import copy
from types import SimpleNamespace
import unittest

from board.identity.camera_faces import CameraFaceExtractor
from board.identity.deferred import DeferredIdentity
from board.identity.live import IdentityService
from board.identity.store import IdentityStore
from board.identity.spoken_query import answer_current_face
from board.interaction.ui_contract import validate_snapshot
from board.vision.dpu_sface import DpuSFace
from board.vision.dpu_vision_schedule import DpuVisionSchedule


class FeatureAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.now = [100.0]
        self.schedule = DpuVisionSchedule(clock=lambda: self.now[0])
        self.schedule.next_primary = 101.0
        self.engine = DpuSFace.__new__(DpuSFace)
        self.engine.schedule = self.schedule
        self.engine._closed = False
        self.engine.clock = lambda: 10000
        self.engine.source_ttl = 1000
        for name in ('requests', 'execution_attempts', 'completed', 'features_returned',
                     'deferred', 'slot_denials', 'expired_after_admission'):
            setattr(self.engine, name, 0)
        self.runner_closed = []
        self.engine.runner = SimpleNamespace(last_ms=0., close=lambda: self.runner_closed.append(True))
        self.extractor = CameraFaceExtractor.__new__(CameraFaceExtractor)
        self.extractor.local_dpu = self.engine
        self.extractor.shadow = None
        self.extractor.shadow_error = ''
        self.key = {'camera_epoch': 'fixture', 'track_id': 1, 'track_generation': 1}
        self.store = IdentityStore(':memory:', self.engine.model_id, 128, .5, .1)
        self.vector = tuple([1.] * 128)
        self.store.enroll('fixture-id', 'fixture-name', self.vector, consent=True)
        self.service = IdentityService(self.store, None, lambda: self.key, clock=lambda: 10000,
                                       multi_frame=True, backend='DPU_SFACE_INT8')
        self.service.extractor = self.extractor
        self.service.ready = True
        self.packet(self.vector)

    def tearDown(self):
        self.store.close()

    def packet(self, vector):
        self.service.result = {'target': self.key, 'fid': 1, 'stamp': 10000,
                               'revision': self.store.revision, 'embedding': vector,
                               'match': self.store.match(vector), 'face_png': b'fixture-private-crop'}

    def fault(self):
        with self.schedule.optional('sface') as acquired:
            self.assertTrue(acquired)
            self.now[0] += .031
        self.assertTrue(self.schedule.disabled('sface'))

    def snapshot(self):
        view, capabilities = self.service.view()
        view.update(target_kind='face', face_count=1, face_target=copy.deepcopy(self.key),
                    face_targets=[{'key': copy.deepcopy(self.key), 'label': 'fixture-face'}])
        return {'protocol_version': 'aura-ui-1', 'board_boot_id': 'fixture-boot',
                'service_epoch': 'fixture-service', 'sequence': 1, 'observed_mono_ms': 10000,
                'ttl_ms': 1000, 'source_kind': 'actual',
                'context': {'session_id': 'fixture-session', 'request_id': '', 'generation': 0},
                'modules': {'camera': {'state': 'READY'}, 'identity': view}, 'capabilities': capabilities}

    def test_real_scheduler_protection_propagates_through_extractor_to_health(self):
        self.assertTrue(self.service.health()['ready'])
        self.fault()
        health = self.service.health()
        self.assertFalse(health['ready'])
        self.assertEqual(health['feature_status']['unavailable_reason'], 'DPU_SFACE_OPTIONAL_DISABLED')
        self.assertTrue(health['feature_status']['recovery_required'])
        self.assertTrue(health['error'])
        self.assertFalse(health['feature_inference']['ready'])
        self.assertEqual(self.schedule.health()['optional']['sface']['overruns'], 1)

    def test_protection_hides_previously_fresh_known_name_and_crop(self):
        self.assertEqual(self.service.view()[0]['state'], 'KNOWN')
        self.assertIsNotNone(self.service.face_preview(self.key, 1))
        self.fault()
        view, capabilities = self.service.view()
        self.assertEqual(view['state'], 'ERROR')
        self.assertEqual(view['person_id'], '')
        self.assertEqual(view['display_name'], '')
        self.assertNotIn('face_preview', view)
        self.assertNotIn('source_frame_id', view)
        self.assertIsNone(self.service.face_preview(self.key, 1))
        self.assertFalse(capabilities['identity_enroll'])
        self.assertFalse(capabilities['identity_sample_start'])
        self.assertTrue(capabilities['identity_delete'])

    def test_existing_fresh_unknown_cannot_enroll_through_direct_action(self):
        self.packet(tuple([1.] * 64 + [-1.] * 64))
        self.assertEqual(self.service.result['match'].state, 'UNKNOWN')
        revision = self.store.revision
        self.fault()
        with self.assertRaisesRegex(ValueError, '不可用'):
            self.service.enroll({'target': self.key, 'display_name': 'new-fixture', 'confirmed': True}, 'cmd')
        self.assertEqual(self.store.revision, revision)
        self.assertEqual(len(self.store.people()), 1)

    def test_ui_protocol_accepts_explicit_error_without_old_identity_or_crop(self):
        self.fault()
        snapshot = validate_snapshot(self.snapshot(), 'fixture-boot', 10000)
        identity = snapshot['modules']['identity']
        self.assertEqual(identity['state'], 'ERROR')
        self.assertEqual(identity['display_name'], '')
        self.assertFalse(snapshot['capabilities']['identity_sample_start'])

    def test_voice_query_distinguishes_service_error_from_unknown_person(self):
        start = self.snapshot()
        self.assertEqual(answer_current_face(start, start, 'fixture-boot', 10000)['code'], 'identity_seen')
        self.fault()
        self.assertEqual(answer_current_face(self.snapshot(), start, 'fixture-boot', 10000)['code'],
                         'identity_unavailable')

    def test_voice_consumer_reports_explicit_camera_error_as_unavailable(self):
        start = self.snapshot()
        current = copy.deepcopy(start)
        current['modules']['identity']['state'] = 'ERROR'
        self.assertEqual(answer_current_face(current, start, 'fixture-boot', 10000)['code'],
                         'identity_unavailable')
        current['modules']['identity'].update(state='UNKNOWN', person_id='', display_name='')
        self.assertEqual(answer_current_face(current, start, 'fixture-boot', 10000)['code'], 'identity_unknown')

    def test_existing_fresh_unknown_cannot_start_sampling_through_direct_action(self):
        self.packet(tuple([1.] * 64 + [-1.] * 64))
        self.fault()
        with self.assertRaisesRegex(ValueError, '不可用'):
            self.service.sample_start({'target': self.key}, 'cmd')
        self.assertEqual(self.service.sampling.stage, 'idle')

    def test_delete_remains_usable_without_feature_inference(self):
        self.fault()
        self.service.delete({'confirmed': True, 'person_id': 'fixture-id',
                             'db_version': self.store.revision}, 'cmd')
        self.assertEqual(self.store.people(), [])

    def test_sampling_cancel_remains_usable_while_backend_is_disabled(self):
        self.service.sampling.start(self.key, self.store.revision, '', anchor=self.vector)
        session = self.service.sampling.session_id
        self.fault()
        self.assertTrue(self.service.view()[1]['identity_sample_cancel'])
        self.service.sample_cancel({'session_id': session}, 'cmd')
        self.assertEqual(self.service.sampling.stage, 'idle')

    def test_temporary_contention_does_not_report_backend_failure(self):
        self.schedule.active = 'yolo'
        self.schedule.waiting_primary = 1
        self.assertTrue(self.service.health()['ready'])
        self.assertEqual(self.service.view()[0]['state'], 'KNOWN')
        self.assertFalse(self.engine.availability()['recovery_required'])

    def test_yunet_disablement_does_not_masquerade_as_sface_disablement(self):
        self.schedule.jobs['yunet'] = {'disabled': True}
        self.assertTrue(self.engine.availability()['ready'])

    def test_disabled_request_defers_without_native_or_fp32_fallback(self):
        self.fault()
        with self.assertRaises(DeferredIdentity) as caught:
            self.engine.feature(None, source_mono_ms=10000)
        self.assertFalse(caught.exception.retryable)
        self.assertEqual(self.engine.execution_attempts, 0)
        self.assertEqual(self.engine.completed, 0)

    def test_closed_backend_is_unavailable_without_requesting_recovery(self):
        self.engine.close()
        self.assertEqual(self.runner_closed, [True])
        self.assertFalse(self.engine.availability()['ready'])
        self.assertEqual(self.engine.availability()['unavailable_reason'], 'DPU_SFACE_CLOSED')
        self.assertFalse(self.engine.availability()['recovery_required'])

    def test_legacy_extractor_without_availability_api_keeps_previous_behavior(self):
        self.service.extractor = SimpleNamespace()
        self.assertTrue(self.service.health()['ready'])
        self.assertEqual(self.service.view()[0]['state'], 'KNOWN')

    def test_unreadable_backend_status_fails_closed_and_keeps_private_exception_out(self):
        def broken():
            raise RuntimeError('private-fixture-data')
        self.service.extractor = SimpleNamespace(feature_status=broken)
        health = self.service.health()
        self.assertFalse(health['ready'])
        self.assertEqual(health['feature_status']['unavailable_reason'], 'FEATURE_STATUS_FAILED')
        self.assertNotIn('private-fixture-data', health['error'])
        self.assertEqual(self.service.view()[0]['state'], 'ERROR')

    def test_malformed_availability_is_rejected(self):
        for invalid in (None, {}, {'ready': 1}, {'ready': None}, {'ready': False},
                        {'ready': False, 'detail': ''}, {'ready': False, 'detail': None}):
            self.service.extractor = SimpleNamespace(feature_status=lambda value=invalid: value)
            self.assertFalse(self.service.health()['ready'])


if __name__ == '__main__':
    unittest.main()
