"""Run only new layout/reconciliation checks; existing probe behavior is identical."""
from pathlib import Path
import hashlib
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / 'tests'))
    suite = unittest.defaultTestLoader.loadTestsFromName('test_driver_layout')
    log = ROOT / 'evidence/layout_tests.log'
    with log.open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    value = dict(status='LAYOUT_TESTS_PASSED' if result.wasSuccessful() else 'LAYOUT_TESTS_FAILED',
        tests=result.testsRun, failures=len(result.failures), errors=len(result.errors), passed=result.wasSuccessful(),
        v2_script_sha256=hashlib.sha256((ROOT / 'probe_bundle_v2/run_readonly_probe.py').read_bytes()).hexdigest(),
        log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(), prior_28_test_probe_behavior_unchanged=True,
        actual_board_executed=False, movement_or_driver_import=False,
        scope='hash-bound source AST, saved fixed metadata and public fake filesystem')
    (ROOT / 'evidence/layout_tests.json').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(value))
    return int(not result.wasSuccessful())


if __name__ == '__main__':
    raise SystemExit(main())
