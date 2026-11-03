"""Consume the current camera feed for at most 10 seconds; never opens PWM IO."""
import argparse
import dataclasses
import http.client
import json
import os
from pathlib import Path
import statistics
import sys
import time

from shadow_follow import FollowConfig, PanFollowController, ShadowDriver


def load_config(path):
    value = json.loads(Path(path).read_text())
    if (value.get('mode') != 'SOFTWARE_SHADOW'
            or value.get('physical_actuation_enabled') is not False
            or value.get('direction_verified') is not False
            or value.get('reference_is_mechanical') is not False
            or value.get('mechanical_calibration_verified') is not False
            or value.get('shadow_reference_us') != 1425
            or value.get('polarity_assumption') != 'UNVERIFIED_CAMERA_TO_PULSE_DIRECTION'
            or value.get('camera_mounting_assumption') != 'axis'):
        raise ValueError('Invalid shadow-only configuration')
    fields = {field.name for field in dataclasses.fields(FollowConfig)}
    if set(value.get('controller', {})) != fields:
        raise ValueError('Explicit controller parameters required')
    control = FollowConfig(**value['controller'])
    if (control.max_offset_us > 20 or control.pulse_min_us != 1425
            or control.pulse_max_us != 1445):
        raise ValueError('Suggestions exceed the observed 1425..1445us envelope')
    return control


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--duration', type=float, default=10.)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if (os.uname().machine != 'aarch64' or not 0 < args.duration <= 10
            or not args.app_root.is_dir()):
        parser.error('Live KV260 shadow requires an AArch64 app root and 0<duration<=10')
    sys.path.insert(0, str(args.app_root.resolve()))
    from common.motion_observation import PATH

    config = load_config(args.config)
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    controller = PanFollowController(ShadowDriver(), boot, reference_us=1425,
                                     polarity=-1, camera_moves_with_axis=True,
                                     config=config, physical=False)
    counts = {}
    seen = set()
    ages, positions = [], []
    began = time.monotonic()
    error = None
    output = args.output.resolve()
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output.parent, 0o700)
    fd = os.open(str(output), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            while time.monotonic() - began < args.duration:
                connection = http.client.HTTPConnection('127.0.0.1', 8790, timeout=.2)
                try:
                    connection.request('GET', PATH)
                    response = connection.getresponse()
                    raw = response.read(8193)
                    if response.status != 200 or len(raw) > 8192:
                        raise RuntimeError('Motion observation feed unavailable or oversized')
                    packet = json.loads(raw)
                finally:
                    connection.close()
                now_ms = int(time.monotonic() * 1000)
                status = controller.observe(packet, now_ms)
                state = packet.get('state', 'INVALID')
                counts[state] = counts.get(state, 0) + 1
                fid = packet.get('source_frame_id')
                epoch = packet.get('camera_epoch')
                if state == 'READY' and type(fid) is int and isinstance(epoch, str):
                    seen.add((epoch, fid))
                    stamp = packet.get('source_mono_ms')
                    if type(stamp) is int:
                        ages.append(now_ms - stamp)
                    target = packet.get('target')
                    box = target.get('box') if isinstance(target, dict) else None
                    width = packet.get('frame_width')
                    if isinstance(box, list) and len(box) == 4 and type(width) is int and width > 0:
                        positions.append(round((box[0] + box[2] / 2) / width * 2 - 1, 5))
                status.pop('target', None)
                stream.write(json.dumps(status, separators=(',', ':')) + '\n')
                stream.flush()
                if controller.stopped:
                    break
                time.sleep(.02)
    except Exception as exc:
        error = type(exc).__name__
    finally:
        if not controller.stopped:
            controller.stop('INPUT_ERROR' if error else 'TIME_LIMIT')
    elapsed = time.monotonic() - began
    driver = controller.driver
    pulses = [item[0] for item in driver.submissions]
    result = {
        'status': 'ERROR' if error else 'SHADOW_EVALUATION_FINISHED',
        'error_type': error,
        'elapsed_s': round(elapsed, 3),
        'physical_actuation': False,
        'driver': type(driver).__name__,
        'register_writes': 0,
        'rows': sum(counts.values()),
        'state_counts': counts,
        'distinct_ready_sources': len(seen),
        'source_age_ms_max': max(ages) if ages else None,
        'source_age_ms_p50': statistics.median(ages) if ages else None,
        'normalized_target_x_min': min(positions) if positions else None,
        'normalized_target_x_max': max(positions) if positions else None,
        'suggestion_count': len(pulses),
        'suggestion_min_us': min(pulses) if pulses else None,
        'suggestion_max_us': max(pulses) if pulses else None,
        'suggestion_limits_us': [controller.low, controller.high],
        'direction_verified': False,
        'reference_is_mechanical': False,
        'mechanical_angle_measured': False,
        'final_reason': controller.reason,
        'final_state': controller.status()['state'],
    }
    summary = output.with_name(output.name + '.summary.json')
    summary_fd = os.open(str(summary), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(summary_fd, 'w') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
    return 1 if error else 0


if __name__ == '__main__':
    raise SystemExit(main())
