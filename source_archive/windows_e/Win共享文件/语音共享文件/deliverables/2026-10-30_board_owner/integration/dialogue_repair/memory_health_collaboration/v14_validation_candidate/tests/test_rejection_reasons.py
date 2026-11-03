import importlib.util
import ast
from pathlib import Path
import random

import pytest

from common.board_memory import CandidateRejected, validate_compaction_text


@pytest.mark.parametrize('text,body,meta,reason', [
    ('用户说明。', '普通', {'names':['合成人名']}, 'protected_name_missing'),
    ('用户说明。', '有42个', {}, 'protected_number_missing_or_changed'),
    ('用户说明。', '普通', {'numbers':[0]}, 'protected_number_missing_or_changed'),
    ('用户说明。', '不能做', {}, 'negation_missing'),
    ('用户说明。', '普通', {'negated':True}, 'negation_missing'),
    ('用户说明。', '普通', {'status':'planned'}, 'planned_status_missing'),
    ('用户说明。', '普通', {'status':'completed'}, 'completed_status_missing'),
    ('用户说明。', '普通', {'status':'cancelled'}, 'cancelled_status_missing'),
    ('用户说明。', '普通', {'evidence':'visual_observation'}, 'observation_evidence_missing'),
])
def test_fixed_code_identifies_the_preserved_rejection_rule(text, body, meta, reason):
    source = dict(include_in_summary=True, text=body, metadata=meta)
    with pytest.raises(CandidateRejected) as caught:
        validate_compaction_text(text, [source])
    assert caught.value.rejection_reasons == (reason,)
    assert '合成人名' not in str(caught.value)


def test_multiple_missing_fields_are_reported_without_values_or_exception_parsing():
    source = dict(include_in_summary=True, text='尚未做42个。',
        metadata=dict(names=['SYNTHETIC_PRIVATE_NAME'], numbers=[42], negated=True, evidence='visual_observation'))
    with pytest.raises(CandidateRejected) as caught:
        validate_compaction_text('用户说明。', [source])
    assert caught.value.rejection_reasons == ('protected_name_missing', 'protected_number_missing_or_changed',
        'negation_missing', 'observation_evidence_missing')
    assert all('PRIVATE' not in value and '42' not in value for value in caught.value.rejection_reasons)


def test_validator_acceptance_matches_unchanged_v13_across_synthetic_combinations():
    here = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('common.v13_parity_memory', here/'before/common/board_memory.py')
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    rng = random.Random(1314)
    words = ['相机观察', '合成人名', '42', '0', '尚未', '计划', '已经完成', '取消', '普通说明']
    def accepted(validate, text, sources):
        try:
            validate(text, sources)
            return True
        except ValueError:
            return False
    for _ in range(1500):
        meta = {}
        if rng.choice((True,False)): meta['names'] = ['合成人名']
        if rng.choice((True,False)): meta['numbers'] = [42,0]
        if rng.choice((True,False)): meta['negated'] = True
        if rng.choice((True,False)): meta['evidence'] = 'visual_observation'
        status = rng.choice((None,'planned','completed','cancelled'))
        if status is not None: meta['status'] = status
        sources = [dict(include_in_summary=True, text='尚未做42个。', metadata=meta)]
        text = '；'.join(word for word in words if rng.choice((True,False))) or '普通'
        assert accepted(previous.validate_compaction_text, text, sources) == accepted(validate_compaction_text, text, sources)


def test_every_store_worker_and_permission_function_is_unchanged():
    here = Path(__file__).resolve().parents[1]
    def unchanged_ast(folder):
        tree = ast.parse((here/folder/'common/board_memory.py').read_text(encoding='utf-8'))
        permitted = {'CandidateRejected', 'validate_compaction_text', 'COMPACTION_REJECTION_REASONS'}
        def name(node):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                return node.name
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                return node.targets[0].id
            return None
        tree.body = [node for node in tree.body if name(node) not in permitted]
        return ast.dump(tree, include_attributes=False)
    assert unchanged_ast('before') == unchanged_ast('after')
