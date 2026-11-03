"""Public synthetic contract/controller tests. No model, socket or device use."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[4]
V16 = ROOT.parent/'feature_trigger_collaboration/runtime_v16'
sys.path.insert(0, str(PROJECT/'aura'))
sys.path.insert(0, str(V16))
import common
import tools
import board.runtime


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


contract = load('common.inference_output_contract', ROOT/'after/common/inference_output_contract.py')
wire = load('common.model_inference_wire', V16/'common/model_inference_wire.py')
adapter = load('board.runtime.compact_request_adapter', ROOT/'after/board/runtime/compact_request_adapter.py')
client = load('board.runtime.board_dialogue_client', ROOT/'after/board/runtime/board_dialogue_client.py')
selection = load('tools.production_output_format', ROOT/'after/tools/production_output_format.py')
dialogue = load('board.runtime.board_dialogue', V16/'board/runtime/board_dialogue.py')
old_contract = load('twofield_before_contract', ROOT/'before/common/inference_output_contract.py')
host = load('twofield_actual_host', ROOT/'after/tools/model_inference_host.py')
from common.board_memory import BoardMemoryStore
from board.runtime.board_memory_policy import BoardContextBuilder

PROFILE = ROOT.parent/'paraformer_small_validation/public_chain/reference/config/character_profile.local.json'
PROMPT = json.loads(PROFILE.read_text(encoding='utf-8-sig'))['persona_full_prompt']
CAPS = dict(format_contract_version=1, output_formats=[
    'json', 'dialogue_schema_v1', 'dialogue_abc_v1', 'dialogue_ab_v1'])
AB = '{"a":"公开合成答复。","b":"friendly"}'
ABC = '{"a":"公开合成答复。","b":"friendly","c":""}'
CANONICAL = '{"reply_text":"公开合成答复。","emotion":"friendly","avatar_action":""}'


def payload():
    return dict(protocol_version=1, request_id='public-request', board_boot_id='public-boot',
        session_id='public-session', generation=1, budget_ms=10000, task='dialogue',
        messages=[dict(role='system', content=PROMPT), dict(role='user', content='原话reply_text不改')],
        options={})


class Transport:
    def __init__(self, caps=CAPS, reply=None):
        self.caps, self.reply = copy.deepcopy(caps), reply
        self.calls, self.cancelled = [], []
        self.hook = None
    def output_format_capabilities(self):
        return copy.deepcopy(self.caps)
    def request(self, kind, body, *, deadline, cancelled):
        self.calls.append((kind, copy.deepcopy(body)))
        mode = body.get('options', {}).get('output_format')
        result = (dict(text=self.reply or (AB if mode == 'dialogue_ab_v1' else
                  ABC if mode == 'dialogue_abc_v1' else CANONICAL)) if kind == 'llm' else
                  dict(audio=wire.audio_payload(b'\x01\x00'*480, 24000)))
        if self.hook: self.hook(kind)
        return wire.make_response(wire.Owner.from_dict(body), result=result)
    def cancel(self, owner):
        self.cancelled.append(owner)


def test_old_schema_and_request_bodies_remain_equal():
    base = dict(model='fixed-public-model', options=dict(num_ctx=2048, num_predict=120, temperature=.6))
    for mode in ('json', 'dialogue_schema_v1', 'dialogue_abc_v1'):
        request = payload(); request['options']['output_format'] = mode
        assert contract.build_body(base, request) == old_contract.build_body(base, request)
    assert contract.dialogue_schema() == old_contract.dialogue_schema()
    assert contract.dialogue_schema(compact=True) == old_contract.dialogue_schema(compact=True)
    assert contract.canonicalize_compact(ABC) == old_contract.canonicalize_compact(ABC)


def test_ab_schema_preserves_sampling_budget_and_adds_no_action_authority():
    request = payload(); request['options']['output_format'] = 'dialogue_ab_v1'
    assert wire.validate_request('llm', request) == request
    base = dict(model='fixed-public-model', options=dict(num_ctx=2048, num_predict=120, temperature=.6))
    body = contract.build_body(base, request)
    assert body['format']['required'] == ['a', 'b']
    assert set(body['format']['properties']) == {'a', 'b'}
    assert body['format']['additionalProperties'] is False
    assert body['options'] == base['options'] and body['messages'] == request['messages']
    assert body['stream'] is True and body['think'] is False and body['keep_alive'] == -1
    assert json.loads(contract.canonicalize_compact(AB, mode='dialogue_ab_v1')) == json.loads(CANONICAL)


@pytest.mark.parametrize('raw', [
    '{"a":"cut', '{}', '[]', '{"a":"x"}', '{"a":"x","b":"friendly","c":""}',
    '{"a":"x","a":"y","b":"friendly"}', '{"a":"x","b":"invalid"}',
    '{"a":1,"b":"friendly"}', '{"a":"","b":"friendly"}',
    '{"a":"<think>private","b":"neutral"}', '{"a":"x","b":"friendly","grant":true}',
    '{"a":"x","b":"friendly"} trailing',
])
def test_ab_rejects_partial_duplicate_extra_and_invalid_content(raw):
    with pytest.raises(contract.OutputContractError):
        contract.canonicalize_compact(raw, mode='dialogue_ab_v1')


def test_negotiated_request_changes_only_static_output_obligation():
    raw = Transport()
    chosen = selection.NegotiatedDialogueClient(raw, system_prompt=PROMPT, mode='dialogue_ab_v1')
    request = payload(); before = copy.deepcopy(request)
    result = chosen.request('llm', request, deadline=20., cancelled=lambda: False)
    sent = raw.calls[0][1]
    assert request == before and sent['messages'][1:] == before['messages'][1:]
    expected = PROMPT.replace('reply_text', 'a').replace('emotion', 'b').replace(
        'avatar_action为空字符串', '不输出动作字段')
    assert sent['messages'][0] == dict(role='system', content=expected)
    assert sent['options'] == {'output_format': 'dialogue_ab_v1'}
    assert wire.Owner.from_dict(sent) == wire.Owner.from_dict(request)
    assert json.loads(result['result']['text']) == json.loads(CANONICAL)
    assert chosen.public()['negotiated_dialogue_format'] == 'dialogue_ab_v1'
    assert chosen.public()['per_turn_health_requests'] == 0


def test_default_abc_legacy_and_capability_downgrade_are_preserved():
    for mode, caps in [('json', CAPS), ('dialogue_abc_v1', CAPS),
                       ('dialogue_ab_v1', dict(format_contract_version=1, output_formats=['json', 'dialogue_abc_v1']))]:
        raw = Transport(caps)
        chosen = selection.NegotiatedDialogueClient(raw, system_prompt=PROMPT, mode=mode)
        chosen.request('llm', payload(), deadline=20., cancelled=lambda: False)
        actual = raw.calls[-1][1]
        if mode != 'dialogue_abc_v1': assert actual == payload()
        else: assert actual['options']['output_format'] == 'dialogue_abc_v1'
    raw = Transport(); chosen = selection.NegotiatedDialogueClient(raw, system_prompt=PROMPT, mode='dialogue_ab_v1')
    chosen.request('llm', payload(), deadline=20., cancelled=lambda: False)
    raw.caps = None
    chosen.request('llm', payload(), deadline=20., cancelled=lambda: False)
    assert raw.calls[-1][1] == payload() and chosen.public()['negotiated_dialogue_format'] == 'json'


def test_verified_health_whitelist_and_invalid_config_remain_strict():
    assert client.InferenceHttpClient._health_output_capabilities({'backend': CAPS}) == CAPS
    for caps in (dict(format_contract_version=True, output_formats=CAPS['output_formats']),
                 dict(format_contract_version=1, output_formats=['json', 'unknown']),
                 dict(format_contract_version=1, output_formats=['json', 'json']),
                 dict(format_contract_version=1, output_formats=['dialogue_ab_v1'])):
        assert client.InferenceHttpClient._health_output_capabilities({'backend': caps}) is None
        assert selection.NegotiatedDialogueClient(Transport(caps), system_prompt=PROMPT,
            mode='dialogue_ab_v1').public()['negotiated_dialogue_format'] == 'json'
    for mode in (None, True, 'dialogue_ab_v2', 'dialogue_schema_v1', ''):
        with pytest.raises(ValueError): selection.validate_dialogue_output_format(mode)
    with pytest.raises(ValueError, match='static_empty_action_contract_missing'):
        adapter.CompactRequestAdapter(Transport(), system_prompt='reply_text/emotion/avatar_action',
            capabilities=CAPS, mode='dialogue_ab_v1')


def test_summary_thinking_different_prompt_tts_and_cancel_keep_original_paths():
    raw = Transport(); chosen = selection.NegotiatedDialogueClient(raw, system_prompt=PROMPT, mode='dialogue_ab_v1')
    for change in ('summary', 'thinking', 'other-prompt'):
        request = payload()
        if change == 'summary': request['task'] = 'summary'
        elif change == 'thinking': request['options']['think'] = True
        else: request['messages'][0]['content'] = 'another public persona'
        chosen.request('llm', request, deadline=20., cancelled=lambda: False)
        assert raw.calls[-1][1] == request
    request = {k:v for k,v in payload().items() if k not in ('task', 'messages', 'options')}
    request['text'] = '公开合成'
    chosen.request('tts', request, deadline=20., cancelled=lambda: False)
    assert raw.calls[-1][1] == request
    owner = wire.Owner.from_dict(payload()); chosen.cancel(owner)
    assert raw.cancelled == [owner]
    with pytest.raises(InterruptedError):
        chosen.request('llm', payload(), deadline=20., cancelled=lambda: True)
    assert len(raw.calls) == 5  # No retry/fallback after receiving cancelled AB.


def make_controller(tmp_path, reply=None):
    store = BoardMemoryStore(tmp_path/'public-synthetic.sqlite3', clock=lambda: 1793400000., data_origin='synthetic')
    raw = Transport(reply=reply)
    controller = dialogue.BoardDialogueController(store, raw, board_boot_id='public-boot',
        system_prompt=PROMPT, context_builder=BoardContextBuilder(PROMPT), clock=lambda: 10.)
    runtime = SimpleNamespace(controller=controller, client=raw, started=False, closed=False,
        jobs=SimpleNamespace(thread=None), summary=SimpleNamespace(client=raw))
    chosen = selection.install_dialogue_output(runtime, mode='dialogue_ab_v1', system_prompt=PROMPT)
    return store, raw, controller, runtime, chosen


def prepare(controller, emitted):
    return controller.prepare_text('公开问题', scope=dict(kind='conversation', id='public-conversation'),
        session_id='public-session', generation=1, budget_ms=10000,
        chunk_sink=lambda *args: emitted.append(args))


def test_real_store_full_controller_requires_complete_ack(tmp_path):
    store, raw, controller, runtime, chosen = make_controller(tmp_path)
    try:
        emitted = []; plan = prepare(controller, emitted)
        assert [kind for kind, _ in raw.calls] == ['llm', 'tts']
        assert plan.reply.avatar_action == '' and plan.reply.text == '公开合成答复。'
        assert plan.sample_rate == 24000 and len(emitted) == 1
        scope = dict(kind='conversation', id='public-conversation')
        assert not any(row['role'] == 'assistant' for row in store.context(scope)['messages'])
        assert runtime.client is runtime.summary.client is raw
        controller.acknowledge(plan, playback_token=plan.playback_token,
            sha256=plan.sha256, samples=plan.samples, complete=True)
        assert any(row['role'] == 'assistant' and row['content'] == plan.reply.text
                   for row in store.context(scope)['messages'])
    finally: controller.cancel('public-session', generation=1)


@pytest.mark.parametrize('failure', ['partial', 'extra', 'cancelled', 'forget-after-tts'])
def test_real_store_failure_or_revocation_emits_no_audio(tmp_path, failure):
    reply = '{"a":"cut' if failure == 'partial' else ABC if failure == 'extra' else None
    store, raw, controller, _, _ = make_controller(tmp_path, reply)
    def hook(kind):
        if failure == 'cancelled' and kind == 'llm': controller.cancel('public-session', generation=1)
        if failure == 'forget-after-tts' and kind == 'tts':
            store.clear(dict(kind='conversation', id='public-conversation'))
    raw.hook = hook
    emitted = []
    try:
        with pytest.raises((contract.OutputContractError, InterruptedError, RuntimeError, ValueError)):
            prepare(controller, emitted)
        assert not emitted
        assert [kind for kind, _ in raw.calls] == (['llm', 'tts'] if failure == 'forget-after-tts' else ['llm'])
        assert not any(row['role'] == 'assistant' for row in store.context(
            dict(kind='conversation', id='public-conversation'))['messages'])
    finally: controller.cancel('public-session', generation=1)


@pytest.mark.parametrize('terminal', ['done', 'eof', 'length'])
def test_actual_host_does_not_return_closed_json_before_backend_done(terminal):
    backend = host.LocalModelBackend.__new__(host.LocalModelBackend)
    backend.model, backend.ollama_host = 'fixed-public-model', 'http://127.0.0.1:11435'
    request = payload(); request['options']['output_format'] = 'dialogue_ab_v1'
    packets = [dict(message=dict(content=AB), done=False)]
    if terminal != 'eof': packets.append(dict(message=dict(content=''), done=True,
        done_reason='length' if terminal == 'length' else 'stop', eval_count=20))
    class Socket:
        def setblocking(self, *_): pass
        def send(self, data): return len(data)
    class Connection:
        def __init__(self, *_args, **_kwargs): self.sock = Socket()
        def connect(self): pass
        def close(self): pass
    class Response:
        status = 200
        def __init__(self, *_): self.count = 0
        def begin(self): pass
        def readline(self, *_):
            self.count += 1
            return (json.dumps(packets.pop(0)).encode()+b'\n') if packets else b''
        def close(self): pass
    response = Response()
    with patch.object(host.http.client, 'HTTPConnection', Connection), \
         patch.object(host.http.client, 'HTTPResponse', lambda *_: response), \
         patch.object(host.select, 'select', lambda _r, w, _x, _t: ([], w, [])):
        if terminal == 'done':
            assert backend._ollama(request, deadline=time.monotonic()+5, cancelled=threading.Event())['text'] == AB
        else:
            with pytest.raises(contract.OutputTruncated if terminal == 'length' else RuntimeError):
                backend._ollama(request, deadline=time.monotonic()+5, cancelled=threading.Event())
    assert response.count == 2  # Closed first object alone did not authorize a return.


def test_public_abba_core_uses_only_four_guarded_calls_and_numeric_evidence():
    bench = load('twofield_public_abba', ROOT/'public_abba.py')
    calls, guards = [], []
    def infer(mode, messages):
        calls.append((mode, messages))
        return dict(text=json.dumps(dict(a='五十四。', b='neutral', **(
            {'c': ''} if mode == 'dialogue_abc_v1' else {})), ensure_ascii=False),
            metrics=dict(eval_count=20, prompt_eval_duration_ms=1., arbitrary_text='DO_NOT_RETAIN'))
    result = bench.run_public_abba(infer, lambda: guards.append(True), system_prompt=PROMPT)
    assert [mode for mode,_ in calls] == list(bench.ORDER)
    assert len(guards) == 8 and result['all_complete'] and result['all_semantic_pass']
    assert all(messages[-1] == dict(role='user', content=bench.QUESTION) for _,messages in calls)
    assert 'DO_NOT_RETAIN' not in json.dumps(result) and bench.plan()['warmups'] == 0


def test_public_abba_core_retains_failure_without_retry_or_extra_generations():
    bench = load('twofield_public_abba_failure', ROOT/'public_abba.py')
    calls = []
    def infer(mode, messages):
        calls.append(mode)
        return dict(text='incomplete SECRET')
    result = bench.run_public_abba(infer, lambda: None, system_prompt=PROMPT)
    assert len(calls) == 1 and result['completed_trials'] == 1 and not result['all_complete']
    assert result['trials'][0]['error_code'] == 'INVALID_OR_FAILED_REPLY'
    assert 'SECRET' not in json.dumps(result)
