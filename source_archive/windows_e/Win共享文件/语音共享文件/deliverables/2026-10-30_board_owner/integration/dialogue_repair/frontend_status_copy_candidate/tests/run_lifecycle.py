"""Existing real-proxy/capture contracts against the fast metadata copy."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == '__main__':
    entry = load('_status_copy_contract_fixtures', ROOT / 'tests/test_status_copy.py')
    external = load('_status_copy_old_external', INTEGRATION /
        'production_frontend_process_capture_candidate/tests/test_capture_contract_external.py')
    external.AFTER = ROOT / 'after'
    worker = load('_status_copy_old_worker', INTEGRATION /
        'production_frontend_process_capture_candidate/tests/test_worker_ipc.py')
    worker.auto = entry.module
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(external))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(entry.support.FaultSnapshotTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(worker.WorkerTests))
    original = worker.wire.BoardProcessSpeechGate
    def selected(*args, **kwargs):
        kwargs.setdefault('optimization', 'combined')
        return original(*args, **kwargs)
    with patch.object(worker.wire, 'BoardProcessSpeechGate', selected):
        result = unittest.TextTestRunner(verbosity=1).run(suite)
    evidence = dict(tests=result.testsRun, passed=result.wasSuccessful(),
        failures=len(result.failures), errors=len(result.errors), device_opened=False,
        models_loaded=False, real_socketpair_with_fake_model=True)
    (ROOT / 'tests/lifecycle_result.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
