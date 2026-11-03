"""Same source samples: actual v5 perception output versus one One Euro filter."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT))
from one_euro import OneEuroFilter
from common.motion_observation import PROTOCOL

BASELINE = PROJECT/'continuous_v5/continuous_face_control.py'
spec = importlib.util.spec_from_file_location('v5_ab_control', BASELINE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def scenario(name, seed=13):
    rng = random.Random(seed)
    times = [0.]
    duration = 10. if name == 'stationary_noise' else 6.
    intervals = [.055, .080, .120, .065, .080]
    while times[-1] < duration:
        times.append(round(times[-1]+intervals[(len(times)-1) % len(intervals)], 6))
    rows = []
    spike_inserted = False
    for time in times:
        if name == 'slow_ramp':
            truth = .5+.025*max(0., time-1.)
        elif name == 'fast_ramp':
            truth = .3+.5*min(1., max(0., time-1.))
        elif name == 'direction_reversal':
            truth = (.3+.4*min(1., max(0., time-1.))
                     -.4*min(1., max(0., time-3.)))
        else:
            truth = .5
        measured = truth+(rng.gauss(0., .002) if name == 'stationary_noise' else 0.)
        if name == 'single_spike' and time >= 2. and not spike_inserted:
            measured += .25
            spike_inserted = True
        rows.append((time, truth, measured))
    return rows


def replay(rows):
    baseline = module.FaceEdgeController('math-only-fixture', 1500)
    candidate = OneEuroFilter()
    result = []
    for index, (time, truth, measured) in enumerate(rows, 1):
        stamp = 1000+round(time*1000)
        packet = dict(protocol_version=PROTOCOL, source_kind='fixture', target_kind='face',
            board_boot_id='math-only-fixture', service_epoch='service', camera_epoch='camera',
            state='READY', source_frame_id=index, source_mono_ms=stamp, deadline_mono_ms=stamp+250,
            frame_width=640, frame_height=480, mirror_horizontal=True,
            target=dict(track_id=1, track_generation=1,
                        box=[measured*640-40., 100., 80., 80.], score=.95))
        old = baseline.observe(packet, stamp, allow_fixture=True)['filtered_center_ratio']
        assert not baseline.stopped, baseline.reason
        new = candidate(measured, stamp/1000.)
        result.append(dict(time_s=stamp/1000.-1., truth_ratio=truth, measured_ratio=measured,
                           v5_ratio=old, one_euro_ratio=new,
                           one_euro_cutoff_hz=candidate.cutoff_hz,
                           derivative_ratio_s=candidate.derivative_ratio_s))
    return result


def metrics(name, rows):
    selected = [r for r in rows if r['time_s'] >= 1.]
    result = {}
    for key in ('measured_ratio', 'v5_ratio', 'one_euro_ratio'):
        errors = [r[key]-r['truth_ratio'] for r in selected]
        current = dict(rmse_ratio=math.sqrt(statistics.mean(e*e for e in errors)),
                       maximum_error_ratio=max(abs(e) for e in errors),
                       error_std_px=statistics.pstdev(errors)*640)
        if name in ('slow_ramp', 'fast_ramp'):
            ramp = [r for r in rows if (1.5 if name == 'slow_ramp' else 1.4) <= r['time_s'] <= (5.5 if name == 'slow_ramp' else 1.96)]
            velocity = .025 if name == 'slow_ramp' else .5
            current['mean_ramp_lag_ms'] = statistics.mean((r['truth_ratio']-r[key])/velocity*1000 for r in ramp)
        result[key] = current
    return result


report = dict(scope='pure math synthetic replay; no camera, hardware, identity or service access',
    baseline=dict(source=str(BASELINE), sha256=hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
                  actual_class='FaceEdgeController', compared_field='filtered_center_ratio',
                  median_window=3, position_tau_ms=80.,
                  current_session_fact='v5 zone_holding preserves ARM for normal in-zone holds; no v2r2 lifecycle assumption'),
    candidate=dict(source='one_euro.py', parameters=dict(min_cutoff_hz=1., beta=6., derivative_cutoff_hz=1.),
                   units='image-width ratio, actual source seconds', extra_position_median_or_ema=False),
    source_intervals_ms=[55, 80, 120, 65, 80], scenarios={})
for name in ('stationary_noise', 'slow_ramp', 'fast_ramp', 'direction_reversal', 'single_spike'):
    rows = replay(scenario(name))
    report['scenarios'][name] = dict(metrics=metrics(name, rows), rows=rows)
report['interpretation'] = ['Position filtering comparison only; does not prove PWM/axis smoothness.',
    'One Euro is not an outlier rejector; high-speed adaptation can pass a single bad jump.',
    'Do not stack this candidate after the existing median and fixed position EMA.',
    'Normalized-ratio beta must not be copied as a pixel-domain beta.']
(ROOT/'AB.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({name: value['metrics'] for name, value in report['scenarios'].items()}, indent=2))
