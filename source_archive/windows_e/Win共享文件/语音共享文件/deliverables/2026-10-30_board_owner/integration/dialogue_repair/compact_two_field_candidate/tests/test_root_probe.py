"""Pure fake wrapper admission/control tests; never execute an actual backend."""
import copy
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module; spec.loader.exec_module(module)
    return module


probe = load('root_probe_tested', HERE/'root_public_probe.py')
contract = load('root_probe_test_contract', HERE/'after/common/inference_output_contract.py')


def permit():
    value = dict.fromkeys(probe.FLAGS, True)
    value.update(issued_utc=datetime.now(timezone.utc).isoformat(), model=probe.MODEL,
        expected_runner_pid=101, expected_static_prompt_sha256='a'*64,
        evidence=dict(startup_sha256='b'*64, board_boot_id='8100a7fd-0c6a-46c4-82b8-f874988a1521',
            writer_lock_observed_free=True, unit=dict(MainPID='0', ActiveState='inactive', Job='',
                SendSIGKILL='no', TimeoutStopUSec='infinity')))
    return value


def test_both_default_cli_modes_are_dry(capsys, monkeypatch):
    monkeypatch.setattr(probe, 'execute', lambda *_: pytest.fail('Dry invoked execute'))
    for mode, count in [('abba', 4), ('d01', 1)]:
        assert probe.main(['--experiment', mode]) == 0
        value = json.loads(capsys.readouterr().out)
        assert value['requests'] == count and value['tts_instances_constructed'] == 0
        assert value['think'] is (mode == 'd01')


@pytest.mark.parametrize('change', ['old', 'future', 'ui', 'writer', 'flag', 'pid-bool'])
def test_fresh_permit_and_real_closed_owner_evidence_are_required(change):
    value = permit()
    if change == 'old': value['issued_utc'] = (datetime.now(timezone.utc)-timedelta(seconds=121)).isoformat()
    if change == 'future': value['issued_utc'] = (datetime.now(timezone.utc)+timedelta(seconds=5)).isoformat()
    if change == 'ui': value['evidence']['unit']['MainPID'] = '99'
    if change == 'writer': value['evidence']['writer_lock_observed_free'] = False
    if change == 'flag': value['all_other_project_model_probes_stopped'] = 1
    if change == 'pid-bool': value['expected_runner_pid'] = True
    with pytest.raises(probe.TrialError): probe.validate_permit(value)
    assert probe.validate_permit(permit())['expected_runner_pid'] == 101


@pytest.mark.parametrize('change', ['busy', 'runner', 'model-path', 'residency', 'context'])
def test_original_guard_refuses_owner_or_model_changes(tmp_path, change):
    health = dict(ok=True, role='model_inference_only', active=False, pending=0, request_logging=False,
        backend=dict(model=probe.MODEL, tts='omnivoice', num_step=16, tts_ready=True))
    row = dict(name=probe.MODEL, size=100, size_vram=80, context_length=2048)
    runner = dict(pid=101, model_path=str(tmp_path/'blobs/public-model'))
    def fetch(url): return copy.deepcopy(health if url.endswith('/health') else dict(models=[row]))
    observations = []
    guard = probe.owner_guard(fetch, lambda _: runner, 'http://127.0.0.1:8797/health',
        permit(), (tmp_path/'blobs').resolve(), observations)
    guard()
    if change == 'busy': health['active'] = True
    if change == 'runner': runner['pid'] = 102
    if change == 'model-path': runner['model_path'] = str(tmp_path/'other/public-model')
    if change == 'residency': row['size_vram'] = 81
    if change == 'context': row['context_length'] = 1024
    with pytest.raises(probe.TrialError): guard()
    assert len(observations) == 1


def test_d01_observer_ignores_unrelated_metadata_responses_and_restores_class():
    class MarkedSocket: pass
    class Response:
        def __init__(self, sock): self.status = sock.status if isinstance(sock, MarkedSocket) else 200
        def begin(self): pass
        def readline(self):
            return json.dumps(dict(message=dict(thinking='PUBLIC_SECRET', content='{}'),
                done=True, done_reason='stop', eval_count=3)).encode()
    http = SimpleNamespace(client=SimpleNamespace(HTTPResponse=Response))
    bundle = SimpleNamespace(contract=contract, host=SimpleNamespace(http=http, _ResponseSocket=MarkedSocket))
    metadata = {}
    with probe.observe_d01(bundle, metadata):
        other = http.client.HTTPResponse(object()); other.begin(); other.readline()
        assert not metadata
        sock = MarkedSocket(); sock.status = 400
        actual = http.client.HTTPResponse(sock); actual.begin(); actual.readline()
    assert http.client.HTTPResponse is Response
    assert metadata['http_status'] == 400 and metadata['backend_done']
    assert metadata['thinking_characters'] == len('PUBLIC_SECRET')
    assert 'PUBLIC_SECRET' not in json.dumps(metadata)


@pytest.mark.parametrize('failure', [None, 'http400', 'length'])
def test_d01_is_one_canonical_think_call_without_hidden_retry(monkeypatch, failure):
    @contextmanager
    def observe(bundle, metadata):
        metadata.update(http_status=400 if failure=='http400' else 200,
            backend_done=True, ended_by_length=failure=='length', thinking_characters=5)
        yield metadata
    monkeypatch.setattr(probe, 'observe_d01', observe)
    calls = []
    def infer(mode, messages, *, think):
        calls.append((mode, messages, think))
        if failure == 'http400': raise RuntimeError('DO_NOT_LOG_RAW')
        return dict(text='{"reply_text":"17乘23等于391。","emotion":"neutral","avatar_action":""}',
                    metrics=dict(eval_count=40, eval_duration_ms=1., untrusted_body='DO_NOT_LOG_RAW'))
    bundle = SimpleNamespace(contract=contract, validator=lambda raw, _: SimpleNamespace(text=json.loads(raw)['reply_text']))
    row = probe.run_d01(bundle, 'EXACT_CANONICAL_978B', infer)
    assert len(calls) == 1 and calls[0][0] is None and calls[0][2] is True
    assert calls[0][1][0] == dict(role='system', content='EXACT_CANONICAL_978B')
    assert row['reply_contract'] == 'canonical' and row['wire_format'] == 'json'
    assert row['error_code'] == ('BACKEND_HTTP_REJECTED' if failure=='http400' else
                                 'OUTPUT_TRUNCATED' if failure=='length' else 'NONE')
    assert row['complete_json'] is (failure is None)
    assert 'DO_NOT_LOG_RAW' not in json.dumps(row)


def test_fixed_seed_is_process_only_with_original_chat_body(monkeypatch):
    prior = sys.modules.get('tools.dialogue_host_ollama')
    try:
        probe.seeded_chat_body()
        value = sys.modules['tools.dialogue_host_ollama'].chat_body('fixed', 'system', 'public', fast=True)
        assert value['options']['seed'] == 8701
        assert value['options']['num_ctx'] == 2048 and value['options']['num_predict'] == 120
        assert value['options']['temperature'] == .6 and value['think'] is False
    finally:
        if prior is None: sys.modules.pop('tools.dialogue_host_ollama', None)
        else: sys.modules['tools.dialogue_host_ollama'] = prior


def test_execute_modes_keep_request_counts_and_wire_options_separate(tmp_path, monkeypatch):
    p = permit(); permit_path = tmp_path/'public-permit.json'; permit_path.write_text(json.dumps(p))
    prompt = 'reply_text为台词，emotion为neutral/friendly/happy/sad之一，avatar_action为空字符串。'
    pins = dict(baseline_startup_sha256='b'*64, static_prompt_sha256='a'*64)
    monkeypatch.setattr(probe, 'verified_sources', lambda: pins)
    metadata = dict(ok=True, role='model_inference_only', active=False, pending=0, request_logging=False,
        backend=dict(model=probe.MODEL, tts='omnivoice', num_step=16, tts_ready=True))
    def fetch(url): return copy.deepcopy(metadata if url.endswith('/health') else dict(models=[
        dict(name=probe.MODEL, context_length=2048, size=100, size_vram=80)]))
    monkeypatch.setattr(probe, 'reuse_guard_helpers', lambda _: (fetch, lambda _: prompt))
    original_read = probe.read_json
    monkeypatch.setattr(probe, 'read_json', lambda path, **kw: dict(ollama_directory=str(tmp_path/'models'))
        if path.name=='model_storage.local.json' else original_read(path, **kw))
    original_here = probe.HERE
    calls, events = [], []
    class Backend:
        def llm(self, payload, *, deadline, cancelled):
            calls.append(copy.deepcopy(payload)); events.append(cancelled)
            mode = payload['options'].get('output_format')
            return dict(text=json.dumps(dict(a='五十四。', b='neutral', **(
                dict(c='') if mode=='dialogue_abc_v1' else {}))) if mode else
                '{"reply_text":"391。","emotion":"neutral","avatar_action":""}', metrics={})
    bundle = SimpleNamespace(backend=Backend(), wire=SimpleNamespace(validate_request=lambda _,p: p),
        contract=contract, validator=lambda raw,_: SimpleNamespace(text=json.loads(raw)['reply_text']),
        native=SimpleNamespace(_discover=lambda _:dict(pid=101,model_path=str(tmp_path/'models/blobs/public-model'))))
    # The pilot core uses already-tested contract/adapter/validator modules.
    before = {name:sys.modules.get(name) for name in (
        'board.runtime.compact_request_adapter','board.runtime.board_dialogue','common.inference_output_contract')}
    try:
        sys.path.insert(0, str(probe.AURA))
        load('common.inference_output_contract', original_here/'after/common/inference_output_contract.py')
        load('board.runtime.compact_request_adapter', original_here/'after/board/runtime/compact_request_adapter.py')
        sys.modules['board.runtime.board_dialogue'] = SimpleNamespace(validate_model_reply=bundle.validator)
        monkeypatch.setattr(probe, 'prepare_backend', lambda *_: bundle)
        tmp_core = tmp_path/'public_abba.py'; tmp_core.write_bytes((original_here/'public_abba.py').read_bytes())
        monkeypatch.setattr(probe, 'HERE', tmp_path)
        for mode, expected in [('abba',4), ('d01',1)]:
            calls.clear(); events.clear()
            @contextmanager
            def observe(_, metadata):
                metadata.update(http_status=200,backend_done=True,thinking_characters=1)
                yield metadata
            monkeypatch.setattr(probe, 'observe_d01', observe)
            result = probe.execute(SimpleNamespace(root_permit=permit_path,experiment=mode,
                host_health_url='http://127.0.0.1:8797/health'))
            assert result['checks_passed'] and result['post_guard_passed']
            assert result['model_requests_attempted'] == len(calls) == expected
            assert all(event.is_set() for event in events)
            if mode == 'abba':
                assert [c['options']['output_format'] for c in calls] == [
                    'dialogue_abc_v1','dialogue_ab_v1','dialogue_ab_v1','dialogue_abc_v1']
                assert all(c['options']['think'] is False for c in calls)
            else:
                assert calls[0]['options'] == dict(think=True,num_predict=120)
                assert calls[0]['messages'][0] == dict(role='system',content=prompt)
    finally:
        for name, value in before.items():
            if value is None: sys.modules.pop(name,None)
            else: sys.modules[name] = value
