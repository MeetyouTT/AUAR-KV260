"""Strict acceptance for a synthetic observer cost report, never a board gain."""
import json
import math
from pathlib import Path
import sys

from prepare_sources import PINS, EXPECTED_TESTS

ITERATIONS = 200
ADDED_MEAN_LIMIT_MS = .5


def number(value, label, *, nonnegative=True):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(label + ': finite number required')
    if nonnegative and value < 0:
        raise ValueError(label + ': negative measurement')
    return value


def summary(value, label):
    if type(value) is not dict or type(value.get('count')) is not int or value['count'] != ITERATIONS:
        raise ValueError(label + ': incomplete sample count')
    mean = number(value.get('mean_ms'), label)
    minimum = number(value.get('min_ms'), label)
    maximum = number(value.get('max_ms'), label)
    if not minimum <= mean <= maximum:
        raise ValueError(label + ': inconsistent summary')
    return mean


def evaluate(report):
    failures, differences = [], {}
    try:
        if type(report) is not dict:
            raise ValueError('Report must be an object')
        if report.get('schema') != 'aura-synthetic-freshness-light-preflight-1' or report.get('complete') is not True:
            raise ValueError('Incomplete or unrecognized report')
        if report.get('source_sha256') != PINS:
            raise ValueError('Sources differ from the reviewed observer')
        if (report.get('execution_scope') != 'synthetic_no_devices'
                or type(report.get('new_dpu_jobs')) is not int or report['new_dpu_jobs'] != 0
                or report.get('board_connected') is not False):
            raise ValueError('Only device-free synthetic execution is accepted')
        tests = report['tests']
        if (tests.get('successful') is not True or type(tests.get('run')) is not int or tests['run'] != EXPECTED_TESTS
                or any(type(tests.get(k)) is not int or tests[k] != 0 for k in ('failures', 'errors', 'skipped'))):
            raise ValueError('All light32 tests must run and pass without skips')
        bench = report['benchmark']
        if bench.get('iterations') != ITERATIONS or bench.get('real_clocks_verified') is not True:
            raise ValueError('Benchmark scope/count/real clocks are not verified')
        if (tests.get('pid') == bench.get('pid') or type(tests.get('pid')) is not int
                or type(bench.get('pid')) is not int or tests['pid'] <= 0 or bench['pid'] <= 0):
            raise ValueError('Virtual-clock tests and real-clock benchmark need separate workers')
        for case in ('normal_empty_face', 'slot_unavailable', 'full_event_health_outer_lock'):
            rows = bench['cases'][case]
            means = {}
            for mode in ('original', 'off', 'on'):
                row = rows[mode]
                if row.get('iterations_completed') != ITERATIONS or row.get('closed_cleanly') is not True:
                    raise ValueError(case + '/' + mode + ': incomplete loop/close')
                if row.get('behavior_verified') is not True:
                    raise ValueError(case + '/' + mode + ': behavior mismatch')
                if mode == 'on' and (row.get('observer_complete') is not True
                        or type(row.get('observer_failures')) is not int or row['observer_failures'] != 0):
                    raise ValueError(case + ': observer incomplete')
                if mode == 'on' and (row.get('observer_schema') != 'aura-face-freshness-light-1'
                        or row.get('internal_attempt_wall_or_cpu_collected') is not False):
                    raise ValueError(case + ': incorrect light observer scope')
                if mode != 'on' and any(row.get(key) is not None for key in (
                        'observer_complete', 'observer_failures', 'observer_schema',
                        'internal_attempt_wall_or_cpu_collected')):
                    raise ValueError(case + ': disabled observer measurements must be absent, not zero')
                means[mode] = {clock: summary(row[clock], case + '/' + mode + '/' + clock)
                               for clock in ('wall', 'thread_cpu')}
            differences[case] = {}
            for name, a, b in (('on_minus_original', 'on', 'original'), ('on_minus_off', 'on', 'off'),
                               ('off_minus_original', 'off', 'original')):
                delta = {clock: means[a][clock] - means[b][clock] for clock in ('wall', 'thread_cpu')}
                differences[case][name] = delta
                if any(value > ADDED_MEAN_LIMIT_MS for value in delta.values()):
                    failures.append(case + '/' + name + ': added mean exceeds 0.5 ms')
        if bench['cases']['full_event_health_outer_lock']['on'].get('events_before_measurement') != 16:
            raise ValueError('Full-event snapshot benchmark was not full')
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as exc:
        failures.append(str(exc))
    return {'schema': 'aura-synthetic-freshness-light-assessment-1', 'passed': not failures,
            'failures': failures, 'signed_mean_differences_ms': differences,
            'added_mean_limit_ms': ADDED_MEAN_LIMIT_MS,
            'scope': 'synthetic service hooks/health only, not full vision or identity workload',
            'physical_board_verified': False, 'speedup_or_ttl_improvement_proven': False,
            'allows_automatic_deployment': False}


if __name__ == '__main__':
    try:
        value = json.loads(Path(sys.argv[1]).read_text(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
        result = evaluate(value)
    except (OSError, ValueError, IndexError) as exc:
        result = {'passed': False, 'failures': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    raise SystemExit(0 if result['passed'] else 1)
