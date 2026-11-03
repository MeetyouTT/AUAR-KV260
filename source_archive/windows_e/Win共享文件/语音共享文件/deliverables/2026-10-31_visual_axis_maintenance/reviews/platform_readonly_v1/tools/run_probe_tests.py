"""Run only the new read-only probe's fake filesystem/HTTP checks."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', default='probe_tests')
    args = parser.parse_args()
    assert args.label.replace('_', '').isalnum()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / 'tests'))
    suite = unittest.defaultTestLoader.loadTestsFromName('test_readonly_probe')
    log = ROOT / 'evidence' / (args.label + '.log')
    with log.open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    script = ROOT / 'probe_bundle/run_readonly_probe.py'
    report = dict(status='PROBE_TESTS_PASSED' if result.wasSuccessful() else 'PROBE_TESTS_FAILED',
        tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        passed=result.wasSuccessful(), script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
        log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
        physical_device_or_network_accessed=False, existing_r2_regressions_repeated=False,
        scope='fake filesystem and mocked loopback HTTP; no board execution')
    (ROOT / 'evidence' / (args.label + '.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))
    return int(not result.wasSuccessful())


if __name__ == '__main__':
    raise SystemExit(main())
