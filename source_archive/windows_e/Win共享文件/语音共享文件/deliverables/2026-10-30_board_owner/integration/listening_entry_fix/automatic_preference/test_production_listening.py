"""Real paired VoiceFirst controller; only device/transport owners are fakes."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / 'production_business_overlay' / 'candidate' / 'aura'
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('production_listening_under_test',
    HERE / 'after/aura/tools/production_listening.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from common.handsfree_settings import HandsFreeSettings
from tools.formal_yuki import paired_recording_type
from tools.voice_first_recording import VoiceFirstRecordingController
from tools.yuki_business_candidate import CandidateMonitorChoice


class Pair:
    def __init__(self):
        self.ready = False
        self.invalidators = []
    def ready_now(self):
        return self.ready
    def require_ready(self):
        if not self.ready:
            raise RuntimeError('Native first swap not ready')


class Capture:
    def __init__(self, *args, **kwargs):
        self.state = 'IDLE'
        self.starts = 0
        self.error = ''
    def start(self):
        self.starts += 1
        self.state = 'RECORDING'
        return 'fake-capture-' + str(self.starts)
    def snapshot(self):
        return dict(state=self.state, error=self.error, sample_count=0,
                    speech_active=False, input_ready=self.state == 'RECORDING')
    def cancel(self):
        self.state = 'CANCELLED'
    def close(self):
        self.cancel()


class Transcriber:
    def __init__(self):
        self.feedback_ready = True
        self.available = True
        self.pending = False
        self.selections = []
    def enabled(self):
        return self.available
    def public(self):
        return dict(enabled=self.available, streaming=True, pending=self.pending,
                    feedback_ready=self.feedback_ready)
    def select_conversation(self, *, resume):
        self.selections.append(resume)
    def cancel(self):
        self.pending = False
    def capture_started(self, capture_id):
        pass
    def poll(self):
        return None
    def close(self):
        self.cancel()


class Controller:
    def __init__(self):
        self.last_error = ''
        self.state = dict(phase='IDLE', playing=False, paused=False,
                          pending_job=None, audio_output_state='IDLE_READY')
    def public(self):
        return dict(self.state)
    def tick(self):
        pass
    def take_completion(self):
        return None
    def cancel(self):
        self.state.update(phase='IDLE', playing=False, paused=False, pending_job=None)


class ListeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        if os.name != 'nt':
            self.root.chmod(0o700)
        self.now = [10.]
        self.visual_calls = 0

    def make(self, *, ready=False, started=False, bind=True, settings=None):
        pair = Pair()
        pair.ready = ready
        tx = Transcriber()
        settings = settings or module.ProductionMonitorChoice(self.root)
        kind = paired_recording_type(VoiceFirstRecordingController, pair)
        def visual():
            self.visual_calls += 1
            raise AssertionError('Ordinary voice must not query visual readiness')
        owner = kind(Controller(), transcriber=tx, boot_id='fake-boot',
            clock=lambda: self.now[0], monitor_settings=settings, early_listen=False,
            attention_provider=visual, auto_capture_factory=Capture,
            barge_capture_factory=lambda: self.fail('No barge capture expected'),
            barge_enabled=False, device_observer=False, visual_social=False)
        self.addCleanup(owner.close)
        business = SimpleNamespace(character_pair=pair, recording=owner,
            runtime=SimpleNamespace(started=started, closed=False,
                config=SimpleNamespace(data_origin='board')))
        if bind:
            module.bind_automatic_listening(owner, business, pair)
        return owner, business, tx, pair

    def test_first_start_auto_arms_only_after_native_and_runtime_start(self):
        owner, business, tx, pair = self.make()
        self.assertTrue(owner.monitor_enabled)
        owner.tick()
        self.assertIsNone(owner.capture)
        pair.ready = True
        owner.tick()
        self.assertIsNone(owner.capture)
        business.runtime.started = True
        owner.tick()
        self.assertEqual(owner.capture.starts, 1)
        self.assertEqual(owner.capture.state, 'RECORDING')
        self.assertEqual(tx.selections, [False])
        owner.tick()
        self.assertEqual(owner.capture.starts, 1)
        state = owner.public()['handsfree_dialogue']
        self.assertTrue(state['microphone_open'])
        self.assertFalse(state['visual_required'])
        self.assertEqual(self.visual_calls, 0)
        self.assertFalse((self.root / 'listening_preference.json').exists())

    def test_runtime_before_native_still_never_opens_capture(self):
        owner, business, tx, pair = self.make(started=True)
        for _ in range(3):
            owner.tick()
        self.assertIsNone(owner.capture)
        self.assertEqual(tx.selections, [])
        pair.ready = True
        owner.tick()
        self.assertEqual(owner.capture.starts, 1)

    def test_original_feedback_and_enabled_readiness_remain(self):
        owner, business, tx, pair = self.make(ready=True, started=True)
        tx.feedback_ready = False
        owner.tick()
        self.assertIsNone(owner.capture)
        tx.feedback_ready = True
        tx.available = False
        owner.tick()
        self.assertIsNone(owner.capture)
        tx.available = True
        owner.tick()
        self.assertEqual(owner.capture.starts, 1)

    def test_user_pause_survives_restart_and_explicit_resume_persists(self):
        owner, business, tx, pair = self.make(ready=True, started=True)
        owner.tick()
        owner.handsfree_toggle()
        path = self.root / 'listening_preference.json'
        self.assertFalse(HandsFreeSettings(path).read())
        self.assertFalse(owner.monitor_enabled)
        self.assertEqual(owner.capture.state, 'CANCELLED')
        owner.close()
        restarted, _, _, _ = self.make(ready=True, started=True)
        self.now[0] += 30
        restarted.tick()
        self.assertFalse(restarted.monitor_enabled)
        self.assertIsNone(restarted.capture)
        restarted.handsfree_toggle()
        self.assertTrue(HandsFreeSettings(path).read())
        self.now[0] += 1
        restarted.tick()
        self.assertEqual(restarted.capture.starts, 1)

    def test_service_error_retries_without_overwriting_user_choice(self):
        path = self.root / 'listening_preference.json'
        HandsFreeSettings(path).write(True)
        before = path.read_bytes()
        owner, _, _, _ = self.make(ready=True, started=True)
        owner.tick()
        owner.capture.state, owner.capture.error = 'ERROR', 'synthetic capture failure'
        owner.tick()
        self.assertEqual(owner.monitor_reason, 'SERVICE_ERROR')
        self.assertTrue(owner.monitor_enabled)
        self.assertEqual(path.read_bytes(), before)
        self.now[0] += 6
        owner.tick()
        self.assertEqual(owner.capture.starts, 2)
        self.assertEqual(path.read_bytes(), before)

    def test_internal_cancel_and_close_do_not_persist_a_user_pause(self):
        path = self.root / 'listening_preference.json'
        HandsFreeSettings(path).write(True)
        before = path.read_bytes()
        owner, _, _, _ = self.make(ready=True, started=True)
        owner.tick()
        owner.cancel()
        self.assertFalse(owner.monitor_enabled)
        self.assertEqual(path.read_bytes(), before)
        owner.close()
        self.assertEqual(path.read_bytes(), before)
        restarted, _, _, _ = self.make(ready=True, started=True)
        restarted.tick()
        self.assertEqual(restarted.capture.starts, 1)

    def test_temporary_native_readiness_loss_closes_owned_capture(self):
        owner, business, tx, pair = self.make(ready=True, started=True)
        owner.tick()
        pair.ready = False
        owner.tick()
        self.assertEqual(owner.capture.state, 'CANCELLED')
        self.assertTrue(owner.monitor_enabled)
        self.assertFalse((self.root / 'listening_preference.json').exists())
        pair.ready = True
        self.now[0] += 6
        owner.tick()
        self.assertEqual(owner.capture.starts, 2)

    def test_malformed_saved_preference_stays_paused_without_rewrite(self):
        path = self.root / 'listening_preference.json'
        path.write_text('{"enabled":true}', encoding='utf-8')
        if os.name != 'nt':
            path.chmod(0o600)
        before = path.read_bytes()
        owner, _, _, _ = self.make(ready=True, started=True)
        owner.tick()
        self.assertFalse(owner.monitor_enabled)
        self.assertEqual(owner.monitor_reason, 'LISTENING_PREFERENCE_UNAVAILABLE')
        self.assertIsNone(owner.capture)
        self.assertEqual(path.read_bytes(), before)

    def test_candidate_keeps_ram_only_explicit_start(self):
        pair = Pair()
        pair.ready = True
        choice = CandidateMonitorChoice(pair)
        owner, _, _, _ = self.make(ready=True, started=True, settings=choice, bind=False)
        owner.tick()
        self.assertFalse(owner.monitor_enabled)
        self.assertIsNone(owner.capture)
        self.assertFalse((self.root / 'listening_preference.json').exists())

    def test_production_binding_rejects_synthetic_and_double_binding(self):
        owner, business, _, pair = self.make(bind=False)
        business.runtime.config.data_origin = 'synthetic'
        with self.assertRaises(ValueError):
            module.bind_automatic_listening(owner, business, pair)
        business.runtime.config.data_origin = 'board'
        module.bind_automatic_listening(owner, business, pair)
        with self.assertRaises(ValueError):
            module.bind_automatic_listening(owner, business, pair)

    def test_same_process_stop_is_not_automatically_overridden_on_later_tick(self):
        owner, _, _, _ = self.make(ready=True, started=True)
        owner.tick()
        owner.handsfree_toggle()
        for _ in range(4):
            self.now[0] += 30
            owner.tick()
        self.assertFalse(owner.monitor_enabled)
        self.assertEqual(owner.capture.starts, 1)
        self.assertFalse(HandsFreeSettings(self.root / 'listening_preference.json').read())

    def test_preference_validation_failure_still_stops_capture_on_user_pause(self):
        owner, _, _, _ = self.make(ready=True, started=True)
        owner.tick()
        with patch.object(owner.monitor_settings, '_check', side_effect=ValueError('fixture unsafe path')):
            owner.handsfree_toggle()
        self.assertFalse(owner.monitor_enabled)
        self.assertEqual(owner.capture.state, 'CANCELLED')
        self.assertIn('暂停设置未能保存', owner.monitor_error)


class OverlayTests(unittest.TestCase):
    def test_current_dependencies_match_fresh_pins_and_python39_ast(self):
        pins = json.loads((HERE.parent / 'source_before_manifest.json').read_text(encoding='utf-8'))
        for name in ('tools/voice_first_recording.py', 'tools/board_recording.py'):
            self.assertEqual(hashlib.sha256((SOURCE / name).read_bytes()).hexdigest(), pins[name]['sha256'])
        for path in (HERE / 'after/aura').rglob('*.py'):
            ast.parse(path.read_text(encoding='utf-8'), feature_version=(3, 9))

    def test_gtk_binds_before_owner_and_presentation_while_candidate_branch_survives(self):
        source = (HERE / 'after/aura/tools/board_avatar_gtk.py').read_text(encoding='utf-8')
        ctor = source.index('            recording=recording_type(')
        bind = source.index('                    bind_automatic_listening(recording,')
        presentation = source.index('                bind_presentation(self,recording)')
        worker = source.index('            self.controller = AvatarRenderWorker(recording,')
        self.assertLess(ctor, bind)
        self.assertLess(bind, presentation)
        self.assertLess(presentation, worker)
        self.assertIn("recording_options['monitor_settings']=CandidateMonitorChoice(self.character_pair)", source)
        self.assertIn("set_label('暂停聆听' if handsfree.get('enabled') else '开始聆听')", source)


if __name__ == '__main__':
    unittest.main()
