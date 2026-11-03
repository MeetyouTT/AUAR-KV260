"""Offline numeric alignment only: capture timestamps, not JPEG download times."""
import bisect
import hashlib
import json
import math
from pathlib import Path
import statistics

SOURCE = Path('/home/ghmd/aura-pan-board-20261024/uart/20261027T061523.591320Z-da36-region-repeat-motion-observed/response.json')


def analyze():
    data = json.loads(SOURCE.read_text())
    control, preview = data['result'], data['preview_motion']
    start = control['started_mono_s']
    commands = control['commands']
    times = [c['acknowledgement']['observed_mono_s'] for c in commands]
    assert times == sorted(times) and control['stopped_readback']['flags'] == 0
    rows = []
    for sample in preview['samples']:
        stamp = sample['captured_mono_ms'] / 1000.
        assert sample['board_boot_id'] == control['boot_id']
        index = bisect.bisect_right(times, stamp) - 1
        row = dict(frame_id=sample['frame_id'], captured_mono_ms=sample['captured_mono_ms'],
                   capture_relative_s=stamp-start, sample_relative_s=sample['sample_mono_s']-start,
                   cache_and_fetch_age_ms=(sample['sample_mono_s']-stamp)*1000.,
                   state=sample['state'], dx_px=sample.get('dx_px'), dy_px=sample.get('dy_px'),
                   inliers=sample.get('inliers'), inlier_ratio=sample.get('inlier_ratio'),
                   median_residual_px320=sample.get('median_flow_residual_px320'))
        if index >= 0:
            c = commands[index];rb = c['acknowledgement']['readback']
            row.update(last_ack_before_capture=dict(target_us=rb['target_us'], width_us=rb['width_us'],
                       ack_seq=rb['ack_seq'], age_ms=(stamp-times[index])*1000.))
        if index+1 < len(commands):
            c = commands[index+1];rb = c['acknowledgement']['readback']
            row.update(next_ack_after_capture=dict(target_us=rb['target_us'], width_us=rb['width_us'],
                       ack_seq=rb['ack_seq'], after_capture_ms=(times[index+1]-stamp)*1000.))
        rows.append(row)
    measured = [r for r in rows if r['state'] == 'MEASURED_BACKGROUND_SHIFT']
    before = [r for r in measured if r['capture_relative_s'] < 0]
    initial_step = next(c['submitted_mono_s']-start for c in commands if c['target_us'] != 1420)
    first_width_change = next(c['acknowledgement']['observed_mono_s']-start for c in commands
                              if c['acknowledgement']['readback']['width_us'] != 1420)
    first_return = next(c['submitted_mono_s']-start for c in commands if c['submitted_mono_s']-start > 2.5 and c['target_us'] > 1405)
    plateau = statistics.median(r['dx_px'] for r in measured if 1.85 <= r['capture_relative_s'] <= 2.3)
    def bracket(test, after):
        selected = [r for r in measured if r['capture_relative_s'] >= after]
        for previous, current in zip(selected, selected[1:]):
            if test(current): return [previous['capture_relative_s'], current['capture_relative_s']]
        return None
    outbound = bracket(lambda r: r['dx_px'] > 1., 0.)
    returned = bracket(lambda r: r['dx_px'] < plateau-1., 2.5)
    secant = max(r['dx_px'] for r in measured) / 15.
    age = [r['cache_and_fetch_age_ms'] for r in rows]
    gap = [(b['captured_mono_ms']-a['captured_mono_ms'])/1000. for a,b in zip(rows,rows[1:])]
    u = 10/640/.04;envelope = u*u*(3-2*u)
    return dict(scope='OFFLINE_NUMERIC_CAPTURE_TIME_ANALYSIS_NOT_SHAFT_ANGLE_MEASUREMENT',
      source_path=str(SOURCE), source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
      control=dict(accepted=len(commands), elapsed_s=control['completed_mono_s']-start,
                   final_stop=control['stopped_readback']),
      preview=dict(measured_frames=len(measured), baseline_corners=preview['baseline']['corners'],
                   minimum_inliers=min(r['inliers'] for r in measured), minimum_inlier_ratio=min(r['inlier_ratio'] for r in measured),
                   maximum_abs_dx_px=preview['maximum_abs_dx_px'], maximum_abs_dy_px=preview['maximum_abs_dy_px'],
                   precontrol_maximum_abs_dx_px=max(abs(r['dx_px']) for r in before),
                   cache_and_fetch_age_ms=dict(minimum=min(age),median=statistics.median(age),maximum=max(age)),
                   capture_interval_s=dict(minimum=min(gap),median=statistics.median(gap),maximum=max(gap))),
      timing=dict(first_changed_target_submit_s=initial_step,first_observed_changed_pwm_width_s=first_width_change,
                  outbound_more_than_1px_capture_bracket_s=outbound,
                  outbound_1px_threshold_minus_first_submit_s=[v-initial_step for v in outbound],
                  first_return_target_submit_s=first_return,return_more_than_1px_capture_bracket_s=returned,
                  return_1px_threshold_minus_first_return_submit_s=[v-first_return for v in returned],
                  caveat='1px is an explicit visibility threshold; these are sampled crossing brackets, not pure transport or mechanical delay estimates'),
      response=dict(held_outbound_plateau_dx_px=plateau,secant_px_per_us=secant,secant_is_linear_calibration=False,
                    same_pwm_1409_examples=[r for r in measured if r.get('last_ack_before_capture',{}).get('width_us')==1409],
                    final_sample_dx_px=measured[-1]['dx_px'],camera_mechanical_deadband_identified=False),
      r15_units=dict(position_error='fraction of 640px image width',face_velocity='fraction of image width per second from OneEuro derivative',
                     proportional_gain_us_s_per_px=160/640,velocity_gain_us_per_px=12/640,
                     face_speed_clip_px_s=640,velocity_envelope_full_distance_px=.04*640,
                     extra_command_at_100px_s_full_envelope_us_s=12*100/640,
                     command_for_10px_error_and_100px_s_outward_face_us_s=max(6,min(20,160*10/640+12*100/640*envelope)),
                     maximum_speed_us_s=20,edge_floor_us_s=6,acceleration_us_s2=100,jerk_us_s3=800),
      order_of_magnitude_only=dict(image_speed_at_6us_s_px_s=6*secant,image_speed_at_20us_s_px_s=20*secant,
                     image_shift_for_downward_20us_budget_px=20*secant,
                     warning='Extrapolates a nonlinear one-trial secant; not an accepted gain or a calibrated travel measurement'),
      kinematics=dict(rest_to_20us_s_minimum_s=20/100+100/800,
                      rest_to_10us_s_minimum_s=2*math.sqrt(10/800),
                      rest_to_half_us_lower_bound_ms=155.762622,
                      scope='Ideal continuous trajectory, excludes source confirmation, quantization tick, PWM latch, servo nonlinearity'),
      aligned_samples=rows)


if __name__ == '__main__':
    print(json.dumps(analyze(), indent=2))
