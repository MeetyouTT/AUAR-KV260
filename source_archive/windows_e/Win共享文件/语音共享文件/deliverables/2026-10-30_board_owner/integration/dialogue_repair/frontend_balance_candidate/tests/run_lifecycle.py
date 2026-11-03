"""Frozen old wire/complete-capture contracts against the selected new proxy."""
import hashlib
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
    entry = load('_balance_mode_test_fixtures', ROOT / 'tests/test_mode_entry.py')
    legacy, wire = entry.legacy, entry.wire
    worker = load('_balance_complete_capture_contracts', INTEGRATION /
        'production_frontend_process_capture_candidate/tests/test_worker_ipc.py')
    worker.wire, worker.auto = wire, entry.auto
    results = []
    suite = unittest.TestSuite()
    for cls in (legacy.ProcessTests, legacy.ProtocolTests):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    results.append(dict(kind='original_wire', tests=result.testsRun, passed=result.wasSuccessful()))
    original = wire.BoardProcessSpeechGate
    for mode in ('baseline', 'combined'):
        def selected(*args, **kwargs):
            kwargs.setdefault('optimization', mode)
            return original(*args, **kwargs)
        suite = unittest.TestSuite()
        for cls in (worker.WorkerTests, worker.GuardTests):
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
        with patch.object(wire, 'BoardProcessSpeechGate', selected):
            result = unittest.TextTestRunner(verbosity=1).run(suite)
        results.append(dict(kind='full_capture_' + mode, tests=result.testsRun, passed=result.wasSuccessful()))
    evidence = dict(source_sha256=hashlib.sha256((ROOT / 'after/board/runtime/audio/board_frontend_process.py').read_bytes()).hexdigest(),
        results=results, tests=sum(r['tests'] for r in results), passed=all(r['passed'] for r in results),
        model='synthetic gate', devices_opened=False, priority_changed=False)
    (ROOT / 'tests/lifecycle_result.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(0 if evidence['passed'] else 1)
