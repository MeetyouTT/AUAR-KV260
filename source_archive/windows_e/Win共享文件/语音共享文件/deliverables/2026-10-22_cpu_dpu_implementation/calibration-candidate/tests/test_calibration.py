"""Operator protocol/statistics tests use synthetic vectors, never biometrics."""
import bootstrap
import copy
from functools import partial
import io
import json
from email.message import Message
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from board.identity.sface_calibration import (CalibrationSession, calibration_configuration,
                                              normalized, target_tuple)
from board.identity.calibration_http import wrap_handler, PATH
from board.identity.sface_shadow import SFaceShadow
from board.identity.store import IdentityStore
from test_shadow import configuration, Embedder, wait_for, vector


def pose(**changes):
    return dict({'yaw': 0., 'roll': 0., 'pixels': 112., 'eye_distance': 36., 'blur': 100.}, **changes)


def key(generation=1):
    return {'camera_epoch': 'test_epoch', 'track_id': 1, 'track_generation': generation}


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.current = key()
        self.serial = 0
        self.session = CalibrationSession(lambda: self.now, 1000)
        self.session.ticket = partial(self.session.ticket, quality=pose())
        self.addCleanup(self.session.close)

    def begin(self, purpose='calibration_gallery', person='P_A', capture=None):
        self.serial += 1
        return self.session.begin(purpose, person, capture or 'C_'+str(self.serial), self.current, self.current)

    def capture(self, purpose, person, values=None):
        control = self.begin(purpose, person)
        for feature in (values or [vector()] * 3):
            self.now += 600
            ticket = self.session.ticket(self.now, self.now, self.current, self.current)
            self.assertTrue(self.session.accept(ticket, feature, self.current))
        self.session.end(control['session_token'])
        return control

    def complete_calibration(self):
        for purpose, person, axis in (
                ('calibration_gallery', 'P_A', 0), ('calibration_gallery', 'P_B', 1),
                ('calibration_probe', 'P_A', 0), ('calibration_probe', 'P_B', 1),
                ('calibration_unknown', 'P_C', 2)):
            self.capture(purpose, person, [vector(axis)] * 3)

    def request(self, action, params):
        self.serial += 1
        return self.session.dispatch(action, dict(params, request_id=format(self.serial, '032x')),
                                     current_target=self.current)

    def test_configuration_default_off_and_explicit_independent_shadow(self):
        self.assertIsNone(calibration_configuration({}))
        self.assertIsNone(calibration_configuration({'dpu_sface_calibration': {'enabled': False}}))
        config = configuration()
        config['dpu_sface_shadow']['compare_cosine'] = False
        config['dpu_sface_calibration'] = {'enabled': True, 'mode': 'CALIBRATION_ONLY', 'control_token': 'b'*64}
        self.assertEqual(calibration_configuration(config)['mode'], 'CALIBRATION_ONLY')
        for field, value in (('control_token', 'short'), ('mode', 'IDENTITY'), ('enabled', 1)):
            altered = copy.deepcopy(config)
            altered['dpu_sface_calibration'][field] = value
            with self.assertRaises(ValueError): calibration_configuration(altered)
        config['dpu_sface_shadow']['compare_cosine'] = True
        with self.assertRaises(ValueError): calibration_configuration(config)

    def test_strict_anonymous_labels_target_and_split_controls(self):
        for person in ('Alice', 'P_a', 'P_A/name', 'P_'+'A'*13, '', None):
            with self.assertRaises((ValueError, TypeError)):
                self.begin(person=person)
        for target in (None, dict(key(), extra=1), dict(key(), track_id=True), dict(key(), camera_epoch='../')):
            with self.assertRaises(ValueError): target_tuple(target)
        with self.assertRaises(ValueError):
            self.session.begin('calibration_gallery', 'P_A', 'C_OK', key(), key(2))
        with self.assertRaises(ValueError): self.begin('validation_known')
        with self.assertRaises(ValueError): self.begin('calibration_probe')

    def test_explicit_session_source_time_dedup_and_ticket_replay(self):
        self.assertIsNone(self.session.ticket(1, self.now, self.current))
        control = self.begin()
        for stamp in (self.now-1000, self.now+1):
            self.assertIsNone(self.session.ticket(1, stamp, self.current))
        ticket = self.session.ticket(1, self.now, self.current)
        self.assertTrue(self.session.accept(ticket, vector(), self.current))
        self.assertFalse(self.session.accept(ticket, vector(), self.current))
        self.now += 600
        repeated = self.session.ticket(1, self.now, self.current)
        self.assertFalse(self.session.accept(repeated, vector(), self.current))
        second = self.session.ticket(2, self.now, self.current)
        self.now += 1000
        self.assertFalse(self.session.accept(second, vector(), self.current))
        self.session.end(control['session_token'])
        self.assertEqual(self.session.health()['samples_in_ram'], 1)

    def test_end_reset_generation_and_target_change_invalidate_inflight(self):
        first = self.begin()
        ticket = self.session.ticket(1, self.now, self.current)
        self.session.end(first['session_token'])
        self.begin(capture='C_OTHER')
        self.assertFalse(self.session.accept(ticket, vector(), self.current))
        ticket = self.session.ticket(2, self.now, self.current)
        self.current = key(2)
        self.assertFalse(self.session.accept(ticket, vector(), self.current))
        self.assertFalse(self.session.health()['active_session'])
        self.assertEqual(self.session.health()['last_session_end_reason'], 'TARGET_CHANGED')
        self.current = key()
        self.assertFalse(self.session.accept(ticket, vector(), self.current))

    def test_timeout_bad_end_token_and_explicit_discard(self):
        first = self.begin()
        with self.assertRaises(ValueError): self.session.end('c'*64)
        self.now += self.session.MAX_SESSION_MS
        self.assertFalse(self.session.health()['active_session'])
        self.assertEqual(self.session.health()['last_session_end_reason'], 'SESSION_EXPIRED')
        with self.assertRaises(ValueError): self.session.end(first['session_token'])
        second = self.begin()
        ticket = self.session.ticket(1, self.now, self.current)
        self.assertTrue(self.session.accept(ticket, vector(), self.current))
        self.session.end(second['session_token'], discard=True)
        self.assertEqual(self.session.health()['samples_in_ram'], 0)

    def test_invalid_feature_and_sampling_rate_do_not_poison_session(self):
        self.begin()
        for i, feature in enumerate(([0.]*128, [float('nan')]*128, [1.]*127, [True]*128)):
            ticket = self.session.ticket(i+1, self.now, self.current)
            self.assertFalse(self.session.accept(ticket, feature, self.current))
        good = self.session.ticket(10, self.now, self.current)
        self.assertTrue(self.session.accept(good, vector(), self.current))
        self.now += 499
        early = self.session.ticket(11, self.now, self.current)
        self.assertFalse(self.session.accept(early, vector(), self.current))
        self.now += 1
        proper = self.session.ticket(12, self.now, self.current)
        self.assertTrue(self.session.accept(proper, vector(), self.current))

    def test_runtime_numpy_float32_output_is_accepted_without_numpy_dependency(self):
        import numpy as np
        self.begin()
        ticket = self.session.ticket(1, self.now, self.current)
        actual_runtime_type = np.array(vector(), dtype=np.float32)
        self.assertTrue(self.session.accept(ticket, actual_runtime_type, self.current))
        self.assertEqual(self.session.health()['samples_in_ram'], 1)

    def test_busy_calibration_lock_never_blocks_primary_offer(self):
        self.begin()
        held, release, done = threading.Event(), threading.Event(), threading.Event()
        def hold():
            with self.session.lock:
                held.set()
                release.wait(2)
            done.set()
        worker = threading.Thread(target=hold)
        worker.start()
        self.addCleanup(worker.join, 2)
        self.addCleanup(release.set)
        self.assertTrue(held.wait(1))
        result = []
        returned = threading.Event()
        def produce():
            result.append(self.session.ticket(1, self.now, self.current))
            returned.set()
        producer = threading.Thread(target=produce)
        producer.start()
        self.addCleanup(producer.join, 2)
        self.assertTrue(returned.wait(.1), 'Primary offer blocked on calibration lock')
        self.assertEqual(result, [None])
        self.assertFalse(done.is_set())
        release.set()

    def test_bounded_samples_sessions_people_and_unique_capture(self):
        first = self.begin(capture='C_BOUND')
        for i in range(self.session.MAX_SAMPLES):
            self.now += 600
            ticket = self.session.ticket(i+1, self.now, self.current)
            self.assertTrue(self.session.accept(ticket, vector(), self.current))
        self.assertIsNone(self.session.ticket(99, self.now, self.current))
        self.session.end(first['session_token'])
        with self.assertRaises(ValueError): self.begin(capture='C_BOUND')
        for i in range(1, self.session.MAX_SESSIONS):
            item = self.begin(purpose='calibration_probe',capture='C_BOUND_'+str(i))
            self.session.end(item['session_token'])
        with self.assertRaises(ValueError): self.begin(capture='C_OVERFLOW')
        self.assertEqual(self.session.health()['sessions'], 32)
        other = CalibrationSession(lambda: self.now, 1000)
        self.addCleanup(other.close)
        for i in range(8):
            item = other.begin('calibration_gallery', 'P_'+str(i), 'C_'+str(i), self.current, self.current)
            other.end(item['session_token'])
        with self.assertRaises(ValueError):
            other.begin('calibration_gallery', 'P_9', 'C_9', self.current, self.current)

    def test_token_collision_and_control_replay_are_refused(self):
        other = CalibrationSession(lambda: self.now, 1000, token_factory=lambda: 'd'*64)
        self.addCleanup(other.close)
        first = other.begin('calibration_gallery', 'P_A', 'C_ONE', self.current, self.current)
        other.end(first['session_token'])
        with self.assertRaises(ValueError):
            other.begin('calibration_gallery', 'P_A', 'C_TWO', self.current, self.current)
        control = {'request_id': 'e'*32}
        self.session.dispatch('reset', control)
        with self.assertRaises(ValueError): self.session.dispatch('reset', control)
        with self.assertRaises(ValueError): self.session.dispatch('garbage', {'request_id': 'f'*32})
        with self.assertRaises(ValueError): self.session.dispatch('reset', {'request_id': 'f'*32})
        for i in range(126): self.session.dispatch('reset', {'request_id': format(i, '032x')})
        self.assertEqual(self.session.health()['mutation_slots_remaining'], 0)
        with self.assertRaises(ValueError): self.session.dispatch('reset', {'request_id': '1'*32})

    def test_insufficient_coverage_cannot_freeze_or_claim_accuracy(self):
        self.capture('calibration_gallery', 'P_A')
        self.capture('calibration_probe', 'P_A')
        report = self.session.report()
        self.assertEqual(report['status'], 'COVERAGE_INSUFFICIENT')
        self.assertFalse(report['coverage']['general_accuracy_proven'])
        self.assertIsNone(self.session.suggest()['candidate'])
        with self.assertRaises(ValueError): self.session.freeze(.5, .1)

    def test_calibration_statistics_suggestion_and_freeze_are_scalar_only(self):
        self.complete_calibration()
        report = self.session.report()
        self.assertTrue(report['coverage']['sufficient'])
        self.assertEqual(report['cross_capture_scores']['same_person']['count'], 18)
        self.assertEqual(report['cross_capture_scores']['different_person']['count'], 72)
        suggestion = self.session.suggest()
        self.assertEqual(suggestion['calibration_metrics']['known_samples'], 6)
        self.assertEqual(suggestion['calibration_metrics']['unknown_samples'], 3)
        self.assertEqual(suggestion['calibration_metrics']['correct_accept'], 6)
        self.assertEqual(suggestion['calibration_metrics']['false_accept'], 0)
        chosen = suggestion['candidate']
        frozen = self.session.freeze(chosen['threshold'], chosen['ambiguity_margin'])
        self.assertFalse(frozen['validation_used_for_selection'])
        self.assertFalse(frozen['general_accuracy_proven'])
        with self.assertRaises(ValueError): self.begin('calibration_unknown', 'P_D')
        encoded = json.dumps(self.session.report(), allow_nan=False)
        for forbidden in ('session_token', 'embedding', 'samples": [', 'P_A', 'camera_epoch'):
            self.assertNotIn(forbidden, encoded)

    def test_independent_validation_never_changes_frozen_candidate(self):
        self.complete_calibration()
        original = self.session.freeze(.6, .1)
        # Reusing the same unknown identity in a genuinely separate capture is
        # permitted and explicitly disclosed; independent subjects not claimed.
        self.capture('validation_known', 'P_A', [vector(1)]*3)
        self.capture('validation_known', 'P_B', [vector(1)]*3)
        self.capture('validation_unknown', 'P_C', [vector(0)]*3)
        validation = self.session.report(validation=True)
        self.assertTrue(validation['coverage']['sufficient'])
        self.assertEqual(validation['metrics']['misidentification'], 3)
        self.assertEqual(validation['metrics']['false_accept'], 3)
        self.assertEqual(validation['validation_unknown_people_seen_in_calibration'], 1)
        self.assertEqual(validation['candidate'], original)
        self.assertEqual(self.session.report()['metrics']['false_accept'], 0)
        with self.assertRaises(ValueError): self.session.freeze(.9, .4)
        self.assertIsNone(self.session.suggest()['candidate'])

    def test_observed_medoid_and_threshold_margin_semantics_match_real_store(self):
        from board.identity.sampling import EnrollmentSampling
        a = normalized([1., .8]+[0.]*126)
        b = normalized([1., .2]+[0.]*126)
        c = normalized([1., -.1]+[0.]*126)
        self.capture('calibration_gallery', 'P_A', [a, b, c])
        self.capture('calibration_gallery', 'P_B', [vector(1)]*3)
        self.capture('calibration_probe', 'P_A', [a]*3)
        self.capture('calibration_probe', 'P_B', [vector(1)]*3)
        self.capture('calibration_unknown', 'P_C', [vector(2)]*3)
        data, _, _ = self.session._snapshot()
        gallery = self.session._gallery(data)
        self.assertIn(gallery['P_A'], tuple(row.feature for row in data[0]['samples']))
        mean = normalized(tuple(sum(row[i] for row in (a,b,c))/3 for i in range(128)))
        self.assertNotEqual(gallery['P_A'], mean)
        actual = EnrollmentSampling(.6, .1, lambda: self.now)
        actual.training = [{'embedding': row.feature, 'pose': dict(zip(('yaw','roll','pixels','eye_distance','blur'),row.pose)),
                            'quality': row.quality} for row in data[0]['samples']]
        self.assertTrue(actual._choose_front())
        self.assertEqual(gallery['P_A'], actual.candidate['embedding'])
        with tempfile.TemporaryDirectory() as folder:
            store = IdentityStore(Path(folder)/'synthetic.sqlite3', 'test-model', 128, .6, .1)
            self.addCleanup(store.close)
            for person, template in gallery.items(): store.enroll(person, person, template, consent=True)
            ambiguous = normalized(tuple(x+y for x,y in zip(gallery['P_A'],gallery['P_B'])))
            for feature, expected in ((b, 'KNOWN'), (vector(2), 'UNKNOWN'), (ambiguous, 'AMBIGUOUS')):
                scores = sorted(((sum(x*y for x,y in zip(feature, template)), person)
                                 for person,template in gallery.items()), reverse=True)
                rows = [(False, scores[0][1], scores[0][1], scores[0][0], scores[0][0]-scores[1][0])]
                result = self.session._metrics(rows, .6, .1)
                state = ('KNOWN' if result['correct_accept'] else 'UNKNOWN' if result['false_reject'] else 'AMBIGUOUS')
                self.assertEqual(state, expected)
                self.assertEqual(store.match(feature).state, state)

    def test_no_file_io_and_close_erases_features(self):
        with patch('builtins.open', side_effect=AssertionError('Calibration must not open files')):
            self.complete_calibration()
            self.session.suggest()
            self.session.report()
        self.session.close()
        self.assertEqual(self.session.health()['samples_in_ram'], 0)
        with self.assertRaises(ValueError): self.begin()

    def test_quality_is_camera_supplied_and_only_qualified_frontal_samples_collect(self):
        self.begin()
        for invalid in (None, {}, pose(yaw=.23), pose(roll=15.01), pose(blur=39.9),
                        pose(eye_distance=17.9), pose(pixels=71.9), pose(yaw=float('nan'))):
            self.assertIsNone(self.session.ticket(1,self.now,self.current,quality=invalid))
        ticket = self.session.ticket(1,self.now,self.current,quality=pose(yaw=.22,roll=15.))
        self.assertTrue(self.session.accept(ticket, vector(), self.current))
        self.assertEqual(self.session.health()['quality_rejected'], 8)

    def test_top_five_frontal_ranking_and_quality_tie_match_actual_enrollment(self):
        from board.identity.sampling import EnrollmentSampling
        control = self.begin()
        for i,yaw in enumerate((.21,.05,.2,.1,.01,.15,.02,.04,.19,.03)):
            self.now += 600
            ticket = self.session.ticket(i+1,self.now,self.current,
                    quality=pose(yaw=yaw,roll=float(i),blur=100.+i*3))
            feature = normalized([1., i*.08]+[0.]*126)
            self.assertTrue(self.session.accept(ticket,feature,self.current))
        self.session.end(control['session_token'])
        data, _, _ = self.session._snapshot()
        actual = EnrollmentSampling(.6,.1,lambda:self.now)
        actual.training = [{'embedding': row.feature, 'pose': dict(zip(('yaw','roll','pixels','eye_distance','blur'),row.pose)),
                            'quality': row.quality} for row in data[0]['samples']]
        self.assertTrue(actual._choose_front())
        self.assertEqual(self.session._gallery(data)['P_A'],actual.candidate['embedding'])
        self.assertEqual(self.session.report()['gallery_policy'],
                         'frontal_medoid_v1_observed_top5_operator_labelled_capture')
        self.assertFalse(self.session.report()['deployment_threshold_validated'])

    def test_analytical_reports_are_serialized_without_blocking_health(self):
        with self.session.analysis_lock:
            with self.assertRaises(ValueError): self.session.dispatch('report', {})
            with self.assertRaises(ValueError): self.session.dispatch('suggest', {})
            self.assertEqual(self.session.dispatch('health', {})['samples_in_ram'], 0)
        self.assertEqual(self.session.dispatch('report', {})['status'], 'COVERAGE_INSUFFICIENT')


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.key = key()
        self.config = configuration()
        self.config['dpu_sface_shadow']['compare_cosine'] = False
        self.controller = CalibrationSession(lambda: self.now, 500)
        self.embedder = Embedder(block=True)
        self.service = SFaceShadow(self.config, object(), object(), lambda: self.key,
            clock=lambda: self.now, guard_lock=threading.RLock(),
            embedder_factory=lambda: self.embedder, result_observer=self.controller)
        self.addCleanup(lambda: self.service.close(.2))
        self.addCleanup(self.embedder.release.set)
        import numpy as np
        self.crop = np.zeros((112,112,3), np.uint8)
        self.service.start()
        wait_for(self, lambda: self.service.ready)

    def begin(self):
        return self.controller.begin('calibration_gallery', 'P_A', 'C_EXPLICIT', self.key, self.key)

    def offer(self):
        wait_for(self, lambda: self.service.offer(self.crop, 1, self.now, self.key, None, quality=pose()))
        self.assertTrue(self.embedder.entered.wait(1))

    def test_feature_is_collected_only_after_explicit_label_and_valid_completion(self):
        self.begin()
        self.offer()
        self.assertEqual(self.controller.health()['samples_in_ram'], 0)
        self.embedder.release.set()
        wait_for(self, lambda: self.controller.health()['samples_in_ram'] == 1)
        self.assertEqual(self.service.health()['identity_decisions_from_shadow'], 0)
        self.assertEqual(self.service.health()['calibration_observer_errors'], 0)

    def test_end_while_inflight_invalidates_observer_without_stopping_shadow(self):
        control = self.begin()
        self.offer()
        self.controller.end(control['session_token'])
        self.embedder.release.set()
        wait_for(self, lambda: self.service.health()['accepted'] == 1)
        self.assertEqual(self.controller.health()['samples_in_ram'], 0)
        self.assertEqual(self.controller.health()['rejected'], 1)

    def test_generation_change_discards_output_and_invalidates_session(self):
        self.begin()
        self.offer()
        self.key = key(2)
        self.embedder.release.set()
        wait_for(self, lambda: self.service.health()['processed'] == 1)
        self.assertEqual(self.service.health()['accepted'], 0)
        self.assertFalse(self.controller.health()['active_session'])
        self.assertEqual(self.controller.health()['samples_in_ram'], 0)

    def test_shadow_can_run_without_any_calibration_collection_and_close_clears(self):
        self.offer()
        self.embedder.release.set()
        wait_for(self, lambda: self.service.health()['accepted'] == 1)
        self.assertEqual(self.controller.health()['samples_in_ram'], 0)
        self.assertTrue(self.service.close(1))
        self.assertTrue(self.controller.health()['closed'])
        self.assertTrue(self.embedder.closed.is_set())

    def test_observer_failure_does_not_turn_shadow_result_into_identity(self):
        self.begin()
        self.controller.accept = lambda *_: (_ for _ in ()).throw(RuntimeError('synthetic observer failure'))
        self.offer()
        self.embedder.release.set()
        wait_for(self, lambda: self.service.health()['accepted'] == 1)
        self.assertEqual(self.service.health()['calibration_observer_errors'], 1)
        self.assertEqual(self.service.health()['failures'], 0)


class PrimaryCalibrationIntegrationTests(unittest.TestCase):
    def test_camera_quality_hook_observes_dpu_output_and_preserves_windows_vector(self):
        import numpy as np
        from board.identity.camera_faces import CameraFaceExtractor
        config = configuration()
        config['dpu_sface_shadow']['compare_cosine'] = False
        config['dpu_sface_calibration'] = {'enabled': True, 'mode': 'CALIBRATION_ONLY', 'control_token': 'f'*64}
        current = key()
        primary = vector(1)
        embedder = Embedder()
        # Embedder's baseline test helper uses a truth test on its value;
        # supply the actual runtime float32 vector after construction instead.
        embedder.value = np.array(vector(), dtype=np.float32)
        remote = SimpleNamespace(RemoteFaceFeatures=lambda _: SimpleNamespace(feature=lambda *_: primary))
        with patch.dict('sys.modules', {'board.identity.remote_features': remote}), patch.object(SFaceShadow,'_make_embedder',return_value=embedder):
            extractor = CameraFaceExtractor(config,face_targets=True,schedule=object(),owner=object(),
                clock=lambda:1000,current_target=lambda:current,guard_lock=threading.RLock())
        self.addCleanup(extractor.close)
        wait_for(self,lambda:extractor.shadow.ready)
        control = extractor.calibration.begin('calibration_gallery','P_A','C_CAMERA_HOOK',current,current)
        image = np.repeat(((np.indices((112,112)).sum(axis=0)%2)*255).astype(np.uint8)[:,:,None],3,axis=2)
        extractor.align_crop = lambda image,_: image
        observation = {'target_kind':'face','face_target':current,'frame_id':1,'captured_mono_ms':1000,
            'face':[0,0,112,112,38.2946,51.6963,73.5318,51.5014,56.0252,71.7366,
                    41.5493,92.3655,70.7299,92.2041,.99]}
        result, reason = extractor.extract(image,observation,current)
        self.assertIs(result,primary)
        self.assertEqual(reason,'')
        wait_for(self,lambda:extractor.calibration.health()['samples_in_ram']==1)
        self.assertGreaterEqual(extractor.enrollment_quality['blur'],40.)
        self.assertEqual(extractor.calibration.health()['templates_written'],0)
        extractor.calibration.end(control['session_token'])


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.controller = CalibrationSession(lambda: self.now, 1000)
        self.addCleanup(self.controller.close)
        self.current = key()
        self.capability = 'a'*64
        self.extractor = SimpleNamespace(calibration=self.controller, shadow=SimpleNamespace(ready=True),
            config={'dpu_sface_calibration': {'enabled': True, 'control_token': self.capability}})
        self.state = SimpleNamespace(lock=threading.RLock(),
            identity=SimpleNamespace(extractor=self.extractor), identity_target=lambda: self.current)
        class Original:
            def do_POST(self): self.respond(299, {'original': True})
            def respond(self, code, value): self.response = (code, value)
        self.handler = wrap_handler(Original, self.state)()
        self.handler.path = PATH
        self.handler.client_address = ('127.0.0.1', 1234)
        self.handler.connection = SimpleNamespace(gettimeout=lambda: None, settimeout=lambda _: None)

    def request(self, action='health', params=None, raw=None, auth=True):
        data = raw if raw is not None else json.dumps({'action': action, 'params': params or {}}).encode()
        self.handler.rfile = io.BytesIO(data)
        self.handler.headers = Message()
        self.handler.headers['Content-Length'] = str(len(data))
        self.handler.headers['Content-Type'] = 'application/json'
        if auth: self.handler.headers['Authorization'] = 'Bearer '+self.capability
        self.handler.do_POST()
        return self.handler.response

    def test_only_new_route_loopback_and_capability_are_accepted(self):
        self.assertEqual(self.request()[0], 200)
        self.assertEqual(self.request(auth=False)[0], 403)
        self.handler.client_address = ('192.168.50.1', 1234)
        self.assertEqual(self.request()[0], 403)
        self.handler.path = '/v1/ui/commands'
        self.assertEqual(self.request()[0], 299)
        self.handler.path = PATH
        self.handler.client_address = ('127.0.0.1', 1234)
        self.extractor.config = {}
        self.assertEqual(self.request()[0], 404)

    def test_start_is_explicit_atomic_and_http_never_accepts_features(self):
        params = {'request_id': 'b'*32, 'purpose': 'calibration_gallery', 'person': 'P_A',
                  'capture_session': 'C_HTTP', 'target': key()}
        code, result = self.request('start', params)
        self.assertEqual(code, 200)
        self.assertIn('session_token', result)
        self.assertEqual(self.request('start', params)[0], 400)
        code, result = self.request('health')
        self.assertEqual(code, 200)
        for forbidden in ('session_token', 'control_token', 'embedding', 'features', 'samples'):
            self.assertNotIn(forbidden, result)
        self.assertNotIn(self.capability, json.dumps(result))
        self.assertEqual(self.request('accept', {'request_id': 'c'*32, 'feature': [0]*128})[0], 400)
        self.assertEqual(self.request('report', {'embedding': [0]*128})[0], 400)

    def test_oversized_duplicate_nonfinite_json_and_not_ready_are_refused(self):
        self.assertEqual(self.request(raw=b' '*4097)[0], 400)
        self.assertEqual(self.request(raw=b'{"action":"health","action":"reset","params":{}}')[0], 400)
        self.assertEqual(self.request(raw=b'{"action":"freeze","params":{"threshold":NaN}}')[0], 400)
        self.assertEqual(self.request(raw=b'{"action":"health","params":{},"feature":[]}')[0], 400)
        self.extractor.shadow.ready = False
        self.assertEqual(self.request('start', {'request_id': 'd'*32, 'purpose': 'calibration_gallery',
             'person': 'P_A', 'capture_session': 'C_NOT_READY', 'target': key()})[0], 400)


if __name__ == '__main__': unittest.main()
