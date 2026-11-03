"""Evaluate one live observation stream, bounded to 10s, with no actuator IO."""
import argparse
import dataclasses
import http.client
import json
import os
from pathlib import Path
import statistics
import sys
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--duration', type=float, default=10.)
    a = p.parse_args()
    if os.uname().machine != 'aarch64' or not 0 < a.duration <= 10 or not a.app_root.is_dir():
        p.error('Live KV260 source clock and duration <=10s required')
    sys.path.insert(0, str(a.app_root.resolve()))
    from shadow_follow import FollowConfig, PanFollowController, ShadowDriver
    cfg = json.loads(a.config.read_text())
    assert cfg['mode'] == 'SOFTWARE_SHADOW' and cfg['physical_actuation_enabled'] is False
    assert cfg['direction_verified'] is False and cfg['reference_is_mechanical'] is False
    assert cfg['mechanical_calibration_verified'] is False and cfg['shadow_reference_us'] == 1425
    assert cfg['camera_mounting_assumption'] == 'axis'
    assert cfg['polarity_assumption'] == 'UNVERIFIED_CAMERA_TO_PULSE_DIRECTION'
    assert set(cfg['controller']) == {f.name for f in dataclasses.fields(FollowConfig)}
    control = FollowConfig(**cfg['controller'])
    assert control.pulse_min_us == 1425 and control.pulse_max_us == 1445 and control.max_offset_us <= 20
    driver = ShadowDriver()
    follower = PanFollowController(driver, Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                                   reference_us=1425, polarity=-1, config=control, physical=False)
    output = a.output.resolve()
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output.parent, 0o700)
    fd = os.open(str(output), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    counts, seen, ages = {}, set(), []
    error = None
    started = time.monotonic()
    connection = http.client.HTTPConnection('127.0.0.1', 8790, timeout=.3)
    try:
        with os.fdopen(fd, 'w') as log:
            connection.request('GET', '/v1/motion/stream?duration_ms=' + str(round(a.duration*1000)))
            response = connection.getresponse()
            if response.status != 200:
                raise RuntimeError('Observation stream HTTP ' + str(response.status))
            while time.monotonic() - started < a.duration:
                line = response.readline(8193)
                if not line:
                    break
                if len(line) > 8192 or not line.endswith(b'\n'):
                    raise ValueError('Unbounded or partial observation stream packet')
                packet = json.loads(line)
                now = int(time.monotonic()*1000)
                state = packet.get('state', 'INVALID')
                counts[state] = counts.get(state, 0) + 1
                if state == 'READY':
                    seen.add((packet.get('camera_epoch'), packet.get('source_frame_id')))
                    stamp = packet.get('source_mono_ms')
                    if type(stamp) is int:
                        ages.append(now-stamp)
                result = follower.observe(packet, now)
                result.pop('target', None)
                log.write(json.dumps(result, separators=(',', ':')) + '\n')
                log.flush()
                if follower.stopped:
                    break
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)[:120]
    finally:
        connection.close()
        if not follower.stopped:
            follower.stop('INPUT_ERROR' if error else 'TIME_LIMIT')
    elapsed = time.monotonic()-started
    pulses = [p for p, _ in driver.submissions]
    summary = {'status': 'ERROR' if error else 'SHADOW_EVALUATION_FINISHED', 'error': error,
               'transport': 'bounded_HTTP_observation_stream', 'elapsed_s': round(elapsed, 3),
               'physical_actuation': False, 'register_writes': 0, 'driver': 'ShadowDriver',
               'rows': sum(counts.values()), 'state_counts': counts, 'distinct_ready_sources': len(seen),
               'source_age_ms_max': max(ages) if ages else None,
               'source_age_ms_p50': statistics.median(ages) if ages else None,
               'suggestion_count': len(pulses), 'suggestion_min_us': min(pulses) if pulses else None,
               'suggestion_max_us': max(pulses) if pulses else None, 'suggestion_limits_us': [follower.low, follower.high],
               'direction_verified': False, 'reference_is_mechanical': False,
               'final_state': follower.status()['state'], 'final_reason': follower.reason,
               'full_duration_completed': follower.reason == 'TIME_LIMIT' and elapsed >= a.duration-.15}
    sf = os.open(str(output)+'.summary.json', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(sf, 'w') as stream:
        stream.write(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary), flush=True)
    return 1 if error else 0


if __name__ == '__main__':
    raise SystemExit(main())
