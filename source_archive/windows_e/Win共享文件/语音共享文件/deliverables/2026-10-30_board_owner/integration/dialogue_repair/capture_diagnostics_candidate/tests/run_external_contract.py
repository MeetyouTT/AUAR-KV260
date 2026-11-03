"""Run the frozen 12 capture contracts against the new diagnostic proxy."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == '__main__':
    load('_capture_diagnostics_newtests', ROOT / 'tests/test_capture_diagnostics.py')
    path = ROOT.parents[1] / 'production_frontend_process_capture_candidate/tests/test_capture_contract_external.py'
    expected = '3a9baa97240b32afaf8c537a7758cb76267d06fa848f6c628beb419f6482164f'
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit('Frozen contract fixture changed')
    module = load('_capture_diagnostics_frozen_contract', path)
    module.AFTER = ROOT / 'after'
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    evidence = dict(source_sha256=hashlib.sha256((ROOT / 'after/board/runtime/audio/board_frontend_auto.py').read_bytes()).hexdigest(),
        fixture_sha256=expected, tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        passed=result.wasSuccessful(), device_opened=False, models_loaded=False)
    (ROOT / 'external_contract_result.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
