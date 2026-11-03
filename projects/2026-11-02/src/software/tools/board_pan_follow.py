"""Evaluate pan commands from the motion feed or recorded packets; NO PWM IO."""
import argparse
import dataclasses
import http.client
import json
import os
from pathlib import Path
import sys
import time

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))
from board.motion.follow import FollowConfig, PanFollowController, ShadowDriver
from common.motion_observation import PATH


def load_config(path):
    config = json.loads(Path(path).read_text())
    if (config.get('mode') != 'SOFTWARE_SHADOW' or config.get('physical_actuation_enabled') is not False
            or config.get('camera_mounting_assumption') != 'axis'):
        raise ValueError('This entry supports axis-camera SHADOW only; no physical ARM or default fixed-camera mapping')
    fields = {field.name for field in dataclasses.fields(FollowConfig)}
    if set(config.get('controller', {})) != fields:
        raise ValueError('Explicit controller parameters required')
    return config, FollowConfig(**config['controller'])


def packets(args):
    if args.replay:
        with args.replay.open() as stream:
            for line in stream:
                if len(line) > 32768:
                    raise ValueError('Replay row exceeds bound')
                if line.strip():
                    value = json.loads(line)
                    yield value['observation'], value['received_mono_ms']
        return
    if os.uname().machine != 'aarch64':
        raise RuntimeError('Live mode must run on KV260, in the source clock domain')
    until = time.monotonic()+args.duration
    while time.monotonic() < until:
        connection = http.client.HTTPConnection('127.0.0.1', 8790, timeout=.15)
        try:
            connection.request('GET', PATH)
            response = connection.getresponse()
            raw = response.read(8193)
            if response.status != 200 or len(raw) > 8192:
                raise RuntimeError('Motion feed not ready; start the camera with board_camera_motion.py')
            yield json.loads(raw), int(time.monotonic()*1000)
        finally:
            connection.close()
        time.sleep(.02)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=AURA/'config/pan_follow.shadow.json')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--live', action='store_true')
    source.add_argument('--replay', type=Path)
    parser.add_argument('--duration', type=float, default=10.)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--boot-id', help='Required for replay; live always reads the actual boot')
    args = parser.parse_args()
    if not 0 < args.duration <= 120 or args.live and args.boot_id or args.replay and not args.boot_id:
        parser.error('Use 0<duration<=120; --boot-id is only required for replay')
    config, control_config = load_config(args.config)
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip() if args.live else args.boot_id
    driver = ShadowDriver()
    controller = PanFollowController(driver, boot, reference_us=config['shadow_reference_us'],
                                     polarity=config['polarity'], config=control_config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = new_sources = 0
    seen = set()
    error = None
    try:
        with args.output.open('x') as stream:
            for packet, now in packets(args):
                status = controller.observe(packet, now, allow_fixture=bool(args.replay))
                identity = (packet.get('camera_epoch'), packet.get('source_frame_id'))
                if identity not in seen:
                    new_sources += 1;seen.add(identity)
                stream.write(json.dumps({'received_mono_ms': now, 'observation': packet, 'control': status})+'\n')
                stream.flush();rows += 1
                if controller.stopped:
                    break
    except Exception as exc:
        error = type(exc).__name__+': '+str(exc)
    finally:
        if not controller.stopped:
            controller.stop('INPUT_ERROR' if error else 'REPLAY_ENDED' if args.replay else 'TIME_LIMIT')
    result = {'status': 'ERROR' if error else 'SHADOW_EVALUATION_FINISHED', 'error': error,
              'physical_actuation': False, 'mechanical_calibration_verified': False,
              'camera_mounting_is_assumed': True, 'rows': rows, 'distinct_sources': new_sources,
              'final': controller.status()}
    summary = args.output.with_name(args.output.name+'.summary.json')
    with summary.open('x') as stream:
        stream.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return 1 if error else 0


if __name__ == '__main__':
    raise SystemExit(main())
