"""Two-hour read-only numeric observations; never controls a model or display."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import urllib.request

EXPECTED_BOOT = '89d53e38-4726-4c94-b958-53f2dfb3bd4e'
REPORT_FIELDS = ('abi_version', 'outcome', 'hardcap', 'guard', 'submitted', 'completed',
    'native_status', 'task', 'start_ns', 'native_return_ns', 'release_decision_ns',
    'after_unlock_ns', 'business_ready', 'result_fresh', 'recovery_phase')
SOURCE = Path(__file__).resolve()
TOKEN = hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
ROOT = Path('/home/root/aura-display-sequence-20261024/unattended') / TOKEN
STOP = False


def atomic(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as out:
        json.dump(value, out, indent=2, sort_keys=True)
        out.write('\n')
    os.replace(temporary, path)


def nonnegative(value):
    if type(value) is not int or value < 0:
        raise ValueError('Expected a nonnegative counter')
    return value


def extract(health, now_ns):
    """Whitelist only numeric/model-health fields; exclude identities and images."""
    schedule = health['dpu_schedule']
    if schedule.get('native_critical') is not True or schedule.get('native_abi') != 2:
        raise ValueError('Unexpected execution backend')
    face = health['identity']['face_targets']
    optional = {}
    for kind in ('yunet', 'sface'):
        job = schedule['optional'][kind]
        policy = job['recovery']
        if policy['phase'] not in ('RUNNING', 'COOLDOWN', 'PROBATION', 'LATCHED'):
            raise ValueError('Unexpected recovery phase')
        report = job.get('last_native_report') or {}
        optional[kind] = dict(calls=nonnegative(job['calls']),
            completed=nonnegative(job['native_completed']), overruns=nonnegative(job['overruns']),
            native_failures=nonnegative(job['native_failures']),
            not_submitted=nonnegative(job['not_submitted']), disabled=bool(job['disabled']),
            phase=policy['phase'], faults=nonnegative(policy['faults']),
            attempts=nonnegative(policy['attempts']), recoveries=nonnegative(policy['recoveries']),
            report={key: nonnegative(report[key]) if key != 'native_status' else int(report[key])
                    for key in REPORT_FIELDS if key in report})
    fallback = face.get('inference') or {}
    return dict(mono_ns=now_ns, pid=nonnegative(health['pid']),
        frames=nonnegative(health['detected_frames']),
        primary_calls=nonnegative(schedule['primary_calls']),
        primary_overruns=nonnegative(schedule['primary_period_overruns']),
        owner_fenced=bool(schedule['owner_fenced']), worker_alive=bool(face['worker_alive']),
        camera_error=bool(health.get('camera_error') or health.get('detector_error')),
        identity_ready=bool(health['identity']['feature_inference']['ready']),
        gaps=nonnegative(face['freshness_metrics']['counters']['observed_gap_intervals']),
        fallback_calls=nonnegative(fallback.get('fallback_calls', 0)), optional=optional)


def compare(before, after):
    if before['pid'] != after['pid']:
        raise ValueError('Observation process changed; do not merge counters')
    ns = after['mono_ns'] - before['mono_ns']
    if ns <= 0:
        raise ValueError('Nonpositive observation window')
    result = dict(seconds=ns / 1e9)
    for key in ('frames', 'primary_calls', 'primary_overruns', 'gaps', 'fallback_calls'):
        delta = after[key] - before[key]
        if delta < 0:
            raise ValueError('Counter decreased: ' + key)
        result[key] = delta
    result['yolo_hz'] = result['frames'] / result['seconds']
    result['optional'] = {}
    for kind in ('yunet', 'sface'):
        counters = {}
        for key in ('calls', 'completed', 'overruns', 'native_failures', 'not_submitted',
                    'faults', 'attempts', 'recoveries'):
            delta = after['optional'][kind][key] - before['optional'][kind][key]
            if delta < 0:
                raise ValueError('Optional counter decreased: ' + kind + '.' + key)
            counters[key] = delta
        result['optional'][kind] = counters
    result['three_model_load_observed'] = result['optional']['sface']['completed'] > 0
    return result


def read_cpu():
    rows = Path('/proc/stat').read_text().splitlines()
    result = {}
    for row in rows:
        fields = row.split()
        if not fields or not fields[0].startswith('cpu'):
            continue
        if fields[0] != 'cpu' and not fields[0][3:].isdigit():
            continue
        values = [int(item) for item in fields[1:9]]
        result[fields[0]] = (sum(values), values[3] + values[4])
    return result


def cpu_delta(before, after):
    result = {}
    for name, (total, idle) in before.items():
        if name not in after:
            continue
        duration = after[name][0] - total
        free = after[name][1] - idle
        if duration > 0 and 0 <= free <= duration:
            result[name] = 100. * (duration - free) / duration
    return result


def observe():
    global STOP
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == EXPECTED_BOOT
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def health():
        with opener.open('http://127.0.0.1:8790/health', timeout=3) as stream:
            return extract(json.load(stream), time.monotonic_ns())
    def stop(*unused):
        global STOP
        STOP = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    start = previous = health()
    first_cpu = read_cpu()
    report = dict(scope='TWO_HOUR_UNPAIRED_PASSIVE_OPERATION_NO_HUMAN_LOAD_REQUIREMENT',
        boot=EXPECTED_BOOT, source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        target_seconds=7200, interval_seconds=2, phase='OBSERVING', before=start,
        health_queries=1, query_failures=0, consecutive_query_failures=0,
        fault_observations=0, report_capture_scope='last reports sampled through existing health; not a lossless native event ring',
        fault_events_lost_possible=True, display_control_commands=0, model_instances_created=0,
        images_saved=0, identities_saved=0, dpu_utilization_measured=False,
        health_snapshot_atomic=False, limitations=['Unpaired workload; cannot infer optimization gain',
            'No visual screen correctness measurement', 'No SFace load claim without completed feature requests'])
    atomic(ROOT / 'progress.json', report)
    failed = 0
    reason = 'DURATION_COMPLETE'
    began = time.monotonic()
    try:
        with (ROOT / 'samples.jsonl').open('x') as samples, (ROOT / 'events.jsonl').open('x') as events:
            while not STOP and time.monotonic() - began < 7200:
                time.sleep(min(2., max(0., 7200 - (time.monotonic() - began))))
                if STOP:
                    break
                try:
                    if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != EXPECTED_BOOT:
                        reason = 'BOOT_CHANGED';break
                    current = health();report['health_queries'] += 1
                    if current['pid'] != start['pid']:
                        report['changed_process_observation'] = current
                        reason = 'CAMERA_PROCESS_CHANGED';break
                    compare(start, current)
                except Exception as exc:
                    failed += 1;report['query_failures'] += 1
                    report['consecutive_query_failures'] = failed
                    events.write(json.dumps(dict(mono_ns=time.monotonic_ns(), error_type=type(exc).__name__)) + '\n')
                    events.flush()
                    if failed >= 5:
                        reason = 'FIVE_CONSECUTIVE_QUERY_OR_COUNTER_FAILURES';break
                    continue
                failed = 0;report['consecutive_query_failures'] = 0
                for kind in ('yunet', 'sface'):
                    old, new = previous['optional'][kind], current['optional'][kind]
                    if any(new[key] != old[key] for key in ('overruns', 'native_failures', 'faults', 'phase', 'recoveries')):
                        event = dict(kind=kind, mono_ns=current['mono_ns'], state=new,
                            exact_fault_report_available=bool(new['report'].get('hardcap') or new['report'].get('guard')
                                or new['report'].get('native_status', 0)))
                        events.write(json.dumps(event, sort_keys=True) + '\n');events.flush()
                        report['fault_observations'] += int(new['faults'] > old['faults'])
                elapsed = (current['mono_ns'] - start['mono_ns']) / 1e9
                if report['health_queries'] % 5 == 0:
                    sample = dict(elapsed_seconds=elapsed, state=current,
                                  cpu_since_start=cpu_delta(first_cpu, read_cpu()))
                    samples.write(json.dumps(sample, sort_keys=True) + '\n');samples.flush()
                report.update(after=current, window=compare(start, current),
                    cpu_since_start=cpu_delta(first_cpu, read_cpu()))
                previous = current
                if report['health_queries'] % 15 == 0:
                    atomic(ROOT / 'progress.json', report)
                if current['owner_fenced'] or not current['worker_alive'] or current['camera_error']:
                    reason = 'BUSINESS_UNAVAILABLE_OBSERVED';break
    finally:
        if STOP:
            reason = 'STOP_REQUESTED'
        report.update(phase='COMPLETE', finish_reason=reason, observer_self_cpu_seconds=time.process_time(),
            observer_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        atomic(ROOT / 'result.json', report)
        atomic(ROOT / 'progress.json', report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observe', action='store_true')
    args = parser.parse_args()
    if args.observe:
        observe();return
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == EXPECTED_BOOT
    ROOT.mkdir(parents=True, exist_ok=False, mode=0o700)
    unit = 'aura-passive-two-hour-' + TOKEN
    subprocess.run(['systemd-run', '--quiet', '--no-block', '--unit=' + unit,
        '--property=Type=oneshot', '--property=RuntimeMaxSec=7350', '--property=TimeoutStopSec=10',
        '/usr/bin/python3', '-B', str(SOURCE), '--observe'], check=True)
    until = time.monotonic() + 6
    while time.monotonic() < until and not (ROOT / 'progress.json').exists():
        time.sleep(.1)
    assert (ROOT / 'progress.json').exists(), 'Observer did not enter readiness'
    print(json.dumps(dict(root=str(ROOT), unit=unit, progress=json.loads((ROOT / 'progress.json').read_text()))))


if __name__ == '__main__':
    main()
