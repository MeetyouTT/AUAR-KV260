"""Isolate trajectory quantization and PWM frame wait; no device access."""
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'continuous_v11_recenter_candidate'))
from continuous_face_control import EdgeConfig
from trajectory import Trajectory


if __name__ == '__main__':
    library = ROOT / 'ps_trajectory_v1/libaura_trajectory_compat_host.so'
    trajectory = Trajectory(library, hashlib.sha256(library.read_bytes()).hexdigest())
    config = EdgeConfig(maximum_speed_us_s=30., maximum_acceleration_us_s2=120.,
                        maximum_jerk_us_s3=800.)
    pva = [1420., 0., 0.]
    first = {}
    # Intentionally ideal: no camera, transport, confirmation, ARM or Linux
    # scheduling delay. Even a 1ms planner retains the same physical units.
    for elapsed_ms in range(1, 1001):
        pva = trajectory.step(pva, 30., .001, config)
        for delta in (1, 3):
            if delta not in first and round(pva[0]) - 1420 >= delta:
                first[delta] = elapsed_ms
    assert 1 in first and 3 in first
    print(json.dumps(dict(
        scope='ideal software trajectory and arithmetic only; not servo start latency',
        planner_tick_ms=1, reference_us=1420, target_velocity_us_s=30,
        maximum_acceleration_us_s2=120, maximum_jerk_us_s3=800,
        first_integer_target_change_ms=first[1],
        first_three_us_target_change_ms=first[3],
        frame_candidates=[dict(frequency_hz=hz, period_ms=1000/hz,
                               frame_step_limit_us=step,
                               hardware_slew_cap_us_s=step*hz,
                               additional_frame_start_wait_ms=[0, 1000/hz])
                          for hz, step in ((50, 4), (100, 2), (200, 1))],
        frame_wait_excludes_pulse_decoding_and_mechanical_response=True,
        source_freshness_constraints_unchanged=True,
        original_range_us=[1400, 1600],
        production_changed=False, motor_commands_sent=0), indent=2))
