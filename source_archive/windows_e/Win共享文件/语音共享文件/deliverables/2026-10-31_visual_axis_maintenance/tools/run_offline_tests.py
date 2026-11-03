"""Run fake-device regressions in a fresh Python process, without native IO."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tree', choices=('baseline', 'candidate'), required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    selected = ROOT / args.tree
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(selected / 'controller'), str(selected / 'aura'),
                   str(ROOT / 'tests/fixtures'), str(ROOT / 'tests')]
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in ('test_hardware_slew', 'test_wide_range', 'test_session_target_lock',
                 'test_follow_report_freshness'):
        suite.addTests(loader.loadTestsFromName(name))
    evidence = ROOT / 'evidence'
    log_path = evidence / (args.label + '.log')
    began = time.monotonic()
    with log_path.open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    records = []
    for path in sorted(selected.rglob('*.py')):
        raw = path.read_bytes()
        records.append(dict(path=path.relative_to(selected).as_posix(), sha256=hashlib.sha256(raw).hexdigest()))
    report = dict(tree=args.tree, tests=result.testsRun, failures=len(result.failures),
        errors=len(result.errors), skipped=len(result.skipped), passed=result.wasSuccessful(),
        elapsed_s=round(time.monotonic()-began, 4),
        failure_tests=[str(x[0]) for x in result.failures],
        error_tests=[str(x[0]) for x in result.errors],
        source_pins=records, log_sha256=hashlib.sha256(log_path.read_bytes()).hexdigest(),
        physical_device_opened=False, network_accessed=False, models_loaded=False,
        camera_source_modified=False, production_source_written=False,
        scope='pure Python fake registers, synthetic face boxes; not electrical, mechanical, identity accuracy or live acceptance')
    (evidence / (args.label + '.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_pins','failure_tests','error_tests')}))
    return int(not result.wasSuccessful())


if __name__ == '__main__':
    raise SystemExit(main())
