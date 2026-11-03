"""Offline diagnosis of the frozen continuous-v2r2 controller; no hardware IO."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

SOURCE = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-24_pan_follow_shadow/source')
sys.dont_write_bytecode = True
sys.path[:0] = [str(SOURCE / 'continuous_v2r2'), str(SOURCE)]
from continuous_face_control import EdgeConfig
from continuous_session import ContinuousSession
from common.motion_observation import PROTOCOL
from test_continuous_session import Device


def run(name, centers, period_ms, initial_us):
    now = [1.0]
    device = Device(lambda: now[0])
    device.pulse = initial_us
    session = ContinuousSession(device, 'offline-boot', EdgeConfig(),
        lambda pulse: SimpleNamespace(reference_us=pulse), clock=lambda: now[0], allow_fixture=True)
    rows = []
    first_outside = first_changed = None
    previous = initial_us
    changes = []
    for fid, center in enumerate(centers, 1):
        stamp = 1000 + fid * period_ms
        now[0] = (stamp + 20) / 1000
        packet = dict(protocol_version=PROTOCOL, source_kind='fixture', target_kind='face',
            board_boot_id='offline-boot', service_epoch='service', camera_epoch='camera',
            state='READY', source_frame_id=fid, source_mono_ms=stamp, deadline_mono_ms=stamp+250,
            frame_width=640, frame_height=480, mirror_horizontal=True,
            target=dict(track_id=1, track_generation=1, box=[center*640-40, 100., 80., 80.], score=.95))
        status = session.step(packet)
        if first_outside is None and center > EdgeConfig().right_ratio:
            first_outside = stamp
        if device.pulse != previous:
            if first_changed is None:
                first_changed = stamp
            changes.append(dict(source_ms=stamp, delta_us=device.pulse-previous))
        previous = device.pulse
        rows.append(dict(source_ms=stamp, center_ratio=center, state=status['state'],
            reason=status['reason'], commanded_us=device.pulse, arms=device.arms,
            finishes=device.finishes, acks=len(device.acks),
            velocity_us_s=status['control']['velocity_us_s']))
    return dict(scenario=name, period_ms=period_ms, initial_us=initial_us, frames=len(rows),
        arm_count=device.arms, finish_count=device.finishes, ack_count=len(device.acks),
        commanded_travel_us=device.pulse-initial_us,
        crossing_to_first_changed_command_ms=None if first_changed is None else first_changed-first_outside,
        changes=changes, rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initial-us', type=int, default=1445)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    edge = EdgeConfig().right_ratio
    scenarios = []
    for period in (40, 100):
        scenarios.extend([
            run('alternating_1p28px_across_boundary', [.78]*6 + [edge+.002, edge-.002]*20, period, args.initial_us),
            run('five_outside_one_inside_repeated', [.78]*6 + ([edge+.002]*5+[edge-.002])*10, period, args.initial_us),
            run('continuous_outward_after_inside_warmup', [.78]*6 + [edge+.001+.002*i for i in range(18)], period, args.initial_us),
            run('cold_start_stationary_outside', [.85]*18, period, args.initial_us),
        ])
    result = dict(kind='OFFLINE_SYNTHETIC_CURRENT_CODE_DIAGNOSIS', hardware_io=False,
        runtime_deployed=False, caveat='FakeDevice has no physical servo or autonomous lease timer. Results are software command behavior, not measured mechanical latency.',
        source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            SOURCE/'continuous_v2r2/continuous_face_control.py',
            SOURCE/'continuous_v2r2/continuous_session.py',
            SOURCE/'continuous_v2r2/test_continuous_session.py', SOURCE/'common/motion_observation.py']},
        results=scenarios)
    out = args.output or Path(__file__).with_name('current_controller_replay_'+str(args.initial_us)+'.json')
    with out.open('x') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(json.dumps([{k:v for k,v in r.items() if k not in ('rows','changes')} for r in scenarios], indent=2))


if __name__ == '__main__':
    main()
