"""Public-source confirmation gate reproduction; synthetic local SQLite only."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
import unittest
import uuid

HERE = Path(__file__).resolve().parent
WORKFLOW = HERE.parent
RUNTIME = WORKFLOW.parent / 'start_sync_fix/candidate_runtime'
sys.path.insert(0, str(RUNTIME))
ROUTER = WORKFLOW / 'unified_identity_binding.current_a6d4.py'
assert hashlib.sha256(ROUTER.read_bytes()).hexdigest() == '85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809'
assert hashlib.sha256((RUNTIME / 'common/identity_links.py').read_bytes()).hexdigest() == 'e623e5d15f81f5f66505b6345c6f807270409fea67a60f506c61e1f021b7150b'
spec = importlib.util.spec_from_file_location('confirm_review_public_router', ROUTER)
router_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router_module)
from common.identity_links import IdentityLinkRegistry, ReceiptAuthority
from common.speaker_visual import unavailable, validate_visual

FACE = dict(store_id='synthetic-face-store', model_id='synthetic-face-model', revision=2)
VOICE = dict(store_id='synthetic-voice-store', model_id='synthetic-voice-model', revision=0)


def pcm(seed):
    return bytes((seed, 0)) * 4800


def meta(seed, **changes):
    raw = pcm(seed)
    return dict(protocol='aura-asr-1', board_boot_id='synthetic-boot', session_id='synthetic-session',
                request_id='request-' + str(seed), capture_id='capture-' + str(seed), generation=seed,
                sample_count=len(raw)//2, pcm_sha256=hashlib.sha256(raw).hexdigest(), budget_ms=60000,
                **changes)


def visual(owner, **changes):
    evidence = dict(service_epoch='synthetic-service', camera_epoch='synthetic-camera',
        target=dict(camera_epoch='synthetic-camera', track_id=1, track_generation=1), gallery_revision=2,
        face_identity_id=None, boundary_start_ms=1000, boundary_end_ms=4000, checked_ms=4000,
        source_start_ms=990, source_end_ms=3990, frame_start=1, frame_end=2)
    evidence.update(changes)
    return dict(version=1, context=dict(owner), source_kind='actual', state='FACE_AT_CAPTURE_BOUNDARIES',
                reason='NOT_ACTIVE_SPEAKER_PROOF', evidence=evidence)


class Clock:
    def __init__(self): self.now = 1000.
    def __call__(self): return self.now


class Registry(IdentityLinkRegistry):
    """Observe original exceptions without altering the confirmation policy."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.confirm_errors = []
        self.before_confirm = None

    def confirm(self, *args, **kwargs):
        if self.before_confirm is not None: self.before_confirm()
        try:
            return super().confirm(*args, **kwargs)
        except (ValueError, TimeoutError) as error:
            self.confirm_errors.append((type(error).__name__, str(error)))
            raise


class ConfirmGateTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.root = HERE / 'synthetic_results' / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        assert self.root.resolve().is_relative_to(HERE.resolve())
        self.registry = Registry(self.root / 'synthetic-links.sqlite3',
            ReceiptAuthority(b'synthetic-key-not-used-by-production-'*2), clock=self.clock)
        self.router = router_module.UnifiedBindingRouter(self.registry, None,
            face_gallery=lambda:dict(FACE), voice_gallery=lambda:dict(VOICE))
        self.origin = meta(1)
        result = self.router.route(self.origin, '记住我，我叫合成测试', pcm(1), visual=visual(self.origin))
        self.attempt = result['attempt_id']
        self.assertEqual(result['route'], 'face_exchange')
        self.assertEqual(self.state(), 'AWAIT_CONFIRMATION')

    def state(self, owner=None):
        return self.registry.attempt(self.attempt, owner or meta(2))['state']

    def route(self, owner=None, evidence=None, raw=None, text='确认登记'):
        owner = owner or meta(2)
        return self.router.route(owner, text, pcm(2) if raw is None else raw,
                                 visual=visual(owner) if evidence is None else evidence)

    def assert_generic_face_error_keeps_attempt(self, result):
        self.assertEqual(result['reason'], 'BINDING_CONFIRMATION_VISUAL_UNAVAILABLE')
        self.assertEqual(result['route'], 'device_reply')
        self.assertEqual(self.state(), 'AWAIT_CONFIRMATION')
        self.assertIn(self.router.actor(self.origin), self.router.active)
        with self.registry._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM modality_links').fetchone()[0], 0)

    def test_distinct_capture_with_own_visual_reaches_original_face_workflow(self):
        result = self.route()
        self.assertEqual(result['route'], 'face_exchange')
        self.assertEqual(self.state(), 'SAMPLING_FACE')
        self.assertEqual(self.registry.confirm_errors, [])

    def test_previous_capture_visual_is_rejected_but_new_fresh_capture_can_retry(self):
        self.assert_generic_face_error_keeps_attempt(self.route(evidence=visual(self.origin)))
        self.assertEqual(self.registry.confirm_errors[-1], ('ValueError', 'Foreign visual owner'))
        result = self.route(meta(3), visual(meta(3)), pcm(3))
        self.assertEqual(result['route'], 'face_exchange')
        self.assertEqual(self.state(meta(3)), 'SAMPLING_FACE')

    def test_unavailable_face_retains_pending_attempt_instead_of_exiting(self):
        self.assert_generic_face_error_keeps_attempt(self.route(evidence=unavailable(meta(2), 'NO_SINGLE_FACE')))
        self.assertIn('Fresh single face', self.registry.confirm_errors[-1][1])

    def test_stale_boundary_evidence_uses_same_generic_message(self):
        self.assert_generic_face_error_keeps_attempt(self.route(evidence=visual(meta(2), checked_ms=8000)))
        self.assertEqual(self.registry.confirm_errors[-1][1], 'Expired or unordered face boundary evidence')

    def test_current_visual_budget_must_match_this_capture_context(self):
        wrong = visual(meta(2)); wrong['context']['budget_ms'] = 59999
        self.assert_generic_face_error_keeps_attempt(self.route(evidence=wrong))
        self.assertEqual(self.registry.confirm_errors[-1][1], 'Foreign visual owner')

    def test_reused_request_id_is_not_a_visual_failure_but_gets_same_message(self):
        owner = meta(2); owner['request_id'] = self.origin['request_id']
        self.assert_generic_face_error_keeps_attempt(self.route(owner, visual(owner)))
        self.assertEqual(self.registry.confirm_errors[-1][1], 'Confirmation must be a distinct capture')

    def test_reused_capture_id_is_not_a_visual_failure_but_gets_same_message(self):
        owner = meta(2); owner['capture_id'] = self.origin['capture_id']
        self.assert_generic_face_error_keeps_attempt(self.route(owner, visual(owner)))
        self.assertEqual(self.registry.confirm_errors[-1][1], 'Confirmation must be a distinct capture')

    def test_reused_pcm_is_not_a_visual_failure_but_gets_same_message(self):
        owner = meta(2); owner['pcm_sha256'] = self.origin['pcm_sha256']
        self.assert_generic_face_error_keeps_attempt(self.route(owner, visual(owner), pcm(1)))
        self.assertEqual(self.registry.confirm_errors[-1][1], 'Confirmation must be a distinct capture')

    def test_lifecycle_mismatch_has_different_reason_and_cancels(self):
        result = self.route(evidence=visual(meta(2), target=dict(camera_epoch='synthetic-camera',track_id=2,track_generation=1)))
        self.assertEqual(result['reason'], 'FACE_LIFECYCLE_CHANGED')
        self.assertEqual(result['route'], 'face_exchange')
        self.assertEqual(self.state(), 'CANCELLED')
        self.assertNotIn(self.router.actor(self.origin), self.router.active)
        self.assertEqual(self.registry.confirm_errors, [])

    def test_gallery_revision_change_still_cancels_before_any_commit(self):
        result = self.route(evidence=visual(meta(2), gallery_revision=3))
        self.assertEqual(result['reason'], 'FACE_LIFECYCLE_CHANGED')
        self.assertEqual(self.state(), 'CANCELLED')

    def test_expired_before_routing_is_terminal_not_generic_visual_error(self):
        self.clock.now += 181
        result = self.route()
        self.assertEqual(result['reason'], 'EXPIRED')
        self.assertEqual(result['route'], 'ordinary_skip_speaker')
        self.assertEqual(self.registry.confirm_errors, [])

    def test_expiry_race_between_row_read_and_confirm_is_mislabeled_visual(self):
        self.registry.before_confirm = lambda:setattr(self.clock, 'now', self.clock.now+181)
        result = self.route()
        self.assertEqual(result['reason'], 'BINDING_CONFIRMATION_VISUAL_UNAVAILABLE')
        self.assertEqual(self.state(), 'EXPIRED')
        self.assertEqual(self.registry.confirm_errors[-1][1], 'Binding is not awaiting confirmation')

    def test_registry_busy_at_confirmation_uses_same_visual_error(self):
        locked, release = threading.Event(), threading.Event()
        def hold():
            with self.registry.lock:
                locked.set(); release.wait(1)
        worker = threading.Thread(target=hold)
        def block():
            worker.start(); self.assertTrue(locked.wait(.5))
        self.registry.before_confirm = block
        try:
            result = self.route()
        finally:
            release.set(); worker.join(1)
        self.assert_generic_face_error_keeps_attempt(result)
        self.assertEqual(self.registry.confirm_errors[-1][0], 'TimeoutError')

    def test_changed_name_requires_new_consent_without_confirmation(self):
        result = self.route(text='我叫另一个合成名')
        self.assertEqual(result['reason'], 'NAME_CHANGE_REQUIRES_NEW_CONSENT')
        self.assertEqual(self.state(), 'AWAIT_CONFIRMATION')
        self.assertEqual(self.registry.confirm_errors, [])

    def test_non_confirmation_keeps_original_confirmation_prompt(self):
        result = self.route(text='好的')
        self.assertEqual(result['reason'], 'FACE_CONFIRMATION_PENDING')
        self.assertEqual(self.state(), 'AWAIT_CONFIRMATION')


if __name__ == '__main__':
    unittest.main(verbosity=2)
