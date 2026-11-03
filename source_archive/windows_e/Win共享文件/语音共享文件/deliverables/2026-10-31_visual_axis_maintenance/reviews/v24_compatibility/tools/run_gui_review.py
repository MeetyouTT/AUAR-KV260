"""Only GUI freshness and dialog integration tests; no GTK/device startup."""
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
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    if args.source == 'r2':
        sys.path.insert(0, str(REVIEW / 'candidate_r2/aura'))
    sys.path.extend([str(TASK / 'candidate/aura'), str(REVIEW / 'tests'), str(TASK / 'tests')])
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in (
        'test_follow_report_freshness', 'test_dialog_stop_integration'))
    evidence = REVIEW / 'evidence'
    log = evidence / (args.label + '.log')
    with log.open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    import tools.face_pan_controls as tested
    record = dict(source=args.source, tests=result.testsRun, failures=len(result.failures),
        errors=len(result.errors), passed=result.wasSuccessful(),
        tested_gui_sha256=hashlib.sha256(Path(tested.__file__).read_bytes()).hexdigest(),
        log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
        device_accessed=False, gtk_started=False, network_accessed=False,
        original_controller_tests_repeated=False,
        scope='real stage method composition; test widgets; no physical acceptance')
    (evidence / (args.label + '.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record))
    return int(not result.wasSuccessful())


if __name__ == '__main__':
    raise SystemExit(main())
