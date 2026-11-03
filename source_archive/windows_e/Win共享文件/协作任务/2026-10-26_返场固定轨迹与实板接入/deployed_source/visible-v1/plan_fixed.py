"""Offline 5-second visible bench plan, same pinned Ruckig math and limits."""
import ctypes
import hashlib
import json
import math
from pathlib import Path

WORK = Path(__file__).resolve().parent.parent
LIBRARY = WORK / 'ps_trajectory_v1/libaura_trajectory_compat_host.so'
LIBRARY_SHA256 = 'cd8e8359413d621803cea7bab2fb133bd77657c7ac99c6191976f0d5c7e293b4'
LIMITS = dict(speed_us_s=20., acceleration_us_s2=100., jerk_us_s3=800.)
TICK_S = .02


def solver():
    if hashlib.sha256(LIBRARY.read_bytes()).hexdigest() != LIBRARY_SHA256:
        raise ValueError('Host trajectory library changed')
    lib = ctypes.CDLL(str(LIBRARY))
    f = lib.aura_trajectory_step
    f.argtypes = [ctypes.c_double, ctypes.POINTER(ctypes.c_double), ctypes.c_double,
                  ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.POINTER(ctypes.c_double)]
    f.restype = ctypes.c_int
    def step(state, desired):
        before, after = (ctypes.c_double * 3)(*state), (ctypes.c_double * 3)()
        code = f(TICK_S, before, desired, LIMITS['speed_us_s'], LIMITS['acceleration_us_s2'], LIMITS['jerk_us_s3'], after)
        if code or not all(math.isfinite(v) for v in after):
            raise RuntimeError('Pure trajectory solver failed: %d' % code)
        return list(after)
    return step


def make_plan(reference_us, direction=-1):
    if type(reference_us) is not int or type(direction) is not int or direction not in (-1, 1):
        raise ValueError('Explicit integer reference and direction required')
    if not all(1400 <= v <= 1600 for v in (reference_us, reference_us + direction * 15)):
        raise ValueError('Entire illustrative path must fit the existing PL range')
    step, state = solver(), [float(reference_us), 0., 0.]
    rows = [dict(time_ms=0, position_us=state[0], velocity_us_s=0., acceleration_us_s2=0.,
                 desired_velocity_us_s=0., target_us=reference_us)]
    for desired, count in ((direction * 10., 75), (0., 50), (-direction * 10., 75), (0., 50)):
        for _ in range(count):
            state = step(state, desired)
            rows.append(dict(time_ms=len(rows) * 20, position_us=state[0], velocity_us_s=state[1],
                             acceleration_us_s2=state[2], desired_velocity_us_s=desired, target_us=round(state[0])))
    if abs(rows[125]['position_us'] - reference_us - direction * 15) > 1e-7:
        raise RuntimeError('Outbound endpoint is not 15us from reference')
    if abs(state[0] - reference_us) > 1e-7 or abs(state[1]) > 1e-7 or abs(state[2]) > 1e-7:
        raise RuntimeError('Final endpoint is not the reference at rest')
    return rows


def report():
    rows = make_plan(1420, -1)
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return dict(schema='aura-fixed-visible-plan-1', status='OFFLINE_FROZEN_PLAN_NOT_BOARD_MOTION',
                example_reference_us=1420, mechanical_position_confirmed=False, direction_in_pulse_space=-1,
                duration_ms=5000, tick_ms=20, sample_count=251, planned_submissions=248, finish_reserve_ms=40,
                maximum_excursion_us=15, approved_window_us=[1402, 1420], target_range_us=[1405, 1420],
                desired_velocity_sequence=[[-10, 1.5], [0, 1.0], [10, 1.5], [0, 1.0]],
                continuous_limits=LIMITS, first_pwm_minimum_lease_ms=23, maximum_lease_ms=100, margin_ms=20,
                host_library_sha256=LIBRARY_SHA256, plan_sha256=digest, samples=rows,
                board_accessed=False, physical_motion_verified=False, hardware_absolute_deadline_guaranteed=False)


if __name__ == '__main__':
    print(json.dumps(report(), indent=2))
