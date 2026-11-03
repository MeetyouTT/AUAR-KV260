"""Independent source-only stream/real synthetic Store contract checks.

No models, devices, network or real databases are accessed. PCM below is a
public constant, and all SQLite files are newly created pytest fixtures.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
LATENCY = HERE.parents[1]
ROOT = HERE.parents[5]
sys.path.insert(0, str(ROOT / 'aura'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


memory = load('common.stream_test_prepared_memory',
              LATENCY / 'memory_candidate/after/common/board_memory.py')
dialogue = load('board.runtime.stream_test_dialogue',
                HERE.parent / 'after/board/runtime/board_dialogue.py')
jobs_module = load('board.runtime.audio.stream_test_jobs',
                   HERE.parent / 'after/board/runtime/audio/board_dialogue_jobs.py')
# Jobs imports the public classes by absolute module path. Use the independent
# candidate's exact class objects without rebinding any shared module globally.
jobs_module.PlaybackPlan = dialogue.PlaybackPlan
jobs_module.StaleGeneration = dialogue.StaleGeneration

from common.model_inference_wire import Owner, audio_payload, make_response
from common.profile_access import ProfileAccess
from common.voice_channel import ChannelState

SCOPE = {'kind': 'conversation', 'id': 'public-test-conversation'}
TEXT = '第一句公开回答。第二句公开回答。'
PCM = (b'\x01\x00' * 960, b'\x02\x00' * 1440)


class Clock:
    def __init__(self): self.now = 10.
    def __call__(self): return self.now


class Models:
    def __init__(self, clock):
        self.clock = clock
        self.calls, self.cancelled, self.tts_calls = [], [], 0
        self.reply, self.rate = TEXT, 24000
        self.before_return = None
        self.fail_tts = None

    def request(self, kind, payload, **kwargs):
        self.calls.append((kind, payload, kwargs))
        if kind == 'llm':
            result = dict(text=json.dumps(dict(reply_text=self.reply,
                emotion='friendly', avatar_action=''), ensure_ascii=False))
        else:
            self.tts_calls += 1
            if self.fail_tts == self.tts_calls:
                raise RuntimeError('public-fixture-tts-failure')
            result = dict(audio=audio_payload(PCM[(self.tts_calls - 1) % 2], self.rate))
        self.clock.now += .1
        if self.before_return is not None:
            self.before_return(kind, self.tts_calls)
        return make_response(Owner.from_dict(payload), result=result)

    def cancel(self, owner): self.cancelled.append(owner)


def fixture(tmp_path, *, profile=False):
    clock = Clock()
    access = ProfileAccess('a' * 64, clock=clock) if profile else None
    actor = {'board_boot_id': 'public-boot', 'session_id': 'public-session'}
    if profile:
        _, grant = access.issue('b' * 32, actor)
        scope = dict(kind='profile', id='b' * 32, grant=grant)
    else:
        scope = dict(SCOPE)
    store = memory.BoardMemoryStore(tmp_path / 'public-synthetic.sqlite3',
                                    clock=lambda: 1000., profile_access=access)
    store.append_event(scope, 'public-source', 'user_said', '项目尚未完成。')
    store.correct(scope, '项目状态', '尚未完成', source_event_ids=['public-source'])
    models = Models(clock)
    controller = dialogue.BoardDialogueController(store, models,
        board_boot_id='public-boot', system_prompt='公开合成测试人设。', clock=clock)
    return SimpleNamespace(clock=clock, access=access, actor=actor, scope=scope,
                           store=store, models=models, controller=controller)


def prepare(fx, sink=None, *, generation=1):
    return fx.controller.prepare_text('请给我一个简短答复。', scope=fx.scope,
        session_id='public-session', generation=generation, budget_ms=10000,
        turn_id='public-turn-' + str(generation), chunk_sink=sink)


def row(fx, generation=1):
    with sqlite3.connect(fx.store.path) as db:
        db.row_factory = sqlite3.Row
        return dict(db.execute('SELECT * FROM bm_turns WHERE turn_id=?',
                               ('public-turn-' + str(generation),)).fetchone())


def assistant_messages(fx):
    return [x for x in fx.store.context(fx.scope)['messages'] if x['role'] == 'assistant']


def ack(fx, plan, **changes):
    values = dict(playback_token=plan.playback_token, sha256=plan.sha256,
                  samples=plan.samples, complete=True)
    values.update(changes)
    return fx.controller.acknowledge(plan, **values)


def invalidate(fx, operation):
    if operation == 'revoke':
        fx.access.revoke(fx.actor)
        return
    # Independent Store instance changes the durable state without setting the
    # controller's request-local Event or directly calling controller.cancel.
    other = memory.BoardMemoryStore(fx.store.path, clock=lambda: 1001.)
    if operation == 'forget':
        other.forget(fx.scope, event_ids=['public-source'])
    elif operation == 'correct':
        other.correct(fx.scope, '项目状态', '重新核实')
    else:
        other.clear(fx.scope)


def test_generated_precedes_first_chunk_and_only_complete_receipt_becomes_heard(tmp_path):
    fx = fixture(tmp_path)
    emitted = []
    def sink(chunk, reply, start, token):
        durable = row(fx)
        assert durable['status'] == 'awaiting_playback'
        assert durable['assistant_event_id'] is not None
        assert durable['audio_sha256'] is None
        assert fx.store.check_prepared_turn_current(durable['turn_id'], generation=1)
        assert assistant_messages(fx) == []
        emitted.append((chunk, reply, start, token, fx.models.tts_calls))
    plan = prepare(fx, sink)
    assert [value[4] for value in emitted] == [1, 2]
    assert [value[2] for value in emitted] == [0, len(PCM[0]) // 2]
    assert {value[3] for value in emitted} == {plan.playback_token}
    assert tuple(value[0] for value in emitted) == plan.chunks
    assert plan.pcm == b''.join(PCM)
    assert plan.sha256 == hashlib.sha256(plan.pcm).hexdigest()
    assert row(fx)['audio_sha256'] == plan.sha256
    assert assistant_messages(fx) == []
    for fields in (dict(samples=1), dict(sha256='0' * 64), dict(playback_token='wrong')):
        with pytest.raises(ValueError): ack(fx, plan, **fields)
        assert assistant_messages(fx) == []
    assert ack(fx, plan)['status'] == 'played'
    assert assistant_messages(fx) == [dict(role='assistant', content=TEXT)]
    assert fx.controller.idle


@pytest.mark.parametrize('operation', ['forget', 'correct', 'clear', 'revoke'])
@pytest.mark.parametrize('point', ['before_first_sink', 'after_first_sink', 'during_second_tts'])
def test_durable_mutations_block_future_chunks_and_never_commit_complete_heard(tmp_path, operation, point):
    fx = fixture(tmp_path, profile=operation == 'revoke')
    emitted = []
    def sink(chunk, reply, start, token):
        emitted.append(chunk)
        if point == 'after_first_sink': invalidate(fx, operation)
    def hook(kind, nth):
        if kind == 'tts' and nth == (1 if point == 'before_first_sink' else 2) \
                and point != 'after_first_sink':
            invalidate(fx, operation)
    fx.models.before_return = hook
    with pytest.raises((memory.StaleTurn, memory.ScopeDenied, PermissionError)):
        prepare(fx, sink)
    assert len(emitted) == (0 if point == 'before_first_sink' else 1)
    assert fx.controller.idle
    durable = row(fx)
    assert durable['audio_sha256'] is None
    assert durable['status'] != 'played'
    with pytest.raises((memory.StaleTurn, memory.ScopeDenied, PermissionError)):
        fx.store.ack_played('public-turn-1', generation=1, playback_token='not-bound',
                           sha256=hashlib.sha256(PCM[0]).hexdigest(), samples=len(PCM[0]) // 2)
    if operation != 'revoke': assert assistant_messages(fx) == []


def test_second_tts_failure_preserves_partial_as_unheard_and_cancels_remote_owner(tmp_path):
    fx = fixture(tmp_path)
    fx.models.fail_tts = 2
    emitted = []
    with pytest.raises(RuntimeError): prepare(fx, lambda *values: emitted.append(values))
    assert len(emitted) == 1 and fx.models.tts_calls == 2
    assert row(fx)['status'] == 'interrupted'
    assert row(fx)['audio_sha256'] is None
    assert assistant_messages(fx) == []
    assert len(fx.models.cancelled) == 1
    assert fx.controller.idle


def test_cancel_after_first_sentence_prevents_second_tts_and_stale_generation_ack(tmp_path):
    fx = fixture(tmp_path)
    emitted = []
    def sink(*values):
        emitted.append(values)
        assert fx.controller.cancel('public-session', generation=1)
    with pytest.raises(dialogue.StaleGeneration): prepare(fx, sink)
    assert len(emitted) == 1 and fx.models.tts_calls == 1
    assert row(fx)['status'] == 'interrupted'
    assert assistant_messages(fx) == []
    plan = prepare(fx, lambda *values: None, generation=2)
    assert ack(fx, plan)['status'] == 'played'


def test_entire_text_and_native_rate_are_checked_before_first_chunk(tmp_path):
    fx = fixture(tmp_path)
    fx.models.reply = '公开句。' * 61
    emitted = []
    with pytest.raises(dialogue.ReplyRejected): prepare(fx, lambda *values: emitted.append(values))
    assert not emitted and fx.models.tts_calls == 0
    assert row(fx)['assistant_event_id'] is None
    fx.models.reply = TEXT
    fx.models.rate = 22050
    with pytest.raises(dialogue.ReplyRejected):
        prepare(fx, lambda *values: emitted.append(values), generation=2)
    assert not emitted and row(fx, 2)['audio_sha256'] is None
    assert assistant_messages(fx) == []


def test_default_nonstream_path_keeps_existing_complete_plan_and_deadline(tmp_path):
    fx = fixture(tmp_path)
    plan = prepare(fx)
    assert plan.pcm == b''.join(PCM)
    assert ack(fx, plan)['status'] == 'played'
    assert len({kwargs['deadline'] for _, _, kwargs in fx.models.calls}) == 1
    assert len({payload['request_id'] for _, payload, _ in fx.models.calls}) == 3
    assert all((p['board_boot_id'], p['session_id'], p['generation']) ==
               ('public-boot', 'public-session', 1) for _, p, _ in fx.models.calls)


def make_jobs(fx):
    class Asr:
        model_sha256 = 'a' * 64
        def transcribe(self, pcm, **kwargs): return '请给我一个简短答复。'
    return jobs_module.BoardDialogueJobs(fx.controller,
        dict(enabled=True, host='192.168.50.1', port=8808, timeout_ms=30000),
        'public-boot', asr=Asr(), scope_provider=lambda _: dict(fx.scope),
        clock=fx.clock, wall_clock=lambda: 1000., start_worker=False)


def drain(jobs):
    values = []
    while True:
        value = jobs.poll()
        if value is None: return values
        values.append(value)


def clip():
    return SimpleNamespace(capture_id='public-capture',
        audio=SimpleNamespace(sample_count=3200), pcm=b'\x01\x00' * 3200)


def test_actual_jobs_channel_aggregate_receipt_and_off_player_ack_commit(tmp_path):
    fx = fixture(tmp_path)
    jobs = make_jobs(fx)
    metadata = jobs.submit(clip())
    assert jobs.run_next()
    values = drain(jobs)
    assert not any('error' in v for v in values)
    channel = ChannelState(metadata)
    for value in values:
        if 'channel_event' in value:
            channel.accept(value['channel_event'], value['pcm'])
    result = next(v['network_complete'] for v in values if 'network_complete' in v)
    assert channel.ended and channel.samples == sum(len(p) // 2 for p in PCM)
    assert channel.digest.hexdigest() == hashlib.sha256(b''.join(PCM)).hexdigest()
    assert assistant_messages(fx) == []
    jobs.acknowledge(metadata, result)
    assert assistant_messages(fx) == []
    jobs.drain_actions()
    assert jobs.last_ack['committed']
    assert assistant_messages(fx) == [dict(role='assistant', content=TEXT)]
    assert jobs.idle and fx.controller.idle


def test_actual_jobs_late_tts_failure_replaces_queued_pcm_with_error_and_no_ack(tmp_path):
    fx = fixture(tmp_path)
    fx.models.fail_tts = 2
    jobs = make_jobs(fx)
    jobs.submit(clip())
    assert jobs.run_next()
    values = drain(jobs)
    assert len(values) == 1 and 'error' in values[0]
    assert not any('network_complete' in value for value in values)
    jobs.drain_actions()
    assert jobs.last_ack is None and assistant_messages(fx) == []


@pytest.mark.parametrize('operation', ['forget', 'correct', 'clear', 'revoke'])
def test_actual_jobs_rechecks_durable_authority_between_same_sentence_packets(tmp_path, operation):
    fx = fixture(tmp_path, profile=operation == 'revoke')
    fx.models.reply = '公开的一句回复。'
    jobs = make_jobs(fx)
    original_put = jobs._put
    delivered = []
    def put(job, value, **kwargs):
        original_put(job, value, **kwargs)
        if value.get('channel_event', {}).get('kind') == 'audio':
            delivered.append(value)
            if len(delivered) == 1:
                # A GUI/poll owner could have consumed this first packet already.
                # Do not count clearing the remaining queue at final bind as a
                # substitute for checking before publishing the next packet.
                invalidate(fx, operation)
    jobs._put = put
    jobs.submit(clip())
    assert jobs.run_next()
    assert len(delivered) == 1
    values = drain(jobs)
    assert len(values) == 1 and 'error' in values[0]
    assert not any('network_complete' in value for value in values)
    jobs.drain_actions()
    assert jobs.last_ack is None
    if operation != 'revoke': assert assistant_messages(fx) == []


@pytest.mark.parametrize('operation', ['forget', 'revoke'])
def test_actual_jobs_rechecks_durable_authority_after_audio_backpressure_wait(tmp_path, operation):
    fx = fixture(tmp_path, profile=operation == 'revoke')
    fx.models.reply = '公开的一句回复。'
    jobs = make_jobs(fx)
    original_put = jobs._put
    delivered, waits = [], []
    def wait(_timeout):
        waits.append(True)
        invalidate(fx, operation)
        jobs.progress.clear()
    jobs.condition.wait = wait
    def put(job, value, **kwargs):
        if value.get('channel_event', {}).get('kind') == 'audio':
            if not waits:
                # The append must recheck after queue capacity becomes free;
                # a check only before entering _put is insufficient.
                while len(jobs.progress) < 128:
                    jobs.progress.append(dict(public_fixture_backpressure=True))
            original_put(job, value, **kwargs)
            delivered.append(value)
        else:
            original_put(job, value, **kwargs)
    jobs._put = put
    jobs.submit(clip())
    assert jobs.run_next()
    assert len(waits) == 1 and not delivered
    values = drain(jobs)
    assert len(values) == 1 and 'error' in values[0]
    jobs.drain_actions()
    assert jobs.last_ack is None
    if operation != 'revoke': assert assistant_messages(fx) == []

