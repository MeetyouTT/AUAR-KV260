"""Synthetic same-boot proof using the unchanged executor's public fixtures."""
import copy
import importlib.util
from pathlib import Path

import pytest

import restored_readback as adapter


HERE = Path(__file__).resolve().parent
OLD_TEST = HERE.parent.parent / 'resume_camera_pin/test_same_boot_readback.py'
spec = importlib.util.spec_from_file_location('prior_same_boot_public_tests', OLD_TEST)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


@pytest.fixture
def public_complete(monkeypatch):
    env = prior.env.__wrapped__(monkeypatch)
    helper = adapter.load_helper()
    authority = dict(env.a, baseline_pin_count=21)
    data = helper.parse(env.s.files[authority['journal_path']])
    baseline = helper.parse(env.s.files[authority['baseline_path']])
    for index in range(2):
        name = '/public/extra-inherited-source-' + str(index) + '.py'
        env.s.files[name] = ('public added pin ' + str(index)).encode()
        expected = helper.digest(env.s.files[name])
        baseline['source_sha256'][name] = expected
        data['pins'][name] = expected
    env.s.files[authority['baseline_path']] = helper.encoded(baseline)
    authority['baseline_sha256'] = helper.digest(env.s.files[authority['baseline_path']])
    data['baseline_config'] = baseline
    data['readback_sha256'] = authority['baseline_sha256']
    env.s.files[authority['journal_path']] = helper.encoded(data)
    authority['journal_sha256'] = helper.digest(env.s.files[authority['journal_path']])
    return env, helper, authority


def test_explicit_authority_uses_current21_and_adds_only_final_runtime(public_complete):
    env, helper, authority = public_complete
    files = copy.deepcopy(env.s.files)
    commands = list(env.s.commands)
    candidate, report = adapter.prove(helper, authority, executor=prior.exe, system=env.s, reader=env.s.read)
    baseline = helper.parse(files[authority['baseline_path']])
    assert report['ready'] and not report['written']
    assert len(baseline['source_sha256']) == 21
    assert len(candidate['source_sha256']) == 22
    assert set(candidate['source_sha256']) - set(baseline['source_sha256']) == {candidate['camera_config']}
    assert all(candidate['source_sha256'][k] == value for k, value in baseline['source_sha256'].items())
    assert all(candidate[k] == baseline[k] for k in ('database', 'identity_config', 'model_id', 'dimension',
                                                   'model_sha256', 'result_ttl_ms', 'backend'))
    assert helper.AUTHORITY is authority
    assert env.s.files == files and env.s.commands == commands
    assert '/PRIVATE_DB_MUST_NEVER_OPEN' not in env.s.reads


@pytest.mark.parametrize('field', ['boot', 'journal_sha256', 'checkpoint_sha256', 'manifest_sha256',
                                  'candidate_pid', 'restored_pid', 'baseline_pin_count'])
def test_wrong_explicit_completed_provenance_is_refused(public_complete, field):
    env, helper, authority = public_complete
    changed = dict(authority)
    changed[field] = changed[field] + 1 if type(changed[field]) is int else '0' * 64
    with pytest.raises((helper.Refused, prior.exe.Refused)):
        adapter.prove(helper, changed, executor=prior.exe, system=env.s, reader=env.s.read)


def test_production_authority_requires_fixed_current_boot_stage_and_baseline():
    helper = adapter.load_helper()
    authority = dict(adapter.FIXED, candidate_pid=9001, restored_pid=9002,
                     checkpoint_sha256='a' * 64, journal_sha256='b' * 64)
    assert adapter.validate_authority(authority, helper) == authority
    for key in adapter.FIXED:
        wrong = dict(authority)
        wrong[key] = wrong[key] + 1 if type(wrong[key]) is int else 'changed'
        with pytest.raises(ValueError):
            adapter.validate_authority(wrong, helper)
    for key, value in [('candidate_pid', 1335), ('restored_pid', 9001),
                       ('candidate_pid', True), ('journal_sha256', ''), ('checkpoint_sha256', None)]:
        with pytest.raises(ValueError):
            adapter.validate_authority(dict(authority, **{key: value}), helper)
