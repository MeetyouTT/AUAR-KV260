"""Public synthetic regression runner for the two-source stability candidate."""
from __future__ import annotations

import ast
import copy
from contextlib import contextmanager, nullcontext
import hashlib
import importlib.abc
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parents[1]
BASE = REPAIR / 'feature_trigger_collaboration/board_integration_v17/local_runtime_v17'
MAPPING_PATH = REPAIR / 'release_v18_minor_ui_candidate/minor_evidence/source_mapping.json'
MAPPING = json.loads(MAPPING_PATH.read_text(encoding='utf-8'))
PINS = MAPPING['component_pins']
OVERRIDES = {
    'tools.board_avatar_gtk': HERE / 'after/tools/board_avatar_gtk.py',
    'tools.board_recording': HERE / 'after/tools/board_recording.py',
}
for relative in ('board/runtime/board_business.py', 'common/board_production_bootstrap.py',
                 'tools/production_board_business_gui.py'):
    path = REPAIR / 'cold_boot_recovery_candidate/after' / relative
    assert hashlib.sha256(path.read_bytes()).hexdigest() == PINS[relative]
    OVERRIDES[relative[:-3].replace('/', '.')] = path
CURRENT_RUNTIME = REPAIR / 'feature_trigger_collaboration/candidate_m03_v90_stage/public_runtime_v90'
for relative, digest in PINS.items():
    if not relative.endswith('.py'):
        continue
    name = relative[:-3].replace('/', '.')
    baseline_source = BASE / relative
    if name in OVERRIDES or not baseline_source.is_file():
        continue
    if hashlib.sha256(baseline_source.read_bytes()).hexdigest() != digest:
        current_source = CURRENT_RUNTIME / relative
        assert hashlib.sha256(current_source.read_bytes()).hexdigest() == digest
        OVERRIDES[name] = current_source


class CandidateImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        source = OVERRIDES.get(fullname)
        if source is not None:
            return importlib.util.spec_from_file_location(fullname, source)
        return None


sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE))
sys.meta_path.insert(0, CandidateImports())

from tools.board_recording import RecordingController
from tools.voice_first_recording import VoiceFirstRecordingController
from tools.realtime_controller import RealtimeController
from tools.selected_voice_service import SpeechJobs
from tests.framework import test_board_recording as original_recording
from tests.framework import test_automatic_conversation as original_automatic
from tests.framework.test_simple_enrollment import snapshot as original_scene
from common.voice_channel import ChannelState
from board.runtime.board_dialogue import StaleGeneration


def load_previous_recording():
    spec = importlib.util.spec_from_file_location('baseline_board_recording',
        HERE / 'before/tools/board_recording.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.RecordingController


PreviousRecording = load_previous_recording()
OBSERVATIONS = {}


class Clock:
    def __init__(self, now=1.):
        self.now = now

    def __call__(self):
        return self.now


class QueueTranscriber(original_automatic.FakeTranscriber):
    def __init__(self, events=()):
        super().__init__()
        self.events = list(events)
        self.polls = 0
        self.selections = []
        self.social_assets = {}

    def poll(self):
        self.polls += 1
        return self.events.pop(0) if self.events else None

    def select_conversation(self, *, resume):
        self.selections.append(resume)

    def capture_started(self, capture_id):
        pass


class Player(original_automatic.FakeController):
    def __init__(self, clock=None, packet_cost=0.):
        super().__init__()
        self.clock = clock
        self.packet_cost = packet_cost
        self.events = []
        self.cancel_count = 0
        self.on_event = None
        self.channel = None
        self.network = None
        self.network_owner = None
        self.finished_playing = False

    def cancel(self):
        self.cancel_count += 1
        super().cancel()

    def channel_event(self, header, pcm, owner, feedback_assets, requested_at):
        if self.channel is not None:
            self.channel.accept(header, pcm)
        self.events.append(header['kind'])
        if self.clock is not None:
            self.clock.now += self.packet_cost
        if self.on_event is not None:
            self.on_event(header, owner)

    def channel_complete(self, owner, result):
        self.network = result
        self.network_owner = owner

    def take_completion(self):
        if self.finished_playing and self.network is not None:
            value = (self.network_owner, self.network)
            self.network = None
            return value
        return super().take_completion()


OWNER = dict(request_id='public-request', capture_id='public-capture')


def event(kind='audio', owner=None):
    return dict(context=dict(owner or OWNER), channel_event=dict(kind=kind), pcm=b'\0\0' * 480)


def polling_owner(events, *, controller_type=RecordingController, cost=0.):
    clock = Clock()
    tx = QueueTranscriber(events)
    player = Player(clock, cost)
    recording = controller_type(player, transcriber=tx, clock=clock)
    recording.transcription.update(OWNER, state='TRANSCRIBING')
    recording.requested_at = clock()
    return recording, tx, player, clock


@contextmanager
def deterministic_time(clock):
    with patch('time.monotonic', clock), patch('time.perf_counter', clock):
        yield


def gtk_option(name, *, version, business):
    tree = ast.parse((HERE / version / 'tools/board_avatar_gtk.py').read_text(encoding='utf-8'))
    values = [value for node in ast.walk(tree) if isinstance(node, ast.Dict)
              for key, value in zip(node.keys, node.values)
              if isinstance(key, ast.Constant) and key.value == name]
    assert len(values) == 1
    return eval(compile(ast.Expression(values[0]), '<actual GTK option>', 'eval'),
                {'self': SimpleNamespace(board_business=business)})


def business(origin):
    return SimpleNamespace(runtime=SimpleNamespace(config=SimpleNamespace(data_origin=origin)))


def attention(clock, sequence):
    value = original_scene()
    now = round(clock() * 1000)
    value.update(observed_mono_ms=now, sequence=sequence)
    key = dict(camera_epoch='camera', track_id=1, track_generation=1)
    value['modules']['identity'].update(target_kind='face', face_count=1, face_target=key,
        face_targets=[dict(key=key, label='face')], face_attention=dict(version=1,
            target=key, frame_id=sequence, captured_mono_ms=now, ttl_ms=1000,
            yaw_ratio=0., roll_degrees=0., frontal=True))
    return value


def voice_first(version):
    clock = Clock()
    source = [attention(clock, 1)]
    tx = QueueTranscriber()
    tx.social_assets = {'arrival': dict(path=str(HERE / 'synthetic-immutable-cue/public.wav'),
                                        sha256='a' * 64)}
    jobs = SpeechJobs.__new__(SpeechJobs)
    jobs.root = HERE / 'synthetic-selected-voice-root'
    receiver = SimpleNamespace(jobs=jobs)
    player = Player()
    player.submit_generated = lambda value, **kwargs: RealtimeController.submit_generated(
        receiver, value, **kwargs)
    recording = VoiceFirstRecordingController(player, transcriber=tx, clock=clock,
        boot_id='boot', attention_provider=lambda: copy.deepcopy(source[0]),
        capture_factory=original_automatic.FakeCapture,
        auto_capture_factory=original_automatic.FakeCapture,
        barge_capture_factory=lambda: None, barge_enabled=False,
        device_observer=gtk_option('device_observer', version=version, business=business('board')),
        visual_social=gtk_option('visual_social', version=version, business=business('board')),
        wake_word_required=False)
    return recording, tx, player, clock, source


class SocialTests(unittest.TestCase):
    def test_current_production_reproduces_actual_cache_rejection_after_capture_cancel(self):
        owner, tx, player, clock, source = voice_first('before')
        self.addCleanup(owner.close)
        owner.tick()
        self.assertEqual(owner.capture.state, 'RECORDING')
        clock.now = 1.7
        source[0] = attention(clock, 2)
        with self.assertRaisesRegex(ValueError, 'local content-hash cache'):
            owner.tick()
        self.assertEqual(owner.capture.state, 'CANCELLED')
        self.assertEqual(tx.cancelled, 2)
        self.assertEqual(owner.social_count, 0)
        OBSERVATIONS['old_social_failure'] = dict(error_class='ValueError',
            capture_state_after_error='CANCELLED', actual_import_generated=True)

    def test_production_social_disabled_keeps_direct_listener_armed(self):
        owner, tx, player, clock, source = voice_first('after')
        self.addCleanup(owner.close)
        owner.tick()
        initial_cancels = tx.cancelled
        for sequence in range(2, 42):
            clock.now += 1.
            source[0] = attention(clock, sequence)
            owner.tick()
        self.assertEqual(owner.capture.state, 'RECORDING')
        self.assertEqual(owner.capture.counter, 1)
        self.assertEqual(tx.cancelled, initial_cancels)
        self.assertEqual(player.cancel_count, 0)
        self.assertFalse(owner.social_enabled)
        self.assertFalse(owner.wake_word_required)
        self.assertTrue(owner.monitor_enabled)
        self.assertIsNotNone(owner.observer)
        self.assertEqual(owner.monitor_stats['armed'], 1)
        self.assertEqual(owner.monitor_stats['submitted'], 0)
        OBSERVATIONS['new_social_quiet_ticks'] = dict(ticks=41, seconds=40,
            capture_starts=1, spontaneous_cancels=0, direct_listener=True)

    def test_only_production_social_option_changes(self):
        for origin in (None, 'synthetic'):
            value = None if origin is None else business(origin)
            self.assertTrue(gtk_option('visual_social', version='after', business=value))
        self.assertFalse(gtk_option('visual_social', version='after', business=business('board')))
        self.assertTrue(gtk_option('device_observer', version='after', business=business('board')))


class DrainTests(unittest.TestCase):
    def test_25hz_consumer_meets_50_packets_per_second_with_measured_cost_range(self):
        rows = []
        for cost in (.0045, .0065, .008):
            results = {}
            for label, controller_type in (('before', PreviousRecording), ('after', RecordingController)):
                owner, tx, player, clock = polling_owner([event() for _ in range(500)],
                    controller_type=controller_type, cost=cost)
                with deterministic_time(clock):
                    for tick in range(25):
                        clock.now = 1. + tick / 25
                        owner._poll_transcription()
                results[label] = len(player.events)
                owner.close()
            self.assertGreaterEqual(results['after'], 50)
            rows.append(dict(event_cost_ms=cost * 1000, tick_hz=25, **results))
        self.assertEqual(rows[1]['before'], 25)
        self.assertEqual(rows[1]['after'], 50)
        OBSERVATIONS['deterministic_packet_capacity'] = rows

    def test_batch_has_eight_event_limit(self):
        owner, tx, player, clock = polling_owner([event() for _ in range(40)])
        self.addCleanup(owner.close)
        with deterministic_time(clock):
            owner._poll_transcription()
        self.assertEqual(tx.polls, 8)
        self.assertEqual(len(player.events), 8)

    def test_budget_is_checked_between_events(self):
        owner, tx, player, clock = polling_owner([event() for _ in range(40)], cost=.007)
        self.addCleanup(owner.close)
        start = clock()
        with deterministic_time(clock):
            owner._poll_transcription()
        self.assertEqual(tx.polls, 2)
        self.assertAlmostEqual(clock() - start, .014)
        OBSERVATIONS['budget_boundary'] = '12ms checked before the next event; current event may finish after deadline'

    def test_error_stops_same_owner_audio_control_end_and_future_poll(self):
        values = [dict(context=OWNER, error='PUBLIC_SYNTHETIC_FAILURE'),
                  event('audio'), event('control'), event('end')]
        owner, tx, player, clock = polling_owner(values)
        self.addCleanup(owner.close)
        with deterministic_time(clock):
            owner._poll_transcription()
            owner._poll_transcription()
        self.assertEqual(tx.polls, 1)
        self.assertEqual(len(tx.events), 3)
        self.assertEqual(player.events, [])
        self.assertEqual(player.cancel_count, 1)
        self.assertEqual(owner.transcription['state'], 'ERROR')

    def test_cancel_stops_next_event_and_next_tick(self):
        owner, tx, player, clock = polling_owner([event(), event('control'), event('end')])
        self.addCleanup(owner.close)
        player.on_event = lambda header, meta: owner.cancel()
        with deterministic_time(clock):
            owner._poll_transcription()
            owner._poll_transcription()
        self.assertEqual(tx.polls, 1)
        self.assertEqual(player.events, ['audio'])
        self.assertEqual(owner.transcription['state'], 'CANCELLED')

    def test_permission_exception_stops_batch(self):
        owner, tx, player, clock = polling_owner([event(), event('control'), event('end')])
        self.addCleanup(owner.close)
        def denied(header, meta):
            raise PermissionError('PUBLIC_SYNTHETIC_REVOKED')
        player.on_event = denied
        with deterministic_time(clock), self.assertRaises(PermissionError):
            owner._poll_transcription()
        self.assertEqual(tx.polls, 1)
        self.assertEqual(len(tx.events), 2)

    def test_foreign_owner_is_dropped_and_next_current_event_is_delivered(self):
        owner, tx, player, clock = polling_owner([
            event(owner=dict(request_id='old', capture_id='old')), event()])
        self.addCleanup(owner.close)
        with deterministic_time(clock):
            owner._poll_transcription()
        self.assertEqual(player.events, ['audio'])

    def test_nonstandard_local_state_and_no_audio_end_are_not_whitelisted_out(self):
        owner, tx, player, clock = polling_owner([event('end'),
            dict(context=OWNER, network_complete=dict(public_synthetic=True))])
        self.addCleanup(owner.close)
        owner.transcription['state'] = 'LOCAL_ENROLLMENT_PROGRESS'
        with deterministic_time(clock):
            owner._poll_transcription()
        self.assertEqual(player.events, ['end'])
        self.assertIsNotNone(player.network)
        self.assertEqual(tx.ack_calls, [])
        player.finished_playing = True
        owner.tick()
        self.assertEqual(tx.ack_calls, [OWNER])


class Timeline:
    boot_id = 'test-boot'

    def event_time(self):
        return 1793400000.

    def safe_for_compaction(self):
        return True

    def compaction_guard(self):
        return nullcontext()

    def quality_snapshot(self):
        return {'status': 'verified'}


class InferenceFixture:
    host, port = '192.168.50.1', 8797

    def __init__(self):
        self.calls = []

    def request(self, kind, payload, **kwargs):
        from common.model_inference_wire import Owner, make_response, audio_payload
        self.calls.append(kind)
        result = dict(text=json.dumps(dict(reply_text='这是公开测试回答。', emotion='friendly',
                                          avatar_action=''), ensure_ascii=False))
        if kind == 'tts':
            result = dict(audio=audio_payload(b'\x01\x00' * 2400, 24000))
        return make_response(Owner.from_dict(payload), result=result)

    def cancel(self, owner):
        pass


class AsrFixture:
    model_sha256 = 'a' * 64

    def __init__(self, text):
        self.text = text

    def transcribe(self, pcm, **kwargs):
        return self.text


def public_bundle(root, text):
    from board.runtime.board_business import BoardBusinessRuntime, BoardBusinessConfig
    from common.conversation_selection import ConversationSelection
    clock = Clock(10.)
    client = InferenceFixture()
    value = original_scene()
    value.update(board_boot_id='test-boot', observed_mono_ms=10000)
    bundle = BoardBusinessRuntime(BoardBusinessConfig(str(root / 'public-synthetic'),
        (1793300000., 1793500000.)), 'test-boot', asr=AsrFixture(text),
        system_prompt='只输出三个字段JSON。',
        conversation_selection=ConversationSelection(root / 'public-conversation.json'),
        timeline=Timeline(), client=client, clock=clock,
        identity_snapshot=lambda: copy.deepcopy(value),
        identity_command=lambda command: dict(accepted=True, command_id=command['command_id']))
    bundle.jobs.select_conversation(resume=False)
    bundle.jobs.capture_owners['public-capture'] = copy.deepcopy(value)
    return bundle, clock, client


class RealBoardAckTests(unittest.TestCase):
    def test_ordinary_local_and_identity_streams_keep_actual_full_receipt(self):
        rows = []
        for route, text, expected_calls in (
                ('ordinary', '今天聊点什么', ['llm', 'tts']),
                ('local_memory', '查看本次对话记忆', ['tts']),
                ('identity_enrollment', '帮我登记身份，我叫小林', ['tts', 'tts'])):
            with self.subTest(route=route), tempfile.TemporaryDirectory(prefix='public-stability-') as temp:
                bundle, clock, client = public_bundle(Path(temp), text)
                try:
                    checks = []
                    original_checker = bundle.store.prepared_turn_checker
                    @contextmanager
                    def counted_checker(*args, **kwargs):
                        with original_checker(*args, **kwargs) as check:
                            def counted():
                                checks.append(True)
                                return check()
                            yield counted
                    bundle.store.prepared_turn_checker = counted_checker
                    pcm = struct.pack('<h', 1000) * 3200
                    clip = SimpleNamespace(capture_id='public-capture', pcm=pcm,
                        audio=SimpleNamespace(sample_count=3200))
                    meta = bundle.jobs.submit(clip)
                    self.assertTrue(bundle.jobs.run_next())
                    player = Player()
                    player.channel = ChannelState(meta)
                    recording = RecordingController(player, transcriber=bundle.jobs, clock=clock)
                    recording.transcription.update(state='TRANSCRIBING', **{
                        key: meta[key] for key in ('capture_id', 'request_id')})
                    recording.requested_at = clock()
                    for _ in range(50):
                        recording.tick()
                        if player.network is not None:
                            break
                    self.assertNotEqual(recording.transcription['state'], 'ERROR')
                    self.assertIsNotNone(player.network)
                    self.assertTrue(player.channel.ended)
                    self.assertEqual(player.channel.samples, 2400 * client.calls.count('tts'))
                    self.assertIsNone(bundle.jobs.last_ack)
                    self.assertEqual(client.calls, expected_calls)
                    receipt = dict(player.network)
                    with self.assertRaises((ValueError, StaleGeneration)):
                        bundle.jobs.acknowledge(meta, dict(receipt, sample_count=1))
                    self.assertIsNone(bundle.jobs.last_ack)
                    player.finished_playing = True
                    recording.tick()
                    self.assertEqual(recording.transcription['state'], 'ANSWERED')
                    self.assertIsNone(bundle.jobs.last_ack)
                    bundle.jobs.drain_actions()
                    self.assertTrue(bundle.jobs.last_ack['committed'])
                    self.assertEqual(bundle.jobs.last_ack['request_id'], meta['request_id'])
                    if route == 'ordinary':
                        self.assertGreaterEqual(len(checks), player.events.count('audio'))
                    rows.append(dict(route=route, audio_packets=player.events.count('audio'),
                        source_guard_calls=len(checks), full_ack=True, partial_ack_rejected=True,
                        inference_calls=list(client.calls)))
                finally:
                    bundle.close()
        OBSERVATIONS['real_board_jobs_and_receipts'] = rows


def source_audit():
    result = []
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, '__file__', None)
        if not path:
            continue
        path = Path(path).resolve()
        relative = name.replace('.', '/') + '.py'
        if relative not in PINS:
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        expected = PINS[relative]
        if name in ('tools.board_recording', 'tools.board_avatar_gtk'):
            expected = hashlib.sha256(OVERRIDES[name].read_bytes()).hexdigest()
        if actual != expected:
            raise AssertionError('Imported source differs from current mapping: ' + relative)
        result.append(dict(source=relative, sha256=actual))
    return result


def main():
    suite = unittest.TestSuite()
    loader = unittest.defaultTestLoader
    for case in (SocialTests, DrainTests, RealBoardAckTests,
                 original_recording.RecordingTests, original_recording.RoutingTests,
                 original_automatic.EndpointTests, original_automatic.AutomaticOwnerTests,
                 original_automatic.AutomaticRoutingTests):
        suite.addTests(loader.loadTestsFromTestCase(case))
    output = io.StringIO()
    # The archived tests use __new__; supply fields now normally set by GTK init.
    stage_type = original_recording.BoardAvatarStage
    with patch.object(stage_type, 'character_pair', None, create=True), \
            patch.object(stage_type, 'board_business', None, create=True), \
            patch.object(stage_type, 'config', {}, create=True):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    imported = source_audit()
    report = dict(status='PASS' if result.wasSuccessful() else 'FAIL', tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        baseline_startup_sha256=MAPPING['startup_sha256'],
        source_mapping_sha256=hashlib.sha256(MAPPING_PATH.read_bytes()).hexdigest(),
        public_synthetic_only=True, actual_inference=False, actual_audio_device=False,
        gtk_constructor='actual option AST expressions with actual VoiceFirstRecordingController',
        archived_routing_fixture_defaults=['character_pair=None', 'board_business=None', 'config={}'],
        measurements='deterministic simulation, no wall-clock performance claim',
        imported_source_pins=imported, observations=OBSERVATIONS,
        tests=[str(test) for test, _ in result.failures + result.errors])
    (HERE / 'TEST_RESULT.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'TEST_OUTPUT.txt').write_text(output.getvalue(), encoding='utf-8')
    print(output.getvalue())
    print(json.dumps({key: report[key] for key in ('status', 'tests_run', 'failures', 'errors', 'skipped')}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
