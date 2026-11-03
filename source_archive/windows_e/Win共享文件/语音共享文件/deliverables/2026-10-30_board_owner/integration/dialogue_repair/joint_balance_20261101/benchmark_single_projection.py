"""Public RAM-only ABBA microbenchmark; never an end-to-end performance claim."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time

from test_single_projection import OLD, NEW, fixture, lifecycle, old_metadata, new_metadata

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--iterations', type=int, default=500)
    parser.add_argument('--output')
    args = parser.parse_args()
    if not 100 <= args.iterations <= 2000:
        parser.error('iterations must be 100..2000')
    cases = {'small_public': fixture()}
    larger = fixture()
    larger['metadata'] = [dict(slot=i, enabled=True, counts=list(range(12)),
                               status=dict(age_ms=40., phase='READY'), nested=fixture()) for i in range(32)]
    cases['larger_public'] = larger
    result = dict(schema='aura-single-projection-ram-benchmark-1',
                  scope='fixed_public_fake_metadata_only', host_machine=__import__('platform').machine(),
                  source_before_sha256=hashlib.sha256((HERE / 'baseline/tools/production_memory_presentation.py').read_bytes()).hexdigest(),
                  source_after_sha256=hashlib.sha256((HERE / 'presentation_candidate/tools/production_memory_presentation.py').read_bytes()).hexdigest(),
                  whole_board_or_real_dialogue_gain_claimed=False, device_access=False, cases={})
    for label, state in cases.items():
        values = []
        expected = None
        for version in ('old', 'new', 'new', 'old'):
            mod, call = (OLD, old_metadata) if version == 'old' else (NEW, new_metadata)
            life, _, _ = lifecycle(mod)
            for _ in range(16):
                with life.lock:
                    call(life, state)
            began = time.perf_counter_ns()
            cpu = time.thread_time_ns()
            for _ in range(args.iterations):
                with life.lock:
                    output = call(life, state)
            elapsed_cpu = time.thread_time_ns() - cpu
            elapsed = time.perf_counter_ns() - began
            encoded = json.dumps(output, sort_keys=True, separators=(',', ':')).encode()
            digest = hashlib.sha256(encoded).hexdigest()
            if expected is None:
                expected = digest
            if digest != expected:
                raise AssertionError('public output changed')
            values.append(dict(version=version, calls=args.iterations,
                               wall_us_per_call=elapsed / args.iterations / 1000,
                               cpu_us_per_call=elapsed_cpu / args.iterations / 1000,
                               output_sha256=digest))
        old = statistics.mean(row['cpu_us_per_call'] for row in values if row['version'] == 'old')
        new = statistics.mean(row['cpu_us_per_call'] for row in values if row['version'] == 'new')
        result['cases'][label] = dict(slots=values, input_json_bytes=len(json.dumps(state).encode()),
                                      equal_output=True, old_mean_cpu_us=old, new_mean_cpu_us=new,
                                      observed_cpu_change_percent=(new / old - 1) * 100 if old else None)
    raw = json.dumps(result, indent=2) + '\n'
    if args.output:
        path = Path(args.output)
        with path.open('x', encoding='utf-8') as handle:
            handle.write(raw)
    print(raw)


if __name__ == '__main__':
    main()
