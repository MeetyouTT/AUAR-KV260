"""Compare face-source cadence using the existing controller and fake PWM.

Each synthetic image carries its actual capture time. This never opens a
camera, UART, MMIO or production process. Fixed 20ms trajectory ticks stay
unchanged so the comparison isolates the observation cadence.
"""
from collections import Counter
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'continuous_v11_recenter_candidate'))
from test_recenter import Scene


def compare(rate_hz, source_age_ms):
    scene = Scene(reference=1460)
    started = scene.now
    next_frame_ms = 0.
    first_change_ms = None
    events = Counter()
    last_events = 0
    # Stay outside the right trigger, then return to the original zone while
    # retaining the recenter goal. No injected detector loss or target change.
    for elapsed_ms in range(0, 4001, 20):
        scene.now = started + elapsed_ms / 1000.
        if elapsed_ms + .001 >= next_frame_ms:
            center = .86 if elapsed_ms < 1000 else .72
            packet = scene.packet(center)
            stamp = round(scene.now * 1000) - source_age_ms
            packet.update(source_mono_ms=stamp, deadline_mono_ms=stamp + 250,
                          face_detection_mono_ms=stamp)
            scene.session.step(packet)
            next_frame_ms += 1000. / rate_hz
        scene.session.tick()
        if scene.session.motion_updates and first_change_ms is None:
            first_change_ms = elapsed_ms
        current_events = list(scene.session.events)
        for event in current_events[last_events:]:
            events[event['reason']] += 1
        last_events = len(current_events)
        assert not scene.session.fatal, scene.session.reason
        assert 1400 <= scene.device.pulse <= 1600
    result = dict(face_source_hz=rate_hz, source_age_ms=source_age_ms,
                  trajectory_tick_ms=20, synthetic_duration_ms=4000,
                  first_changed_target_ms=first_change_ms,
                  motion_target_changes=scene.session.motion_updates,
                  arms=scene.device.arms, events=dict(events),
                  initial_target_us=1460, final_target_us=scene.device.pulse,
                  fatal=scene.session.fatal)
    scene.session.close()
    return result


if __name__ == '__main__':
    print(json.dumps(dict(
        scope='synthetic software comparison; not mechanical smoothness or real face accuracy',
        camera_opened=False, uart_opened=False, motor_commands_sent=0,
        production_changed=False,
        assumptions=dict(source_age_ms=[55, 90], source_ttl_ms=250,
                         detection_anchor_refreshed_every_frame=True,
                         missing_faces_injected=False),
        rows=[compare(rate, age) for age in (55, 90)
              for rate in (12.5, 10., 8., 5.)]), ensure_ascii=False, indent=2))
