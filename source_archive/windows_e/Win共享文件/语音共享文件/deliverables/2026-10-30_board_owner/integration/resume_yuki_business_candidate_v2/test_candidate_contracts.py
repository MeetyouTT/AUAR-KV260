"""Public synthetic contracts. No GUI/GLES/models/devices/network/private DB.

Uses the real packaged business parsers, context builder, job ACK bridge and
StreamingController with injected in-memory fixtures. No performance claim.
"""
import ast
import copy
from dataclasses import FrozenInstanceError
import hashlib
import importlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock
import uuid

ROOT = Path(__file__).resolve().parent
AURA = ROOT/'candidate/aura'
sys.path.insert(0, str(AURA))

from tools.yuki_business_candidate import (prepare_pair, PairRejected, CharacterSpeechPolicy,
    bind_runtime_pair, create_native_core, native_controller_type, NumericFacials,
    CandidateMonitorChoice, load_private_face_readback, validate_feedback_character,
    LocalRecordText, LocalRecordController)
from tools.native_yuki_candidate import StrictLocalPortrait
from tools.board_persona_candidate import PersonaCandidateRejected
from board.runtime.board_memory_policy import BoardContextBuilder, BoardMemoryCommands
from board.runtime.audio.board_dialogue_jobs import BoardDialogueJobs
from board.runtime.board_dialogue import AudioChunk, BoardReply, PlaybackPlan
from common.model_inference_wire import Owner
from common.voice_channel import ChannelState


def configuration():
    value = json.loads((ROOT/'candidate/yuki_business.config.fragment.json').read_text(encoding='utf-8'))
    value.update(board_business=dict(enabled=True), persistent_audio=True, streaming_conversation=True)
    return value


class Output:
    def __init__(self):
        self.active = self.paused = False
        self.ready = True
        self.duration = 1.
        self.seconds = 0.
        self.track = 'none'
        self.stops = 0
    def position(self): return self.seconds
    def read(self):
        return dict(track=self.track, clock=self.seconds, audible=self.active and not self.paused,
                    answer_clock=self.seconds, answer_started_at=1., started_at=1.)
    def stop(self): self.active = False; self.stops += 1
    def pause(self, value): self.paused = value
    def finished(self): return False


def pair_ready():
    pair = prepare_pair(configuration(), AURA)
    output = Output()
    mailbox = StrictLocalPortrait(output, clock=lambda: 10.)
    pair.attach_mailbox(mailbox)
    mailbox.ready = True  # Native creation alone is intentionally insufficient.
    pair.observe_native_frame(dict(frames=1))  # A simulated successful swap.
    return pair, mailbox, output


class Store:
    def __init__(self):
        self.facts, self.writes, self.preemptions = [], [], 0
    def context(self, scope): return dict(facts=list(self.facts))
    def correct(self, scope, key, value, **kwargs):
        self.writes.append((scope, key, value, kwargs))
        self.facts[:] = [dict(key=key, value=value)]
    def preempt_compaction(self): self.preemptions += 1


class Asr:
    model_sha256 = 'a'*64
    def __init__(self, text='雪妃，今天有点累'): self.text, self.calls = text, 0
    def transcribe(self, *args, **kwargs): self.calls += 1; return self.text


class Controller:
    board_boot_id = 'synthetic-boot'
    idle = True
    def __init__(self, pair, asr):
        self.asr, self.store = asr, Store()
        self.context_builder = BoardContextBuilder(pair.selected_prompt)
        self.command_handler = BoardMemoryCommands(self.store)
        self.calls, self.acks, self.cancels = [], [], []
        self.plans = {}
    def prepare_text(self, text, **kwargs):
        self.calls.append((text, kwargs))
        pcm = b'\x01\x00'*2400
        owner = Owner(uuid.uuid4().hex, self.board_boot_id, kwargs['session_id'], kwargs['generation'])
        plan = PlaybackPlan(self.board_boot_id, kwargs['session_id'], kwargs['generation'], kwargs['turn_id'],
            uuid.uuid4().hex, BoardReply('我在认真听。', 'friendly'),
            (AudioChunk(owner, '我在认真听。', pcm, 24000),), hashlib.sha256(pcm).hexdigest(), 2400, 24000)
        self.plans[plan.turn_id] = plan
        return plan
    def cancel(self, session_id, *, generation): self.cancels.append((session_id, generation)); return True
    def acknowledge(self, plan, **kwargs):
        if kwargs != dict(playback_token=plan.playback_token, sha256=plan.sha256,
                          samples=plan.samples, complete=True):
            raise AssertionError('Complete exact PCM receipt required')
        self.acks.append((plan, kwargs))
        return dict(status='played')


def runtime(pair):
    asr = Asr()
    controller = Controller(pair, asr)
    scope = dict(kind='conversation', id='a'*32)
    jobs = BoardDialogueJobs(controller,
        dict(enabled=True, host='192.168.50.1', port=8797, timeout_ms=30000), 'synthetic-boot',
        scope_provider=lambda meta: scope, wall_clock=lambda: 1793376000., start_worker=False)
    value = types.SimpleNamespace(started=False, closed=False, jobs=jobs, controller=controller,
                                  _foreground_idle=lambda: True)
    bind_runtime_pair(value, pair)
    return value, asr, scope


def clip():
    return types.SimpleNamespace(capture_id=uuid.uuid4().hex, audio=types.SimpleNamespace(sample_count=3200),
                                 pcm=struct.pack('<h', 1000)*3200)


def progress(jobs):
    rows = []
    while True:
        row = jobs.poll()
        if row is None: return rows
        rows.append(row)


class CandidateContracts(unittest.TestCase):
    def test_startup_import_and_public_preflight_do_not_open_resources(self):
        with mock.patch('socket.socket', side_effect=AssertionError('network forbidden')), \
             mock.patch('subprocess.Popen', side_effect=AssertionError('process forbidden')), \
             mock.patch('sqlite3.connect', side_effect=AssertionError('database forbidden')), \
             mock.patch('ctypes.CDLL', side_effect=AssertionError('native library forbidden')):
            importlib.import_module('tools.yuki_business_gui')
            pair = prepare_pair(configuration(), AURA)
            self.assertEqual(pair.state, 'PREPARED')
            self.assertFalse(CandidateMonitorChoice(pair).read())
            self.assertNotIn('gi', sys.modules)

    def test_exact978_byte_prompt_not_stacked_with_review_fragment(self):
        pair = prepare_pair(configuration(), AURA)
        raw = pair.selected_prompt.encode('utf-8')
        self.assertEqual(len(raw), 978)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), '11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e')
        self.assertEqual(pair.identity.formal_name, '御笠雪妃')
        self.assertEqual(pair.identity.romanized_name, 'YUKI MIKASA')
        self.assertNotIn('你是桌面玩偶汐蓝', pair.selected_prompt)

    def test_selection_version_fps_and_single_sink_are_fail_closed(self):
        for change in (dict(native_yuki=dict(configuration()['native_yuki'], fps=8)),
                       dict(portrait_offload=dict(enabled=True)), dict(stable_avatar_fps=8),
                       dict(character_pair=dict(configuration()['character_pair'], profile_version='old')),
                       dict(board_business=dict(enabled=False)), dict(native_avatar=False)):
            with self.subTest(change=change), self.assertRaises(PairRejected):
                prepare_pair(dict(configuration(), **change), AURA)

    def test_no_unpaired_native_profile(self):
        value = configuration(); del value['character_pair']
        with self.assertRaises(PairRejected): prepare_pair(value, AURA)
        self.assertIsNone(prepare_pair({}, AURA))

    def test_asset_hash_change_is_rejected_before_loading_library(self):
        original = Path.read_bytes
        def changed(path):
            raw = original(path)
            return raw+b'x' if path.name == 'libaura_yuki.so' else raw
        with mock.patch.object(Path, 'read_bytes', changed), self.assertRaises(PairRejected):
            prepare_pair(configuration(), AURA)

    def test_readiness_is_actual_first_swap_not_native_constructor(self):
        pair = prepare_pair(configuration(), AURA)
        mailbox = StrictLocalPortrait(Output()); pair.attach_mailbox(mailbox)
        mailbox.ready = True
        self.assertFalse(mailbox.ready)
        with self.assertRaises(PersonaCandidateRejected): pair.require_ready()
        pair.observe_native_frame(dict(frames=1))
        self.assertEqual(pair.require_ready(), pair.selected_prompt)

    def test_one_shot_activation_and_failure_cancel_both_owners(self):
        pair = prepare_pair(configuration(), AURA)
        mailbox = StrictLocalPortrait(Output()); pair.attach_mailbox(mailbox); mailbox.ready = True
        calls = []
        pair.on_ready(lambda: calls.append('start'))
        pair.invalidators.extend((lambda: calls.append('jobs_cancel'), lambda: calls.append('audio_cancel')))
        pair.observe_native_frame(dict(frames=1)); pair.observe_native_frame(dict(frames=2))
        self.assertEqual(calls, ['start'])
        pair.fail('native_unrealized'); pair.fail('again')
        self.assertEqual(calls, ['start','jobs_cancel','audio_cancel'])
        with self.assertRaises(PersonaCandidateRejected): pair.require_ready()
        pair.observe_native_frame(dict(frames=3))
        self.assertEqual(pair.state, 'FAILED')

    def test_raw_asr_literal_name_number_and_negation_preserved(self):
        speech = CharacterSpeechPolicy()
        for text in ('我叫御笠雪妃', '我的朋友叫雪妃', '不要把雪飞改成雪妃', '不是雪妃，是雪飞',
                     '雪妃这个名字怎么写', '计划明天不去，预算是1500', '以前的汐蓝记得什么', '西兰花很好吃'):
            self.assertEqual(speech.prepare(text), dict(raw_text=text, text=text, adjustments=[]))
        self.assertEqual(speech.strip_address('雪妃，帮我登记身份，我叫小林'), '帮我登记身份，我叫小林')
        self.assertEqual(speech.strip_address('御笠雪妃，记住：项目是海风'), '记住：项目是海风')
        self.assertEqual(speech.strip_address('雪妃这个名字怎么写'), '雪妃这个名字怎么写')
        self.assertEqual(speech.strip_address('雪妃长期记住：项目是海风'), '长期记住：项目是海风')

    def test_only_exact_reviewed_names_and_original_interjections_wake(self):
        speech = CharacterSpeechPolicy()
        for text, expected in (('雪妃，在吗', '在吗'), ('御笠雪妃今天好吗','今天好吗'), ('雪妃',''),
                               ('欸，帮我看看','帮我看看'), ('哎',''), ('哎呀',None), ('汐蓝在吗',None),
                               ('西兰在吗',None), ('雪飞在吗',None), ('我叫雪妃',None)):
            self.assertEqual(speech.wake_request(text), expected)
        self.assertEqual(speech.aliases, ())

    def test_new_names_context_and_memory_commands_share_one_pair(self):
        pair, _, _ = pair_ready(); value, _, scope = runtime(pair)
        import common.spoken_input as old_speech
        import board.runtime.board_memory_policy as old_memory
        original_speech, original_name = old_memory.prepare_spoken_input, old_memory.CHARACTER_NAME
        builder = value.controller.context_builder
        text = '西兰你今天好吗'
        messages = builder(dict(messages=[], facts=[], summaries=[]), text)
        self.assertEqual(messages[-1]['content'], text)
        self.assertEqual(messages[0]['content'], pair.selected_prompt)
        command = value.controller.command_handler
        grant_scope = dict(kind='conversation', id=scope['id'])
        result = command('御笠雪妃，记住：项目是海风', grant_scope,
                         turn_id='turn', generation=1, user_event_id='raw-user-event')
        self.assertIn('海风', result.text)
        self.assertIs(value.controller.store.writes[0][0], grant_scope)
        self.assertEqual(value.controller.store.writes[0][3]['source_event_ids'], ('raw-user-event',))
        self.assertIs(old_memory.prepare_spoken_input, original_speech)
        self.assertEqual(old_memory.CHARACTER_NAME, original_name)
        self.assertEqual(old_speech.ALIASES[0], '西兰')

    def test_personal_scope_never_granted_or_rebuilt_by_character_pair(self):
        pair, _, _ = pair_ready(); value, _, scope = runtime(pair)
        command = value.controller.command_handler
        result = command('雪妃，长期记住：项目是海风', scope,
                         turn_id='turn', generation=1, user_event_id='raw')
        self.assertIn('授权', result.text)
        self.assertEqual(value.controller.store.writes, [])
        self.assertFalse(hasattr(pair, 'profile_id'))

    def test_pair_binding_is_before_workers_and_preserves_object_identity(self):
        pair, _, _ = pair_ready(); value, _, _ = runtime(pair)
        store, jobs = value.controller.store, value.jobs
        self.assertIs(value.jobs.controller, value.controller)
        self.assertIs(value.controller.command_handler.original.store, store)
        self.assertIs(value.jobs, jobs)
        with self.assertRaises(PairRejected): bind_runtime_pair(value, pair)

    def test_render_failure_disables_new_asr_and_background_idle(self):
        pair, _, _ = pair_ready(); value, asr, _ = runtime(pair)
        self.assertTrue(value.jobs.enabled()); self.assertTrue(value._foreground_idle())
        pair.fail('renderer_lost')
        self.assertFalse(value.jobs.enabled()); self.assertFalse(value._foreground_idle())
        with self.assertRaises(PersonaCandidateRejected): value.jobs.submit(clip())
        self.assertEqual(asr.calls, 0)

    def test_snow_name_identity_guide_and_memory_prefix_reach_original_routes(self):
        pair, _, _ = pair_ready(); value, _, scope = runtime(pair)
        job = types.SimpleNamespace(scope=scope,
            meta=dict(board_boot_id='synthetic-boot', session_id='s', generation=1, request_id='route'),
            cancelled=threading.Event())
        seen = []
        value.jobs._check = lambda job: None
        value.jobs.special_handlers['identity_enrollment'] = lambda text, **kw: seen.append(text)
        value.jobs.special_handlers['identity_query'] = lambda text, **kw: seen.append(text)
        value.jobs._route(job, '雪妃，帮我登记身份')
        value.jobs._route(job, '御笠雪妃，我是谁')
        self.assertEqual(seen, ['帮我登记身份','我是谁'])
        self.assertEqual(value.jobs._route(job, '汐蓝，帮我登记身份'), (None, None))
        self.assertEqual(seen, ['帮我登记身份','我是谁'])

    def test_stream_packets_raw_asr_and_full_pcm_ack_are_original(self):
        pair, _, _ = pair_ready(); value, asr, _ = runtime(pair)
        jobs = value.jobs; meta = jobs.submit(clip()); self.assertTrue(jobs.run_next())
        rows = progress(jobs)
        self.assertEqual(value.controller.calls[0][0], asr.text)
        channel = ChannelState(meta); audio = b''
        for row in rows:
            event = row.get('channel_event')
            if event:
                channel.accept(event, row.get('pcm', b''))
                if event['kind'] == 'audio': audio += row['pcm']
        network = next(row['network_complete'] for row in rows if 'network_complete' in row)
        self.assertEqual(len(audio), 4800)
        self.assertEqual(hashlib.sha256(audio).hexdigest(), network['pcm_sha256'])
        jobs.acknowledge(meta, network); jobs.drain_actions()
        self.assertEqual(len(value.controller.acks), 1)
        self.assertEqual(value.controller.acks[0][1]['samples'], 2400)

    def test_cancel_rejects_queued_old_full_ack(self):
        pair, _, _ = pair_ready(); value, _, _ = runtime(pair)
        jobs = value.jobs; meta = jobs.submit(clip()); jobs.run_next(); rows = progress(jobs)
        network = next(row['network_complete'] for row in rows if 'network_complete' in row)
        jobs.acknowledge(meta, network)
        pair.fail('renderer_lost'); jobs.drain_actions()
        self.assertEqual(value.controller.acks, [])

    def test_native_mailbox_mouth_uses24k_samples_pause_and_track_ownership(self):
        pair, mailbox, output = pair_ready(); output.active = True
        core = types.SimpleNamespace(talk_gen=4, emotion='friendly', fsm=types.SimpleNamespace(state=types.SimpleNamespace(label='SPEAKING')))
        mailbox.offer(core, 1., .5, .3, 12000, 'answer'); first = mailbox.consume()
        self.assertEqual((first.audio_sample, first.sample_rate, first.playing), (12000,24000,1))
        output.paused = True
        mailbox.offer(core, 1., .5, .3, 12000, 'answer'); paused = mailbox.consume()
        self.assertEqual((paused.audio_sample, paused.paused, paused.playing), (12000,1,0))
        output.paused = False
        mailbox.offer(core, 1., .5, .3, 0, 'feedback'); feedback = mailbox.consume()
        self.assertGreater(feedback.owner, first.owner)
        mailbox.invalidate(); mailbox.consume()
        self.assertTrue(mailbox.offer(core, 1., .5, .3, 13000, 'answer')['_portrait_wait'])
        self.assertIsNone(mailbox.consume())
        core.talk_gen = 5
        mailbox.offer(core, 1., .5, .3, 0, 'answer')
        self.assertIsNotNone(mailbox.consume())

    def test_native_failure_has_no_png_or8fps_fallback(self):
        pair, mailbox, _ = pair_ready()
        mailbox.fail('synthetic GL loss')
        core = types.SimpleNamespace(talk_gen=1)
        self.assertTrue(mailbox.offer(core, 0., 0., 0., 0, 'none')['_portrait_wait'])
        self.assertEqual(mailbox.status()['target_fps'], 16)
        self.assertIsNone(mailbox.status()['fallback_fps'])
        for value in (8,12,24,True):
            with self.assertRaises(PairRejected): mailbox.set_fps(value)
        with self.assertRaises(PairRejected): mailbox.set_enabled(False)

    def test_no_old_png_constructor_or_preload_and_generation_policy_retained(self):
        with mock.patch('tools.realtime_facials.RealtimeFacials', side_effect=AssertionError('old PNG forbidden')), \
             mock.patch('tools.facial_layers.BlinkLayer', side_effect=AssertionError('old eye assets forbidden')), \
             mock.patch('tools.facial_layers.MouthBank', side_effect=AssertionError('old mouth assets forbidden')), \
             mock.patch('tools.idle_body_compositor.IdleBodyTrack', side_effect=AssertionError('old body assets forbidden')):
            core = create_native_core()
            output = Output()
            visual = native_controller_type()(core, types.SimpleNamespace(), output)
            self.assertIsInstance(visual.facials, NumericFacials)
            generation = core.new_turn(); core.cancel()
            self.assertFalse(core.accept_response(generation, dict(reply_text='old', emotion='neutral', avatar_action='')))
            self.assertEqual(core.pool('SPEAKING'), ())
            with self.assertRaises(PairRejected): core.display_frame('IDLE', 0.)

    def test_streaming_pause_cancel_completion_methods_are_inherited(self):
        from tools.streaming_controller import StreamingController
        kind = native_controller_type()
        for name in ('channel_event','channel_complete','take_completion','tick','cancel','toggle_pause'):
            self.assertIs(getattr(kind, name), getattr(StreamingController, name))
        pair, mailbox, output = pair_ready()
        core = create_native_core()
        visual = kind(core, types.SimpleNamespace(), output, clock=lambda: 10.)
        visual.portrait_offload = mailbox
        output.active = True
        visual.toggle_pause(); self.assertTrue(output.paused)
        visual.toggle_pause(); self.assertFalse(output.paused)
        before = core.talk_gen; visual.cancel()
        self.assertGreater(core.talk_gen, before)
        self.assertFalse(output.active)

    def test_unrealize_and_native_error_callbacks_invalidate_the_same_pair(self):
        from tools import native_yuki_candidate
        pair, mailbox, _ = pair_ready(); value, _, _ = runtime(pair)
        class Area:
            def __init__(self): self.callbacks = {}
            def connect(self, name, callback): self.callbacks[name] = callback
        area = Area()
        with mock.patch.object(native_yuki_candidate.original, 'create_gl_area', return_value=area) as factory:
            result = native_yuki_candidate.create_gl_area({}, mailbox, pair)
        self.assertIs(result, area)
        self.assertEqual(result.frame_observer, pair.observe_native_frame)
        result.callbacks['unrealize'](result)
        self.assertEqual(pair.state, 'FAILED')
        self.assertFalse(value.jobs.enabled())
        factory.call_args.kwargs['on_error']('synthetic-native-error')
        self.assertEqual(pair.failure, 'native_unrealized')

    def test_numeric_envelope_matches_existing_sample_clock_interpolation(self):
        from tools.realtime_facials import RealtimeFacials
        envelope = dict(gains=[0., .5, 1., .25], levels=[0., .25, .75, .5], hop_seconds=.02)
        numeric = NumericFacials(None); numeric.begin(envelope)
        old = RealtimeFacials.__new__(RealtimeFacials)
        old.envelope, old.closing = envelope, None
        for seconds in (0., .01, .02, .025, .06, .08, .1):
            for playing in (False, True):
                self.assertEqual(numeric.values(seconds, playing, 10.),
                                 RealtimeFacials.values(old, seconds, playing, 10.))

    def test_microphone_choice_starts_false_and_failure_revokes_ram_enable(self):
        pair, _, _ = pair_ready(); setting = CandidateMonitorChoice(pair)
        self.assertFalse(setting.read())
        setting.write(True); self.assertTrue(setting.read())
        pair.fail('renderer_lost'); self.assertFalse(setting.read())
        with self.assertRaises(PersonaCandidateRejected): setting.write(True)

    def test_private_face_metadata_requires_exact_explicit_pin_and_no_db(self):
        with tempfile.TemporaryDirectory(prefix='yuki-public-metadata-') as directory:
            path = Path(directory)/'face-source.synthetic.json'
            raw = json.dumps(dict(version=1, enabled=True, board_boot_id='synthetic-only',
                                  camera_pid=123, camera_start_ticks='456')).encode()
            path.write_bytes(raw)
            spec = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest())
            with mock.patch('sqlite3.connect', side_effect=AssertionError('DB forbidden')), \
                 mock.patch('board.runtime.audio.face_gallery_readback.FaceGalleryReadback.configured',
                            side_effect=AssertionError('No stale implicit source')):
                readback = load_private_face_readback(spec)
                self.assertEqual(readback.config['camera_start_ticks'], '456')
                with self.assertRaises(PairRejected): load_private_face_readback(dict(spec, sha256='0'*64))
                with self.assertRaises(PairRejected): load_private_face_readback(None)

    def test_existing_voice_reference_is_not_relabelled_as_new_greeting(self):
        old = dict(arrival=dict(reply_text='你好，我是汐蓝。', path='original-reference-unchanged'))
        with self.assertRaises(PairRejected): validate_feedback_character(old)
        self.assertEqual(old['arrival']['reply_text'], '你好，我是汐蓝。')
        self.assertEqual(validate_feedback_character(dict(thinking=dict(reply_text='我想一想。'))),
                         dict(thinking=dict(reply_text='我想一想。')))

    def test_all_core_profile_identity_guide_and_memory_sources_remain_exact(self):
        manifest = json.loads((ROOT/'candidate/manifest.json').read_text(encoding='utf-8'))
        required = ('board/runtime/board_business.py','board/runtime/audio/board_dialogue_jobs.py',
                    'board/runtime/board_memory_policy.py','board/runtime/board_dialogue.py',
                    'tools/board_business_gui.py','board/identity/voice_enrollment.py','common/profile_access.py',
                    'tools/streaming_controller.py','tools/gstreamer_persistent_engine.py')
        for relative in required:
            self.assertEqual(hashlib.sha256((AURA/relative).read_bytes()).hexdigest(),
                             manifest['core_baseline_unchanged_sha256'][relative])
        self.assertEqual(manifest['prompt_utf8_bytes'], 978)
        self.assertFalse(manifest['production_entry_changed'])

    def test_gui_builder_preserves_factory_profile_dialog_and_one_widget_branch(self):
        source = (AURA/'tools/board_avatar_gtk.py').read_text(encoding='utf-8')
        ast.parse(source)
        self.assertIn('self.board_business.bind_recording(recording)', source)
        self.assertIn('self.character_pair.on_ready(self.board_business.activate)', source)
        self.assertIn("recording_options['monitor_settings']=CandidateMonitorChoice", source)
        self.assertIn('self.portrait=self.yuki_portrait', source)
        self.assertNotIn('self.fixed.put(self.yuki_portrait', source)
        selector = (AURA/'tools/profile_selection_ui.py').read_text(encoding='utf-8')
        self.assertIn('local_board_profile_dialog(stage)', selector)

    def test_unmap_is_visible_metric_only_not_readiness_loss_or_fake_fps(self):
        from tools import native_yuki_candidate
        pair, mailbox, _ = pair_ready(); value, _, _ = runtime(pair)
        class Area:
            def __init__(self): self.callbacks = {}
            def connect(self, name, callback): self.callbacks[name] = callback
        area = Area()
        with mock.patch.object(native_yuki_candidate.original, 'create_gl_area', return_value=area):
            native_yuki_candidate.create_gl_area({}, mailbox, pair)
        area.callbacks['map'](area)
        self.assertTrue(native_yuki_candidate.display_status(mailbox)['visible'])
        area.callbacks['unmap'](area)
        state = native_yuki_candidate.display_status(mailbox)
        self.assertFalse(state['visible']); self.assertFalse(state['frame_scheduling_active'])
        self.assertEqual(state['presentation_state'], 'hidden')
        self.assertNotIn('fps', state)
        self.assertTrue(pair.ready_now()); self.assertTrue(value.jobs.enabled())
        area.callbacks['map'](area)
        self.assertEqual(pair.state, 'READY')
        area.callbacks['unrealize'](area)
        self.assertFalse(value.jobs.enabled())


class ActualSpecialRouteContracts(unittest.TestCase):
    """Real LocalIdentityReplies/Controller/Store, only fake public backends."""
    def setUp(self):
        from board.runtime.board_dialogue import BoardDialogueController
        from common.board_memory import BoardMemoryStore
        from common.model_inference_wire import make_response, audio_payload
        self.temporary = tempfile.TemporaryDirectory(prefix='yuki-v2-public-sqlite-')
        self.addCleanup(self.temporary.cleanup)
        self.pair, self.mailbox, self.output = pair_ready()
        class Clock:
            def __call__(self): return 10.
        self.clock = Clock()
        class Timeline:
            def event_time(self): return 1793400000.
        self.timeline = Timeline(); self.timeline.monotonic = self.clock
        class SpyStore(BoardMemoryStore):
            def begin_turn(self, scope, turn_id, user_text, **kwargs):
                self.recorded.append((dict(scope), turn_id, user_text, dict(kwargs)))
                return super().begin_turn(scope, turn_id, user_text, **kwargs)
        self.store = SpyStore(Path(self.temporary.name)/'synthetic-only.sqlite3', clock=self.timeline.event_time)
        self.store.recorded = []
        class Models:
            def __init__(self): self.calls = []
            def request(self, kind, payload, **kwargs):
                self.calls.append((kind, copy.deepcopy(payload)))
                result = (dict(text=json.dumps(dict(reply_text='我在认真听。',emotion='friendly',avatar_action='')))
                          if kind == 'llm' else dict(audio=audio_payload(b'\1\0'*800)))
                return make_response(Owner.from_dict(payload), result=result)
            def cancel(self, owner): pass
        self.models = Models(); self.asr = Asr()
        self.controller = BoardDialogueController(self.store, self.models, board_boot_id='synthetic-boot',
            asr=self.asr, clock=self.clock, system_prompt=self.pair.selected_prompt,
            context_builder=BoardContextBuilder(self.pair.selected_prompt), command_handler=BoardMemoryCommands(self.store))
        self.scope = dict(kind='conversation', id='a'*32)
        self.jobs = BoardDialogueJobs(self.controller,
            dict(enabled=True,host='192.168.50.1',port=8797,timeout_ms=30000), 'synthetic-boot',
            scope_provider=lambda meta: self.scope, wall_clock=self.timeline.event_time,
            clock=self.clock, start_worker=False)
        self.value = types.SimpleNamespace(started=False,closed=False,jobs=self.jobs,
            controller=self.controller,_foreground_idle=lambda: True)
        bind_runtime_pair(self.value, self.pair)
        self.addCleanup(self.jobs.close)

    def say(self, text, *, acknowledge=True):
        self.asr.text = text
        captured = clip()
        if self.jobs.identity_snapshot is not None:
            # Explicit synthetic capture-start scene, same fake monotonic10s.
            # No external camera provider or real process metadata is read.
            self.jobs.capture_owners = {captured.capture_id:self.jobs.identity_snapshot()}
        meta = self.jobs.submit(captured)
        self.assertTrue(self.jobs.run_next())
        rows = progress(self.jobs)
        self.assertFalse([row for row in rows if row.get('error')], rows)
        complete = next(row['network_complete'] for row in rows if 'network_complete' in row)
        if acknowledge:
            self.jobs.acknowledge(meta, complete); self.jobs.drain_actions()
            self.assertTrue(self.jobs.last_ack['committed'])
        return meta, rows, complete

    def assert_raw_record(self, raw, meta):
        rows = self.store.history(self.scope)
        user = [row for row in rows if row['source'] == 'user_said']
        self.assertEqual([row['text'] for row in user], [raw])
        self.assertEqual(len(self.store.recorded), 1)
        self.assertEqual(self.store.recorded[0][2], raw)
        self.assertEqual(self.store.recorded[0][1], meta['request_id'])
        with self.store._db() as db:  # This test's new public synthetic DB only.
            actual = db.execute('SELECT body_hash FROM bm_events WHERE event_id=?', (user[0]['event_id'],)).fetchone()[0]
        self.assertEqual(actual, hashlib.sha256(raw.encode('utf-8')).hexdigest())
        self.assertTrue(any(row['source']=='assistant_played' and row['playback']=='complete' for row in rows))

    def identity_handler(self, *, business=None):
        from board.runtime.board_business import LocalIdentityReplies
        # A synthetic scene, with no real IDs/templates or external camera IO.
        def snapshot():
            key = dict(camera_epoch='synthetic-camera',track_id=1,track_generation=1)
            return dict(protocol_version='aura-ui-1',board_boot_id='synthetic-boot',service_epoch='synthetic-service',
                sequence=1,observed_mono_ms=10000,ttl_ms=2000,source_kind='actual',
                context=dict(session_id='synthetic-camera-session',request_id='',generation=0),
                modules=dict(camera=dict(state='READY'),vision=dict(state='READY',people_count=1),
                    target=dict(state='CONFIRMED',selected=key,tracks=[dict(key=key,label='face')]),
                    identity=dict(state='UNKNOWN',people=[],db_version=0,enrollment_sampling=dict(
                        session_id='',stage='idle',counts=dict(collect=0,validate=0),total=0,total_required=15,
                        detail='waiting',bound_target=None))),
                capabilities=dict(identity_enroll=False,identity_delete=False,identity_sample_start=True,
                                  identity_sample_cancel=False))
        def forbidden_command(command): raise AssertionError('No actual identity commit in this fixture')
        handler = LocalIdentityReplies('synthetic-boot', snapshot, forbidden_command,
                                      clock=self.clock, now_ms=lambda:10000)
        handler.business = business
        self.jobs.identity_snapshot = snapshot
        self.jobs.special_handlers.update(identity_enrollment=handler,identity_query=handler,speaker_identity=handler)
        return handler

    @staticmethod
    def speaker_business(reply=None):
        class Business:
            config = dict(enabled=True)
            def __init__(self): self.seen=[]
            def public(self): return dict(active=False)
            def reset(self): pass
            def route(self, meta, text, pcm, **kwargs): self.seen.append(('route',text)); return None
            def turn(self, meta, text, pcm, **kwargs): self.seen.append(('turn',text)); return reply
        return Business()

    def test_actual_speaker_handler_parses_intent_but_records_full_raw_hash_and_ack(self):
        business = self.speaker_business('这是公开声纹提示测试。')
        self.identity_handler(business=business)
        raw = '雪妃，登记声纹'
        meta, rows, receipt = self.say(raw)
        self.assert_raw_record(raw, meta)
        self.assertEqual(business.seen, [('route','登记声纹'),('turn','登记声纹')])
        self.assertTrue(all(kind=='tts' for kind, _ in self.models.calls))
        self.assertEqual(receipt['sample_count'], 800)

    def test_actual_face_fsm_receives_unprefixed_intent_but_original_user_said(self):
        handler = self.identity_handler()
        raw = '御笠雪妃，帮我登记身份，我叫小林'
        meta, rows, _ = self.say(raw)
        self.assert_raw_record(raw, meta)
        self.assertTrue(handler.public()['active'])
        self.assertIn('称呼是小林', ''.join(row['channel_event'].get('text','') for row in rows if 'channel_event' in row))
        self.assertTrue(all(kind=='tts' for kind, _ in self.models.calls))

    def test_actual_identity_question_keeps_original_address_in_record(self):
        self.identity_handler()
        raw = '雪妃，我是谁'
        meta, rows, _ = self.say(raw)
        self.assert_raw_record(raw, meta)
        answer = ''.join(row['channel_event'].get('text','') for row in rows if 'channel_event' in row)
        self.assertTrue('没有认出' in answer or '请正对摄像头' in answer)
        self.assertTrue(all(kind=='tts' for kind, _ in self.models.calls))

    def test_bare_name_local_sequence_falls_back_once_with_original_raw(self):
        business = self.speaker_business()
        self.identity_handler(business=business)
        raw = '雪妃，我叫小林'
        meta, _, _ = self.say(raw)
        self.assert_raw_record(raw, meta)
        self.assertEqual([kind for kind, _ in self.models.calls], ['llm','tts'])
        self.assertEqual(self.models.calls[0][1]['messages'][-1]['content'], raw)
        self.assertEqual(business.seen, [('route','我叫小林'),('turn','我叫小林')])

    def test_actual_visual_query_keeps_normalized_device_event_and_no_private_raw(self):
        from board.runtime.visual_policy import LocalVisualQueries
        worker = types.SimpleNamespace(store=self.store,timeline=self.timeline,
            scope=dict(kind='device',id='board-camera'),collector=types.SimpleNamespace(allow_fixture=True),
            record_current_observation=lambda:None)
        handler = LocalVisualQueries(self.store, worker, self.timeline)
        self.jobs.visual_intent_matcher = handler.requested
        self.jobs.special_handlers['structured_visual_query'] = handler
        raw = '雪妃，镜头现在有几个人？我的私人暗号是海风'
        meta, _, _ = self.say(raw)
        rows = self.store.history(worker.scope)
        normalized = [row for row in rows if row['source']=='device_event']
        self.assertEqual([row['text'] for row in normalized], ['设备查询意图（规范化）：查询镜头当前人体目标数量。'])
        self.assertFalse(any(row['source']=='user_said' for row in rows))
        self.assertEqual(self.store.history(self.scope), [])
        self.assertNotIn('海风', repr(rows)); self.assertNotIn(raw, repr(self.models.calls))
        self.assertEqual(self.store.recorded[0][0], worker.scope)
        self.assertEqual(self.store.recorded[0][3]['input_source'], 'device_event')
        self.assertIn(dict(field='input_representation',value='normalized_visual_query'), normalized[0]['metadata']['claims'])
        with self.store._db() as db:
            actual = db.execute('SELECT body_hash FROM bm_events WHERE event_id=?', (normalized[0]['event_id'],)).fetchone()[0]
        self.assertEqual(actual, hashlib.sha256(normalized[0]['text'].encode()).hexdigest())
        self.assertNotEqual(actual, hashlib.sha256(raw.encode()).hexdigest())

    def test_local_reply_proxy_immutable_request_owner_and_same_scope_only(self):
        raw = '雪妃，请做公开测试'
        meta = dict(request_id='local-reply',board_boot_id='synthetic-boot',session_id='reply-session',generation=1)
        cancel = threading.Event()
        job = types.SimpleNamespace(scope=self.scope,meta=meta,cancelled=cancel)
        binding = LocalRecordText.capture(job, raw, self.pair.speech)
        proxy = LocalRecordController(self.controller, binding)
        with self.assertRaises(FrozenInstanceError): binding.raw_record_text='changed'
        kwargs = dict(scope=self.scope,session_id=meta['session_id'],generation=1,budget_ms=3000,
                      turn_id=meta['request_id'],cancel_event=cancel)
        with self.assertRaises(PairRejected):
            proxy.prepare_local_reply(binding.intent_text, lambda:BoardReply('不会执行。'),
                                      **dict(kwargs,scope=dict(kind='device',id='board-camera')))
        with self.assertRaises(PairRejected):
            proxy.prepare_local_reply(binding.intent_text, lambda:BoardReply('不会执行。'),
                                      **dict(kwargs,turn_id='different-request'))
        self.assertEqual(self.store.recorded, [])
        plan = proxy.prepare_local_reply(binding.intent_text, lambda:BoardReply('这是公开本地回复。'), **kwargs)
        self.controller.acknowledge(plan,playback_token=plan.playback_token,sha256=plan.sha256,samples=plan.samples)
        self.assert_raw_record(raw, meta)

    def test_request_bindings_do_not_share_latest_text_or_equal_grant_ids(self):
        grant = object()
        scope = dict(kind='profile',id='b'*32,grant=grant)
        first = types.SimpleNamespace(scope=scope,meta=dict(request_id='first',board_boot_id='synthetic-boot',
            session_id='s',generation=1),cancelled=threading.Event())
        second = types.SimpleNamespace(scope=scope,meta=dict(request_id='second',board_boot_id='synthetic-boot',
            session_id='s',generation=2),cancelled=threading.Event())
        a = LocalRecordText.capture(first, '雪妃，第一条公开请求', self.pair.speech)
        b = LocalRecordText.capture(second, '雪妃，第二条公开请求', self.pair.speech)
        self.assertEqual(a.raw_record_text, '雪妃，第一条公开请求')
        self.assertEqual(b.raw_record_text, '雪妃，第二条公开请求')
        self.assertIs(dict(a.scope_items)['grant'], grant)
        self.assertTrue(a.same_scope(dict(scope)))
        self.assertFalse(a.same_scope(dict(scope,grant=object())))
        self.assertFalse(a.same_scope(dict(scope,id='c'*32)))
        self.assertNotEqual(a.owner, b.owner)

    def test_real_special_turn_render_cancel_invalidates_queued_complete_ack(self):
        self.identity_handler(business=self.speaker_business('这是公开声纹提示测试。'))
        raw = '雪妃，登记声纹'
        meta, _, complete = self.say(raw, acknowledge=False)
        self.jobs.acknowledge(meta, complete)
        self.pair.fail('synthetic-render-context-loss')
        self.jobs.drain_actions()
        rows = self.store.history(self.scope)
        self.assertEqual([row['text'] for row in rows if row['source']=='user_said'], [raw])
        self.assertFalse(any(row['source']=='assistant_played' for row in rows))
        self.assertFalse(self.jobs.last_ack and self.jobs.last_ack.get('committed'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
