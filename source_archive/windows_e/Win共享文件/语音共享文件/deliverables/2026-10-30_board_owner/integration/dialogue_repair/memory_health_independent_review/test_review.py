"""Independent review: exact candidate imports and fake replies only."""
import importlib.util
import ast
from pathlib import Path
import sys

import pytest

HERE = Path(__file__).resolve().parent
COLLAB = HERE.parent / 'memory_health_collaboration'
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'aura'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


import common
common.board_memory = load('common.board_memory', COLLAB / 'before/common/board_memory.py')
load('common.board_memory_backoff', COLLAB / 'after/common/board_memory_backoff.py')
policy = load('board.runtime.board_memory_policy', COLLAB / 'after/board/runtime/board_memory_policy.py')
from common.model_inference_wire import Owner, WireError, make_response


class Client:
    def __init__(self, mutation=None): self.calls, self.mutation = [], mutation
    def request(self, kind, payload, **kwargs):
        self.calls.append(payload)
        owner = Owner.from_dict(payload)
        response = make_response(owner, result=dict(text='{"summary":"公开摘要。","keywords":["公开"]}'))
        return self.mutation(owner, response) if self.mutation else response
    def cancel(self, owner): pass


def infer(client, clock):
    summary = policy.BoardSummaryClient(client, board_boot_id='public-boot', clock=lambda: clock)
    summary.metrics = dict(model_calls=0)
    value = summary._infer([dict(source='user_said', text='公开资料。')], lambda: False, deadline=clock + 5.)
    return summary, value


@pytest.mark.parametrize('clock', [0., 105. * 86400., (2 ** 53 - 1024) / 1_000_000.])
def test_microsecond_generation_within_wire_at_zero_105days_and_near_upper_bound(clock):
    client = Client()
    summary, value = infer(client, clock)
    assert value['summary'] == '公开摘要。'
    assert type(summary.generation) is int and 0 <= summary.generation < 2 ** 53
    assert Owner.from_dict(client.calls[0]).generation == summary.generation


def test_upper_bound_fails_before_model_request_without_wrapping_counter():
    client = Client()
    clock = (2 ** 53) / 1_000_000.
    assert int(clock * 1_000_000) >= 2 ** 53
    with pytest.raises(ValueError): infer(client, clock)
    assert client.calls == []


@pytest.mark.parametrize('mutation', ['wrong_owner', 'malformed_error'])
def test_cancel_code_must_pass_exact_wire_validation_before_classification(mutation):
    def mutate(owner, _):
        response = make_response(owner, error='preempted', retryable=True)
        if mutation == 'wrong_owner': response['request_id'] = 'foreign-public-request'
        else: response['error']['retryable'] = 'true'
        return response
    with pytest.raises(WireError): infer(Client(mutate), 100.)


def test_unknown_code_metadata_is_bounded_and_never_copies_response_tokens():
    client = Client(lambda owner, _: make_response(owner, error='SYNTHETIC_PRIVATE_TOKEN', retryable=True))
    summary = policy.BoardSummaryClient(client, board_boot_id='public-boot', clock=lambda: 100.)
    task = dict(sources=[dict(include_in_summary=True, source='user_said', text='公开资料。', metadata={},
                             event_id='public-event', revision=1)],
                schema_version=1, scope=dict(kind='conversation', id='public-scope'), topic='',
                start_utc=1., end_utc=1., required_claims=[])
    with pytest.raises(RuntimeError): summary(task, lambda: False)
    metadata = summary.failure_metadata()
    assert metadata == dict(state='failed', stage='wire_response', code='other', error_class='RuntimeError')


def test_permission_context_summary_validation_and_backoff_logic_ast_are_unchanged():
    old = ast.parse((COLLAB / 'before/board/runtime/board_memory_policy.py').read_bytes())
    new = ast.parse((COLLAB / 'after/board/runtime/board_memory_policy.py').read_bytes())
    for name in ('BoardContextBuilder', 'BoardMemoryCommands'):
        nodes = [next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name) for tree in (old, new)]
        assert ast.dump(nodes[0]) == ast.dump(nodes[1])
    classes = [next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BoardSummaryClient') for tree in (old, new)]
    original = next(n for n in classes[0].body if isinstance(n, ast.FunctionDef) and n.name == '__call__')
    semantic = next(n for n in classes[1].body if isinstance(n, ast.FunctionDef) and n.name == '_summarize')
    class StripStages(ast.NodeTransformer):
        def visit_Assign(self, node):
            if any(isinstance(t, ast.Attribute) and t.attr == '_summary_stage' for t in node.targets): return None
            return self.generic_visit(node)
    semantic = StripStages().visit(semantic)
    semantic.name = '__call__'
    assert ast.dump(original) == ast.dump(semantic)
    backoffs = [ast.parse((COLLAB / mode / 'common/board_memory_backoff.py').read_bytes()) for mode in ('before', 'after')]
    for name in ('_record_failure', '_fail_task', 'step'):
        nodes = [next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name) for tree in backoffs]
        assert ast.dump(nodes[0]) == ast.dump(nodes[1])
