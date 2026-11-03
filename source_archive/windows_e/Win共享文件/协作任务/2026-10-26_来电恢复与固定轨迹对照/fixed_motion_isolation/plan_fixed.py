"""Offline numerical plan only. No camera, source packets, device or execution API."""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
from statistics import median

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
        before = (ctypes.c_double * 3)(*state)
        after = (ctypes.c_double * 3)()
        rc = f(TICK_S, before, desired, LIMITS['speed_us_s'],
               LIMITS['acceleration_us_s2'], LIMITS['jerk_us_s3'], after)
        if rc or not all(math.isfinite(v) for v in after):
            raise RuntimeError('Pure trajectory solver failed: %d' % rc)
        return list(after)
    return step


def make_plan(reference_us, direction=1):
    """Example reference is a calculation input, never a measured/current angle."""
    if type(reference_us) is not int or type(direction) is not int or direction not in (-1, 1):
        raise ValueError('Integer example reference and direction +/-1 required')
    if not all(1400 <= p <= 1600 for p in (reference_us, reference_us + direction * 5)):
        raise ValueError('Entire illustrative path must fit the existing PL range')
    step = solver()
    state = [float(reference_us), 0., 0.]
    rows = [dict(time_ms=0, position_us=state[0], velocity_us_s=0., acceleration_us_s2=0.,
                 desired_velocity_us_s=0., target_us=reference_us)]
    # Velocity mode: symmetric acceleration/deceleration displacements cancel
    # around a 0.5-second velocity command. Each complete leg travels exactly
    # 10 * 0.5 = 5us; the extra 0.5s permits a complete stop before reversal.
    for desired in (direction * 10., 0., -direction * 10., 0.):
        for _ in range(25):
            state = step(state, desired)
            rows.append(dict(time_ms=len(rows) * 20, position_us=state[0], velocity_us_s=state[1],
                             acceleration_us_s2=state[2], desired_velocity_us_s=desired,
                             target_us=round(state[0])))
    if abs(rows[50]['position_us'] - reference_us - direction * 5) > 1e-7:
        raise RuntimeError('First leg did not finish at the specified endpoint')
    if abs(state[0] - reference_us) > 1e-7 or abs(state[1]) > 1e-7 or abs(state[2]) > 1e-7:
        raise RuntimeError('Round trip did not finish at rest at its calculation reference')
    return rows


def metrics(rows):
    initial = rows[0]['target_us']
    changes = [b for a, b in zip(rows, rows[1:]) if a['target_us'] != b['target_us']]
    gaps = [b['time_ms'] - a['time_ms'] for a, b in zip(changes, changes[1:])]
    return dict(duration_ms=rows[-1]['time_ms'], samples=len(rows),
                target_changes=len(changes), first_changed_target_ms=changes[0]['time_ms'] if changes else None,
                target_range_us=[min(r['target_us'] for r in rows), max(r['target_us'] for r in rows)],
                maximum_target_step_us=max(abs(b['target_us'] - a['target_us']) for a, b in zip(rows, rows[1:])),
                target_change_interval_ms=dict(minimum=min(gaps), median=median(gaps), maximum=max(gaps)) if gaps else None,
                maximum_sampled_solver_speed_us_s=max(abs(r['velocity_us_s']) for r in rows),
                maximum_sampled_solver_acceleration_us_s2=max(abs(r['acceleration_us_s2']) for r in rows),
                analytic_triangular_ramp_peak_acceleration_us_s2=math.sqrt(10. * LIMITS['jerk_us_s3']),
                maximum_sampled_acceleration_change_per_second=max(
                    abs(b['acceleration_us_s2'] - a['acceleration_us_s2']) / TICK_S
                    for a, b in zip(rows, rows[1:])),
                first_outbound_quantized_displacements_ms={
                    str(d): next(r['time_ms'] for r in rows[:51] if abs(r['target_us'] - initial) >= d)
                    for d in (1, 2, 3, 4, 5)},
                final_target_us=rows[-1]['target_us'], continuous_endpoint_velocity_us_s=rows[-1]['velocity_us_s'],
                continuous_endpoint_acceleration_us_s2=rows[-1]['acceleration_us_s2'])


def report(reference_us):
    source = WORK / 'r14_timeline_audit_20261026/FIRST_SUBMIT_DELAYS.json'
    historical = json.loads(source.read_text())
    bench = Path('/home/ghmd/aura-pan-joint-20261023/bench_finite_step.py')
    cases = []
    for direction in (1, -1):
        rows = make_plan(reference_us, direction)
        cases.append(dict(direction_in_pulse_space=direction, metrics=metrics(rows), samples=rows))
    return dict(status='OFFLINE_FIXED_TRAJECTORY_PLAN_ONLY', board_accessed=False, executable_motion=False,
                mechanical_position_confirmed=False, example_reference_us=reference_us,
                reference_1420_is_user_historical_reference=True, old_last_width_1426_is_not_current_position=True,
                duration_each_roundtrip_ms=2000, maximum_excursion_us=5, tick_ms=20,
                continuous_limits=LIMITS, fixed_plan_desired_speed_us_s=10.,
                visual_contract_unchanged=dict(image_ttl_ms=250, anchor_ttl_ms=500, submission_margin_ms=20,
                                              maximum_displacement_per_admitted_source_us=4),
                fixed_plan_is_not_face_observation=True, generated_face_packets=0,
                actual_motion_requires_new_boot_reference_and_attended_bounded_executor=True,
                historical_manual_window_us=[1402, 1420],
                positive_5us_plan_at_1420_exceeds_historical_manual_window=True,
                dependencies=dict(host_library=str(LIBRARY), host_library_sha256=LIBRARY_SHA256,
                                  existing_finite_bench=str(bench), existing_finite_bench_sha256=hashlib.sha256(bench.read_bytes()).hexdigest(),
                                  historical_metrics_sha256=hashlib.sha256(source.read_bytes()).hexdigest()),
                existing_bench_review=dict(actual_schedule='hold initial 1s, jump by <=5us, hold target 1s',
                                           update_interval_ms=40, lease_ms=100, smooth_path=False,
                                           reusable='context/owner/finite duration/ACK/QUIESCE/STOP structure only',
                                           directly_equivalent_to_fixed_plan=False),
                historical_visual_evidence=dict(accepted=historical['reconstructed_command_coverage']['accepted_total'],
                                                retained=historical['reconstructed_command_coverage']['retained'],
                                                first_submission_delay_ms=historical['arm_to_submit_lower_bound_ms'],
                                                matched_fixed_motion_comparison=False,
                                                reason='Historical 1402..1449us run, incomplete commands, different path and conditions; no physical onset measurement'),
                interpretation='Continuous p/v/a is smooth; integer-us targets still form steps. This is neither measured PWM nor measured servo motion.',
                cases=cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--example-reference-us', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = report(args.example_reference_us)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(dict(status=result['status'], output=str(args.output),
                          metrics=[c['metrics'] for c in result['cases']], board_accessed=False)))


if __name__ == '__main__':
    main()
