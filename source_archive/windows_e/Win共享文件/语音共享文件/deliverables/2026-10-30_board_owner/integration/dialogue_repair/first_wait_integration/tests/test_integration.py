"""Pinned actual client/controller/constructor with synthetic devices and models."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[4]
AURA = PROJECT / 'aura'
sys.path.insert(0, str(AURA))
import common
import tools
import board.runtime


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = load('common.inference_output_contract', ROOT / 'after/common/inference_output_contract.py')
wire = load('common.model_inference_wire', ROOT / 'after/common/model_inference_wire.py')
adapter = load('board.runtime.compact_request_adapter', ROOT / 'after/board/runtime/compact_request_adapter.py')
client_module = load('board.runtime.board_dialogue_client', ROOT / 'after/board/runtime/board_dialogue_client.py')
selection = load('tools.production_output_format', ROOT / 'after/tools/production_output_format.py')
dialogue = load('first_wait_actual_board_dialogue', ROOT / 'before/board/runtime/board_dialogue.py')
PROMPT = '公开合成人格，仅输出reply_text、emotion、avatar_action三字段JSON。'
CAPS = dict(format_contract_version=1, output_formats=['json', 'dialogue_schema_v1', 'dialogue_abc_v1'])
CANONICAL = '{"reply_text":"公开合成答复。","emotion":"friendly","avatar_action":""}'
COMPACT = '{"a":"公开合成答复。","b":"friendly","c":""}'


def payload(**extra):
    value = dict(protocol_version=1, request_id='public-request', board_boot_id='public-boot',
                 session_id='public-session', generation=1, budget_ms=10000, task='dialogue',
                 messages=[dict(role='system', content=PROMPT), dict(role='user', content='原话reply_text不改')],
                 options={})
    value.update(extra)
    return value


class Transport:
    host, port = '192.168.50.1', 8797
    def __init__(self, capabilities=None, reply=None):
        self.capabilities = copy.deepcopy(capabilities)
        self.calls, self.cancelled = [], []
        self.reply, self.hook = reply, None
        self.clock = lambda: 10.

    def output_format_capabilities(self):
        return copy.deepcopy(self.capabilities)

    def request(self, kind, body, *, deadline, cancelled):
        self.calls.append((kind, body, deadline, cancelled))
        if self.hook:
            self.hook(kind, body)
        if kind == 'llm':
            text = self.reply or (COMPACT if body['options'].get('output_format') == 'dialogue_abc_v1' else CANONICAL)
            result = dict(text=text)
        else:
            result = dict(audio=wire.audio_payload(b'\x01\x00' * 160, 24000))
        return wire.make_response(wire.Owner.from_dict(body), result=result)

    def cancel(self, owner):
        self.cancelled.append(owner)


class Socket:
    def __init__(self, peer): self.peer = peer
    def getpeername(self): return self.peer
    def shutdown(self, *_): pass
    def close(self): pass


class Response:
    status = 200
    def __init__(self, body): self.raw = json.dumps(body).encode()
    def getheaders(self):
        return [('Date', 'Sat, 31 Oct 2026 18:00:00 GMT'), ('Content-Type', 'application/json'),
                ('Content-Length', str(len(self.raw)))]
    def read(self, maximum): return self.raw[:maximum]
    def close(self): pass


class Connection:
    def __init__(self, host, port, body, calls, *, peer=None):
        self.host, self.port, self.body, self.calls = host, port, body, calls
        self.peer, self.sock = peer or (host, port), None
    def connect(self): self.sock = Socket(self.peer)
    def request(self, method, path, **kwargs): self.calls.append((method, path))
    def getresponse(self): return Response(self.body)
    def close(self): pass


def health_client(body, *, peer=None):
    calls = []
    factory = lambda host, port, **kw: Connection(host, port, body, calls, peer=peer)
    client = client_module.InferenceHttpClient('192.168.50.1', 8797,
                                               clock=lambda: 10., connection_factory=factory)
    timeline = types.SimpleNamespace(source_id=client.health_date_source_id(), monotonic=client.clock,
                                     boot_id='public-boot')
    def observe(sample, **kwargs):
        if not client.validate_sample(sample):
            raise AssertionError('actual Date source proof not accepted')
        return {'safe_for_compaction': True}
    timeline.observe_http_date = observe
    return client, timeline, calls


def health_body(capabilities=CAPS):
    return dict(protocol_version=1, ok=True, role='model_inference_only', backend=copy.deepcopy(capabilities))


class HealthTests(unittest.TestCase):
    def test_no_capability_before_or_additional_request_after_existing_date_sample(self):
        client, timeline, calls = health_client(health_body())
        self.assertIsNone(client.output_format_capabilities())
        client.sample_health_date(timeline, deadline=20.)
        self.assertEqual(client.output_format_capabilities(), CAPS)
        detached = client.output_format_capabilities()
        detached['output_formats'].clear()
        for _ in range(10):
            self.assertEqual(client.output_format_capabilities(), CAPS)
        self.assertEqual(calls, [('GET', '/health')])

    def test_legacy_invalid_or_unknown_capability_never_grants_compact(self):
        for caps in (None, {}, {'format_contract_version': True, 'output_formats': ['json', 'dialogue_abc_v1']},
                     {'format_contract_version': 2, 'output_formats': ['json', 'dialogue_abc_v1']},
                     {'format_contract_version': 1, 'output_formats': 'dialogue_abc_v1'},
                     {'format_contract_version': 1, 'output_formats': ['json', 'json']},
                     {'format_contract_version': 1, 'output_formats': ['json', 'future_format']},
                     {'format_contract_version': 1, 'output_formats': ['dialogue_abc_v1']}):
            with self.subTest(caps=caps):
                client, timeline, _ = health_client(health_body(caps))
                client.sample_health_date(timeline, deadline=20.)
                self.assertIsNone(client.output_format_capabilities())

    def test_wrong_peer_or_role_keeps_capability_unavailable(self):
        for body, peer in ((health_body(), ('192.168.50.9', 8797)),
                           (dict(health_body(), role='other_role'), None)):
            with self.subTest(peer=peer):
                client, timeline, _ = health_client(body, peer=peer)
                with self.assertRaises(client_module.ModelRequestError):
                    client.sample_health_date(timeline, deadline=20.)
                self.assertIsNone(client.output_format_capabilities())

    def test_clock_failure_or_cancel_does_not_publish_health_capability(self):
        for cause in ('clock', 'cancel'):
            with self.subTest(cause=cause):
                client, timeline, _ = health_client(health_body())
                cancelled = threading.Event()
                original = timeline.observe_http_date
                def observe(sample, **kwargs):
                    original(sample, **kwargs)
                    if cause == 'clock': raise ValueError('synthetic rejected clock')
                    cancelled.set()
                    return {}
                timeline.observe_http_date = observe
                with self.assertRaises((ValueError, InterruptedError)):
                    client.sample_health_date(timeline, deadline=20., cancelled=cancelled.is_set)
                self.assertIsNone(client.output_format_capabilities())

    def test_existing_idle_refresh_can_downgrade_to_legacy_without_extra_io(self):
        body = health_body()
        client, timeline, calls = health_client(body)
        client.sample_health_date(timeline, deadline=20.)
        body.pop('backend')
        client.sample_health_date(timeline, deadline=20.)
        self.assertIsNone(client.output_format_capabilities())
        self.assertEqual(len(calls), 2)


class RoutingTests(unittest.TestCase):
    def test_default_json_and_legacy_host_keep_exact_request(self):
        for mode, caps in (('json', CAPS), ('dialogue_abc_v1', None),
                           ('dialogue_abc_v1', {'format_contract_version': 1, 'output_formats': ['json']})):
            with self.subTest(mode=mode, caps=caps):
                raw = Transport(caps)
                chosen = selection.NegotiatedDialogueClient(raw, system_prompt=PROMPT, mode=mode)
                body = payload()
                before = copy.deepcopy(body)
                chosen.request('llm', body, deadline=20., cancelled=lambda: False)
                self.assertIs(raw.calls[0][1], body)
                self.assertEqual(body, before)
                self.assertEqual(chosen.public()['negotiated_dialogue_format'], 'json')

    def test_compact_changes_only_static_contract_and_restores_whole_json(self):
        raw = Transport(CAPS)
        chosen = selection.NegotiatedDialogueClient(raw, system_prompt=PROMPT, mode='dialogue_abc_v1')
        body = payload()
        body['messages'].insert(1, dict(role='assistant', content='历史含reply_text、emotion、avatar_action'))
        before = copy.deepcopy(body)
        cancelled = lambda: False
        result = chosen.request('llm', body, deadline=20., cancelled=cancelled)
        sent = raw.calls[0][1]
        self.assertEqual(sent['options'], {'output_format': 'dialogue_abc_v1'})
        self.assertEqual(sent['messages'][1:], before['messages'][1:])
        self.assertEqual(sent['messages'][0]['content'], '公开合成人格，仅输出a、b、c三字段JSON。')
        self.assertEqual(body, before)
        self.assertEqual(json.loads(result['result']['text']), json.loads(CANONICAL))
        self.assertEqual(raw.calls[0][2], 20.)
        self.assertIs(raw.calls[0][3], cancelled)

    def test_summary_thinking_and_different_static_prompt_keep_original_semantics(self):
        for extra in ({'task': 'summary'}, {'options': {'think': True}},
                      {'messages': [dict(role='system', content=PROMPT + '变更'),
                                    dict(role='user', content='公开问题')]}):
            with self.subTest(extra=extra):
                raw = Transport(CAPS, reply=CANONICAL)
                chosen = selection.NegotiatedDialogueClient(raw, system_prompt=PROMPT, mode='dialogue_abc_v1')
                body = payload(**extra)
                chosen.request('llm', body, deadline=20., cancelled=lambda: False)
                self.assertEqual(raw.calls[0][1], body)
                self.assertNotIn('output_format', raw.calls[0][1]['options'])

    def test_tts_cancel_and_raw_date_hooks_are_forwarded(self):
        raw = Transport(CAPS)
        raw.date_marker = object()
        chosen = selection.NegotiatedDialogueClient(raw, system_prompt=PROMPT, mode='dialogue_abc_v1')
        body = dict(protocol_version=1, request_id='public-tts', board_boot_id='public-boot',
                    session_id='public-session', generation=1, budget_ms=10000, text='公开台词')
        chosen.request('tts', body, deadline=20., cancelled=lambda: False)
        owner = wire.Owner.from_dict(body)
        chosen.cancel(owner)
        self.assertEqual(raw.calls[0][1], body)
        self.assertEqual(raw.cancelled, [owner])
        self.assertIs(chosen.date_marker, raw.date_marker)

    def test_invalid_compact_output_fails_once_without_model_retry(self):
        for response in ('{"a":"部分', '{"a":"公开。","a":"重复。","b":"friendly","c":""}',
                         '{"a":"公开。","b":"unsupported","c":""}'):
            with self.subTest(response=response):
                raw = Transport(CAPS, reply=response)
                chosen = selection.NegotiatedDialogueClient(raw, system_prompt=PROMPT, mode='dialogue_abc_v1')
                with self.assertRaises(contract.OutputContractError):
                    chosen.request('llm', payload(), deadline=20., cancelled=lambda: False)
                self.assertEqual(len(raw.calls), 1)

    def test_cancel_after_complete_response_prevents_compact_delivery(self):
        cancelled = threading.Event()
        raw = Transport(CAPS)
        raw.hook = lambda *args: cancelled.set()
        chosen = selection.NegotiatedDialogueClient(raw, system_prompt=PROMPT, mode='dialogue_abc_v1')
        with self.assertRaises(InterruptedError):
            chosen.request('llm', payload(), deadline=20., cancelled=cancelled.is_set)
        self.assertEqual(len(raw.calls), 1)

    def test_latest_verified_downgrade_uses_json_even_after_previous_compact(self):
        raw = Transport(CAPS)
        chosen = selection.NegotiatedDialogueClient(raw, system_prompt=PROMPT, mode='dialogue_abc_v1')
        chosen.request('llm', payload(), deadline=20., cancelled=lambda: False)
        raw.capabilities = None
        original = payload(request_id='public-next')
        chosen.request('llm', original, deadline=20., cancelled=lambda: False)
        self.assertIs(raw.calls[-1][1], original)
        self.assertNotIn('output_format', original['options'])

    def test_config_is_only_the_two_explicit_modes(self):
        for bad in (None, True, 1, '', 'dialogue_schema_v1', 'DIALOGUE_ABC_V1'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                selection.validate_dialogue_output_format(bad)


class Store:
    def __init__(self): self.events, self.rows, self.valid = [], {}, True
    def preempt_compaction(self): self.events.append('preempt')
    def begin_turn(self, scope, turn_id, text, *, generation, metadata):
        self.rows[turn_id] = dict(status='generating', text=text)
        self.events.append('begin')
        return {'user_event_id': 'public-user-source'}
    def context(self, *args, **kwargs): return dict(messages=[], facts=[])
    def generated(self, turn_id, text, **kwargs):
        self.rows[turn_id].update(status='awaiting_playback', assistant=text)
        self.events.append('generated')
    def check_prepared_turn_current(self, turn_id, **kwargs):
        self.events.append('durable_check')
        if not self.valid: raise PermissionError('synthetic scope revoked')
        return True
    def bind_audio_receipt(self, *args, **kwargs): self.events.append('bound')
    def ack_played(self, turn_id, **kwargs):
        self.events.append('heard' if kwargs['complete'] else 'interrupted')
        return dict(status='played' if kwargs['complete'] else 'interrupted')
    def interrupt(self, *args, **kwargs): self.events.append('interrupted')


class Builder:
    system_prompt = PROMPT
    def __call__(self, context, text, history):
        return [dict(role='system', content=PROMPT), dict(role='user', content=text)]


def actual_controller(reply=None):
    store, raw = Store(), Transport(CAPS, reply=reply)
    controller = dialogue.BoardDialogueController(store, raw, board_boot_id='public-boot',
        system_prompt=PROMPT, context_builder=Builder(), clock=lambda: 10.)
    runtime = types.SimpleNamespace(controller=controller, client=raw, started=False, closed=False,
                                     jobs=types.SimpleNamespace(thread=None), summary=types.SimpleNamespace(client=raw))
    chosen = selection.install_dialogue_output(runtime, mode='dialogue_abc_v1', system_prompt=PROMPT)
    return runtime, chosen, store, raw


class ControllerTests(unittest.TestCase):
    def test_actual_full_controller_canonicalizes_then_generates_then_complete_ack(self):
        runtime, chosen, store, raw = actual_controller()
        sink = []
        plan = runtime.controller.prepare_text('公开问题', scope=dict(kind='conversation', id='a'*32),
            session_id='public-session', generation=1, budget_ms=10000,
            chunk_sink=lambda *args: sink.append(args))
        self.assertEqual(plan.reply.text, '公开合成答复。')
        self.assertEqual(plan.sample_rate, 24000)
        self.assertEqual([call[0] for call in raw.calls], ['llm', 'tts'])
        self.assertEqual(len(sink), 1)
        self.assertIn('durable_check', store.events)
        self.assertNotIn('heard', store.events)
        self.assertIs(runtime.summary.client, raw)
        self.assertIs(runtime.client, raw)
        runtime.controller.acknowledge(plan, playback_token=plan.playback_token, sha256=plan.sha256,
                                       samples=plan.samples, complete=True)
        self.assertEqual(store.events[-1], 'heard')

    def test_actual_controller_bad_compact_has_no_generated_tts_or_audio(self):
        runtime, _, store, raw = actual_controller('{"a":"incomplete')
        emitted = []
        with self.assertRaises(contract.OutputContractError):
            runtime.controller.prepare_text('公开问题', scope=dict(kind='conversation', id='b'*32),
                session_id='public-session', generation=1, budget_ms=10000,
                chunk_sink=lambda *args: emitted.append(args))
        self.assertEqual([call[0] for call in raw.calls], ['llm'])
        self.assertEqual(emitted, [])
        self.assertNotIn('generated', store.events)
        self.assertNotIn('heard', store.events)

    def test_actual_controller_still_honors_durable_revocation_after_tts(self):
        runtime, _, store, raw = actual_controller()
        raw.hook = lambda kind, body: setattr(store, 'valid', False) if kind == 'tts' else None
        with self.assertRaises(PermissionError):
            runtime.controller.prepare_text('公开问题', scope=dict(kind='conversation', id='c'*32),
                session_id='public-session', generation=1, budget_ms=10000,
                chunk_sink=lambda *args: self.fail('revoked audio delivered'))
        self.assertNotIn('heard', store.events)

    def test_binding_refuses_started_wrong_prompt_or_replaced_client(self):
        for change in ('started', 'prompt', 'client'):
            with self.subTest(change=change):
                raw = Transport(CAPS)
                controller = types.SimpleNamespace(idle=True, model_client=raw, context_builder=Builder())
                runtime = types.SimpleNamespace(started=False, closed=False, controller=controller,
                                                 client=raw, jobs=types.SimpleNamespace(thread=None))
                if change == 'started': runtime.started = True
                if change == 'prompt': controller.context_builder = types.SimpleNamespace(system_prompt='different')
                if change == 'client': controller.model_client = object()
                with self.assertRaises(ValueError):
                    selection.install_dialogue_output(runtime, mode='dialogue_abc_v1', system_prompt=PROMPT)


class ConstructorTests(unittest.TestCase):
    def run_constructor(self, mode, caps, *, invalid=False):
        events = []
        raw = Transport(None)
        runtime = types.SimpleNamespace(started=False, closed=False, jobs=types.SimpleNamespace(
            thread=None, conversation_selection=types.SimpleNamespace(before_publish=None)),
            client=raw, bootstrap_proof={}, store=object(),
            controller=types.SimpleNamespace(idle=True, model_client=raw, context_builder=Builder()),
            summary=types.SimpleNamespace(client=raw))
        def initialize_clock(**kwargs):
            events.append('health_date')
            raw.capabilities = copy.deepcopy(caps)
        runtime.initialize_clock = initialize_clock
        class Base:
            def capture_idle(self): return True
            def close(self): events.append('close')
        pool = types.SimpleNamespace(close=lambda: None, gate=object())
        gui_stub = types.ModuleType('tools.board_business_gui')
        gui_stub.GuiBoardBusiness, gui_stub.BoardBusinessConfig = Base, lambda *a, **kw: object()
        gui_stub.create_board_business_runtime = lambda *a, **kw: runtime
        gui_stub.ConversationSelection = lambda *a: object()
        def feedback(): return {}
        gui_stub.local_feedback_provider = lambda *a: feedback
        yuki = types.ModuleType('tools.yuki_business_candidate')
        yuki.bind_runtime_pair = lambda *a: events.append('pair')
        readback = types.SimpleNamespace(config={}, verify=lambda *a: None)
        yuki.load_private_face_readback = lambda *a: readback
        yuki.selected_feedback_provider = lambda *a: feedback
        yuki.validate_feedback_character = lambda *a: None
        bootstrap = types.ModuleType('common.board_production_bootstrap')
        bootstrap.verify_production_bootstrap = lambda *a: {}
        bootstrap.register_anonymous_conversation = lambda *a: None
        asr = types.ModuleType('board.runtime.audio.board_asr')
        def make_asr(*a, **kw):
            events.append('asr_ctor')
            return object()
        asr.BoardParaformer = make_asr
        frontend = types.ModuleType('tools.production_frontend_selection')
        frontend.validate_frontend_options = lambda value: ('combined', -10)
        frontend.create_frontend_pool = lambda *a, **kw: pool
        channel = types.ModuleType('board.runtime.audio.channel_jobs')
        channel.ChannelConversationJobs = types.SimpleNamespace(_identity_command=None)
        profile = types.ModuleType('tools.profile_control')
        profile.access_from_config = lambda *a: object()
        modules = {module.__name__: module for module in (gui_stub, yuki, bootstrap, asr, frontend, channel, profile)}
        with patch.dict(sys.modules, modules):
            module = load('first_wait_actual_gui_factory', ROOT / 'after/tools/production_board_business_gui.py')
            module.ProductionGuiBoardBusiness._attach_speaker = lambda *a: events.append('speaker')
            runtime.jobs.prepare_feedback = lambda: events.append('feedback')
            with tempfile.TemporaryDirectory() as temp:
                cue = Path(temp) / 'public_feedback.json'
                cue.write_bytes(b'{}')
                value = dict(enabled=True, private_root='/not-accessed', utc_bounds=[0, 1], data_origin='board',
                    asr_directory='/not-loaded', frontend_directory='/not-loaded', feedback_manifest=str(cue),
                    feedback_manifest_sha256=hashlib.sha256(b'{}').hexdigest(), bootstrap_receipt='/not-read',
                    bootstrap_receipt_sha256='a'*64, speaker={}, resume_saved_conversation=False)
                if mode is not None: value['dialogue_output_format'] = mode
                stage = types.SimpleNamespace(character_pair=types.SimpleNamespace(selected_prompt=PROMPT),
                    board_boot_id='public-boot', services=None)
                if invalid:
                    with self.assertRaises(ValueError): module.prepare_board_business(stage, value, None)
                    self.assertEqual(events, [])
                    return
                result = module.prepare_board_business(stage, value, None)
                self.assertEqual(events, ['asr_ctor', 'pair', 'health_date', 'speaker', 'feedback'])
                self.assertIs(runtime.summary.client, raw)
                self.assertIs(runtime.client, raw)
                self.assertEqual(result.dialogue_output.public()['configured_format'], mode or 'json')
                return runtime, result

    def test_actual_factory_default_json_keeps_original_controller_transport(self):
        runtime, result = self.run_constructor(None, CAPS)
        self.assertIs(runtime.controller.model_client, runtime.client)

    def test_actual_factory_explicit_compact_binds_after_same_clock_sample(self):
        runtime, result = self.run_constructor('dialogue_abc_v1', CAPS)
        self.assertIs(runtime.controller.model_client, result.dialogue_output)
        self.assertEqual(result.dialogue_output.public()['negotiated_dialogue_format'], 'dialogue_abc_v1')

    def test_actual_factory_legacy_host_keeps_json_route(self):
        runtime, result = self.run_constructor('dialogue_abc_v1', None)
        self.assertEqual(result.dialogue_output.public()['negotiated_dialogue_format'], 'json')

    def test_actual_factory_invalid_config_refuses_before_resource_constructors(self):
        self.run_constructor('dialogue_schema_v1', CAPS, invalid=True)


if __name__ == '__main__':
    unittest.main()
