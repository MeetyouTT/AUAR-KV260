"""Synthetic metadata tests: no sockets, services, ML runtime or private stores."""
import copy
import itertools
import json
import math

import pytest

from tests.framework import test_board_dialogue as controller_fixture
from tests.framework import test_board_dialogue_jobs as jobs_fixture
from board.runtime.board_dialogue import BoardDialogueController, BoardReply, ReplyRejected, StaleGeneration
from common.model_inference_wire import Owner, audio_payload, make_response

KEYS = (
    'prompt_eval_count', 'eval_count', 'load_duration_ms', 'prompt_eval_duration_ms',
    'eval_duration_ms', 'total_duration_ms', 'first_packet_ms', 'first_content_ms',
    'first_json_closed_ms', 'backend_done_ms', 'json_closed_to_done_ms',
    'thinking_characters', 'content_characters', 'trailing_whitespace_characters',
    'prompt_eval_cached_count',
)
FIELDS = {'llm_last_backend_' + name for name in KEYS}
USER_TEXT = '今天有点累可以陪我聊聊吗'


def prepared(controller, generation=1, **kwargs):
    return controller.prepare_text(USER_TEXT, scope={'kind': 'conversation', 'id': 'synthetic-session'},
                                   session_id='synthetic-session', generation=generation,
                                   budget_ms=3000, **kwargs)


def response_hook(models, metric_batches, replies=None, failure=None):
    calls = []
    batches = iter(metric_batches)
    replies = iter(replies or ['我会陪你聊聊。'])

    def hook(kind, payload, kwargs):
        owner = Owner.from_dict(payload)
        calls.append((kind, copy.deepcopy(payload), kwargs['deadline']))
        if kind == 'llm':
            if failure is not None:
                raise failure
            metrics = next(batches)
            result = {'text': json.dumps({'reply_text': next(replies), 'emotion': 'friendly', 'avatar_action': ''})}
            if metrics is not None:
                result['metrics'] = copy.deepcopy(metrics)
        else:
            result = {'audio': audio_payload(b'\x01\x00' * 160, 24000)}
        models.clock.now += .1
        return make_response(owner, result=result)

    models.hook = hook
    return calls


def setup():
    clock = controller_fixture.Clock()
    store = controller_fixture.Store()
    models = controller_fixture.Models(clock)
    ids = ('synthetic-' + str(i) for i in itertools.count())
    controller = BoardDialogueController(store, models, board_boot_id='synthetic-boot',
        system_prompt='合成测试三字段JSON', clock=clock, id_factory=lambda: next(ids))
    return controller, store, models


def test_actual_current_result_metrics_are_published_under_host_relative_names():
    controller, store, models = setup()
    backend = dict(first_content_ms=120.5, first_json_closed_ms=300., backend_done_ms=315.,
                   prompt_eval_count=18, eval_count=12)
    calls = response_hook(models, [backend])
    plan = prepared(controller)
    metrics = controller.last_prepare_metrics
    assert metrics.get('llm_backend_metrics_calls') == 1
    assert {key: metrics.get('llm_last_backend_' + key) for key in backend} == backend
    assert metrics['llm_rpc_ms'] == pytest.approx(100.)
    assert metrics['tts_rpc_ms'] == pytest.approx(100.)
    assert plan.pcm == b'\x01\x00' * 160
    assert [row[0] for row in calls] == ['llm', 'tts']
    assert store.rows[plan.turn_id]['status'] == 'generated'
    assert controller_fixture.ack(controller, plan)['status'] == 'played'


def test_multiple_llm_calls_keep_only_last_result_without_stale_optional_keys():
    controller, _, models = setup()
    calls = response_hook(models, [dict(first_content_ms=999., eval_count=10), dict(eval_count=21)],
                          replies=[USER_TEXT, '你可以先休息一下，我陪着你。'])
    plan = prepared(controller)
    metrics = controller.last_prepare_metrics
    assert metrics['llm_calls'] == 2
    assert metrics.get('llm_backend_metrics_calls') == 2
    assert metrics.get('llm_last_backend_eval_count') == 21
    assert 'llm_last_backend_first_content_ms' not in metrics
    assert [row[0] for row in calls] == ['llm', 'llm', 'tts']
    assert controller_fixture.ack(controller, plan)['status'] == 'played'


def test_empty_last_metrics_drop_first_attempt_values():
    controller, _, models = setup()
    response_hook(models, [dict(first_content_ms=9.), {}],
                  replies=[USER_TEXT, '我在这里陪你，慢慢说就好。'])
    prepared(controller)
    metrics = controller.last_prepare_metrics
    assert metrics.get('llm_backend_metrics_calls') == 1
    assert not FIELDS.intersection(metrics)


def test_multiple_tts_chunks_do_not_overwrite_llm_or_unbound_metadata_size():
    controller, _, models = setup()
    backend = {key: index for index, key in enumerate(KEYS)}
    calls = response_hook(models, [backend], replies=['我会陪你聊聊。也可以先安静休息。'])
    plan = prepared(controller)
    metrics = controller.last_prepare_metrics
    assert metrics.get('llm_backend_metrics_calls') == 1
    assert metrics['tts_calls'] == 2 and metrics['llm_calls'] == 1
    assert [row[0] for row in calls] == ['llm', 'tts', 'tts']
    assert len(FIELDS.intersection(metrics)) == 15
    assert all(metrics['llm_last_backend_' + key] == value for key, value in backend.items())
    assert all(type(metrics[key]) in (int, float) for key in FIELDS)
    assert len(plan.chunks) == 2


@pytest.mark.parametrize('value', [True, False, float('nan'), float('inf'), float('-inf'), -1., 1e15, 'synthetic text'])
def test_original_wire_rejection_stays_before_tts_and_no_numeric_metadata_leaks(value):
    controller, store, models = setup()
    calls = response_hook(models, [dict(first_content_ms=value)])
    with pytest.raises(ValueError):
        prepared(controller)
    assert [row[0] for row in calls] == ['llm']
    assert not FIELDS.intersection(controller.last_prepare_metrics)
    assert controller.last_prepare_metrics.get('llm_backend_metrics_calls', 0) == 0
    assert next(iter(store.rows.values()))['status'] == 'interrupted'


def test_unknown_private_strings_are_rejected_by_unchanged_wire_contract():
    controller, _, models = setup()
    response_hook(models, [dict(first_content_ms=1., transcript='synthetic private text')])
    with pytest.raises(ValueError):
        prepared(controller)
    public = json.dumps(controller.last_prepare_metrics)
    assert 'synthetic private text' not in public
    assert 'transcript' not in public


def test_local_reply_next_generation_has_no_previous_llm_observations():
    controller, _, models = setup()
    response_hook(models, [dict(first_content_ms=44.)])
    first = prepared(controller)
    controller_fixture.ack(controller, first)
    before = len(models.calls)
    local = controller.prepare_local_reply('合成查询', lambda: BoardReply('本地合成回答。'),
        scope={'kind': 'conversation', 'id': 'synthetic-session'}, session_id='synthetic-session',
        generation=2, budget_ms=3000)
    assert [row[0] for row in models.calls[before:]] == ['tts']
    assert not FIELDS.intersection(controller.last_prepare_metrics)
    assert controller.last_prepare_metrics.get('llm_backend_metrics_calls', 0) == 0
    assert controller_fixture.ack(controller, local)['status'] == 'played'


@pytest.mark.parametrize('failure', [TimeoutError(), InterruptedError(), RuntimeError('synthetic failure')])
def test_failed_next_prepare_clears_previous_observations(failure):
    controller, _, models = setup()
    response_hook(models, [dict(first_content_ms=44.)])
    first = prepared(controller)
    controller_fixture.ack(controller, first)
    response_hook(models, [], failure=failure)
    with pytest.raises(type(failure)):
        prepared(controller, generation=2)
    assert not FIELDS.intersection(controller.last_prepare_metrics)
    assert controller.last_prepare_metrics.get('llm_backend_metrics_calls', 0) == 0


def test_tts_failure_clears_this_prepare_backend_observation():
    controller, _, models = setup()
    calls = response_hook(models, [dict(first_content_ms=44.)])
    original = models.hook
    def hook(kind, payload, kwargs):
        if kind == 'tts':
            raise TimeoutError()
        return original(kind, payload, kwargs)
    models.hook = hook
    with pytest.raises(TimeoutError):
        prepared(controller)
    assert not FIELDS.intersection(controller.last_prepare_metrics)
    assert controller.last_prepare_metrics.get('llm_backend_metrics_calls', 0) == 0


def test_permission_rejection_clears_stale_observation_before_any_model_request():
    controller, _, models = setup()
    response_hook(models, [dict(first_content_ms=44.)])
    first = prepared(controller)
    controller_fixture.ack(controller, first)
    calls_before = len(models.calls)
    with pytest.raises(PermissionError):
        controller.prepare_text('合成无授权个人查询', scope={'kind': 'profile', 'id': 'synthetic-profile'},
            session_id='synthetic-session', generation=2, budget_ms=3000)
    assert len(models.calls) == calls_before
    assert not FIELDS.intersection(controller.last_prepare_metrics)


def test_jobs_public_filters_numeric_values_and_retains_existing_flags():
    job, controller, _, _, _ = jobs_fixture.setup()
    def hook():
        controller.last_prepare_metrics = {
            'metadata_only': True, 'complete': True, 'llm_rpc_ms': 120.,
            'llm_backend_metrics_calls': 1, 'llm_last_backend_first_content_ms': 2.5,
            'llm_last_backend_backend_done_ms': 4., 'llm_last_backend_eval_count': 12,
            'llm_last_backend_first_packet_ms': True,
            'llm_last_backend_prompt_eval_duration_ms': float('nan'),
            'llm_last_backend_eval_duration_ms': float('inf'),
            'llm_last_backend_total_duration_ms': -1,
            'llm_last_backend_thinking_characters': 'synthetic text',
            'llm_last_backend_private_id': 'synthetic id',
        }
    controller.hook = hook
    meta, events = jobs_fixture.prepare(job)
    value = job.public()['latency']['prepare']
    assert value.get('llm_backend_metrics_calls') == 1
    assert value.get('llm_last_backend_first_content_ms') == 2.5
    assert value.get('llm_last_backend_backend_done_ms') == 4.
    assert value.get('llm_last_backend_eval_count') == 12
    assert value['metadata_only'] is True and value['complete'] is True
    assert value['llm_rpc_ms'] == 120.
    assert set(value).intersection(FIELDS) == {'llm_last_backend_first_content_ms', 'llm_last_backend_backend_done_ms', 'llm_last_backend_eval_count'}
    assert 'synthetic' not in json.dumps(value)
    assert controller.acks == []
    job.acknowledge(meta, jobs_fixture.completion(events))
    job.drain_actions()
    assert len(controller.acks) == 1 and job.last_ack['committed'] is True


def test_jobs_next_failed_or_local_prepare_does_not_copy_previous_metrics():
    job, controller, _, _, _ = jobs_fixture.setup()
    controller.hook = lambda: setattr(controller, 'last_prepare_metrics', {'llm_last_backend_eval_count': 11})
    meta, events = jobs_fixture.prepare(job)
    job.acknowledge(meta, jobs_fixture.completion(events)); job.drain_actions()
    def failure():
        raise TimeoutError()
    controller.hook = failure
    jobs_fixture.prepare(job, capture='synthetic-second-capture')
    assert not FIELDS.intersection(job.public()['latency'].get('prepare', {}))
