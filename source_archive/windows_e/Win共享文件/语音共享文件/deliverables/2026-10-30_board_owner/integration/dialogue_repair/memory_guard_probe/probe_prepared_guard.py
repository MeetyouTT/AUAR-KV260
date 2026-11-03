"""Public synthetic-only prepared-guard cost probe; no model or device I/O.

Run in a fresh Python process with --aura-root pointing at the pinned source.
Only databases created inside this process's TemporaryDirectory are opened.
JSON output contains timing/count metadata, never IDs, text or database paths.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sqlite3
import sys
import tempfile
import time


STORE_SHA256 = '943bf88c05400c49c76a1aee68a0bb242cb929cee3e213bc21f465ac3ef77d46'


def load_store(aura_root, expected_sha256):
    root = Path(aura_root).resolve(strict=True)
    source = root / 'common' / 'board_memory.py'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ValueError('Pinned Store source mismatch')
    sys.path.insert(0, str(root))
    name = 'common.public_guard_probe_store'
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, digest


def percentile(values, fraction):
    values = sorted(values)
    return values[max(0, math.ceil(len(values) * fraction) - 1)]


def one_case(memory, directory, dependencies, iterations):
    path = directory / ('public-' + str(dependencies) + '.sqlite3')
    store = memory.BoardMemoryStore(path, clock=lambda: 1000., data_origin='synthetic')
    scope = dict(kind='conversation', id='public-guard-probe-scope')
    refs = []
    for index in range(dependencies - 1):
        event_id = 'public-source-' + str(index)
        store.append_event(scope, event_id, 'user_said', '公开合成事实。')
        refs.append(event_id)
    store.begin_turn(scope, 'public-probe-turn', '公开合成请求。', generation=1)
    store.generated('public-probe-turn', '公开合成回答。', generation=1,
                    source_event_ids=refs, provenance_complete=True)
    db = sqlite3.connect(path)
    try:
        actual_dependencies = db.execute('SELECT COUNT(*) FROM bm_event_dependencies').fetchone()[0]
    finally:
        db.close()
    assert actual_dependencies == dependencies
    before = hashlib.sha256(path.read_bytes()).digest()
    for _ in range(3):
        assert store.check_prepared_turn_current('public-probe-turn', generation=1)
    samples = []
    cpu_start, wall_start = time.process_time_ns(), time.perf_counter_ns()
    for _ in range(iterations):
        started = time.perf_counter_ns()
        assert store.check_prepared_turn_current('public-probe-turn', generation=1)
        samples.append((time.perf_counter_ns() - started) / 1_000_000.)
    elapsed = (time.perf_counter_ns() - wall_start) / 1_000_000.
    cpu = (time.process_time_ns() - cpu_start) / 1_000_000.
    after = hashlib.sha256(path.read_bytes()).digest()
    assert before == after
    # Instrument one extra check separately; tracing overhead is excluded from
    # the performance measurements above. Discard all actual SQL strings.
    counters = dict(connections=0, closes=0, selects=0, pragmas=0, begins=0, commits=0)
    connect = sqlite3.connect
    class CountedConnection(sqlite3.Connection):
        def close(self):
            counters['closes'] += 1
            return super().close()
    def traced(sql):
        operation = sql.lstrip().split(None, 1)[0].upper()
        key = {'SELECT': 'selects', 'PRAGMA': 'pragmas', 'BEGIN': 'begins', 'COMMIT': 'commits'}.get(operation)
        if key is not None:
            counters[key] += 1
    def counted_connect(*args, **kwargs):
        counters['connections'] += 1
        kwargs['factory'] = CountedConnection
        connection = connect(*args, **kwargs)
        connection.set_trace_callback(traced)
        return connection
    sqlite3.connect = counted_connect
    try:
        assert store.check_prepared_turn_current('public-probe-turn', generation=1)
    finally:
        sqlite3.connect = connect
    assert counters['connections'] == counters['closes']
    return dict(dependencies=actual_dependencies, iterations=iterations,
        wall_ms=round(elapsed, 3), process_cpu_ms=round(cpu, 3),
        mean_ms=round(sum(samples) / len(samples), 3),
        median_ms=round(percentile(samples, .5), 3), p95_ms=round(percentile(samples, .95), 3),
        maximum_ms=round(max(samples), 3), over_20ms=sum(value > 20. for value in samples),
        packet_20ms_budget_fraction=round((sum(samples) / len(samples)) / 20., 4),
        readonly_db_hash_unchanged=before == after, traced_check_counts=counters)


def run(aura_root, expected_sha256=STORE_SHA256):
    memory, digest = load_store(aura_root, expected_sha256)
    values = []
    # The only recursive cleanup is performed by TemporaryDirectory on the
    # unique directory it created itself. No caller-supplied DB path exists.
    with tempfile.TemporaryDirectory(prefix='aura-public-memory-guard-') as temporary:
        directory = Path(temporary)
        values.append(one_case(memory, directory, 1, 100))
        values.append(one_case(memory, directory, 8, 100))
        extra = sum(value['wall_ms'] for value in values) < 1000.
        if extra:
            values.append(one_case(memory, directory, 32, 25))
    return dict(schema='aura.public-prepared-guard-probe.v1', status='PASS',
        store_sha256=digest, origin='synthetic', cases=values,
        optional_32_dependency_case_ran=extra, temporary_directory_cleaned=not directory.exists(),
        real_database_accessed=False, model_or_device_used=False,
        timing_includes_tracing=False, claim='microbenchmark_only_not_actual_playback_acceptance')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--aura-root', required=True)
    parser.add_argument('--store-sha256', default=STORE_SHA256)
    args = parser.parse_args()
    try:
        if len(args.store_sha256) != 64 or any(c not in '0123456789abcdef' for c in args.store_sha256):
            raise ValueError('Invalid expected source digest')
        result = run(args.aura_root, args.store_sha256)
    except Exception as exc:
        print(json.dumps(dict(schema='aura.public-prepared-guard-probe.v1', status='FAIL',
                              error_type=type(exc).__name__), sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
