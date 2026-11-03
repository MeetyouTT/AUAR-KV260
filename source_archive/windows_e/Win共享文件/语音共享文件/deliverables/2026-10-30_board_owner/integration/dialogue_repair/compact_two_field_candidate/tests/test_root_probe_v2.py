"""Replay unchanged wrapper cases against v2; pin original D01 source bytes."""
import importlib.util
from pathlib import Path
import sys

import pytest

HERE = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value; spec.loader.exec_module(value)
    return value


original_tests = load('root_v2_unchanged_case_definitions', HERE/'tests/test_root_probe.py')
probe = load('root_v2_tested', HERE/'root_public_probe_v2.py')
original_tests.probe = probe
for name, value in tuple(vars(original_tests).items()):
    if name.startswith('test_') and callable(value):
        globals()[name] = value


def test_v2_validates_actual_public_before_and_after_sources_without_operations():
    pins = probe.verified_sources()
    assert pins['live_sources']['tools/model_inference_host.py'] == (
        'fd4a8c334658f9720068fceeae664fd1771a8664e7aa02b0c0656f36619ebc65')


def test_v2_refuses_changed_original_d01_contract_before_backend_setup(monkeypatch):
    real_sha = probe.sha
    target = HERE/'before/common/inference_output_contract.py'
    monkeypatch.setattr(probe, 'sha', lambda path: '0'*64 if path==target else real_sha(path))
    with pytest.raises(probe.TrialError) as caught:
        probe.verified_sources()
    assert caught.value.code == 'SOURCE_PIN_CHANGED'
