"""Fake-device controller checks only, when reviewing a changed input gate."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import unittest

REVIEW = Path(__file__).resolve().parents[1]
TASK = REVIEW.parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', choices=('r1', 'r2'), required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--witness-only', action='store_true')
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    paths = [TASK / 'candidate/controller', TASK / 'candidate/aura',
             REVIEW / 'tests', TASK / 'tests/fixtures', TASK / 'tests']
    if args.source == 'r2':
        paths.insert(0, REVIEW / 'candidate_r2/controller')
    sys.path[:0] = [str(path) for path in paths]
    names = ['test_duplicate_clock_safety']
    if not args.witness_only:
        names[:0] = ['test_hardware_slew', 'test_wide_range', 'test_session_target_lock']
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in names)
    log = REVIEW / 'evidence' / (args.label + '.log')
    with log.open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    import continuous_session
    import session_target_lock
    record = dict(source=args.source, witness_only=args.witness_only, tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), passed=result.wasSuccessful(),
        continuous_session_sha256=hashlib.sha256(Path(continuous_session.__file__).read_bytes()).hexdigest(),
        session_target_lock_sha256=hashlib.sha256(Path(session_target_lock.__file__).read_bytes()).hexdigest(),
        log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
        why_tests_needed='Changed duplicate gate must preserve original invalid-clock STOP and controller regressions',
        device_accessed=False, network_accessed=False, native_library_loaded=False,
        scope='independent-clock fake registers and synthetic packets only')
    (REVIEW / 'evidence' / (args.label + '.json')).write_text(
        json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record))
    return int(not result.wasSuccessful())


if __name__ == '__main__':
    raise SystemExit(main())
