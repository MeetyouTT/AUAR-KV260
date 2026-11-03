"""Local-file workload checks for the paired renderer experiment.

No network, renderer, process, device, or service is opened. PASS means the
recorded workload checks passed at the recorded sampling cadence, not that a
candidate is cheaper or that a production switch is authorized. FAIL/UNKNOWN
retain every original run and only limit the conclusions that may be drawn.

Public API: check_case(case_dir, suite_case_row, scenario), check_suite(...),
and descriptive_jpeg_contribution(suite_case_rows). Scenario may be a JSON path
or an already loaded dict. CLI examples are in --help.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import statistics

NOMINAL_SNAPSHOT_SECONDS = .2
EVENT_GRACE_SECONDS = .5
PAUSE_ENTRY_GUARD_SECONDS = NOMINAL_SNAPSHOT_SECONDS
CANCEL_SETTLE_SECONDS = .5
MIN_STABLE_SAMPLES = 2
# These are equality tolerances for *stored numeric values*. They are not
# response-time precision or a claim to observe between the 200ms snapshots.
NUMERIC_ZERO_TOLERANCE = 1e-6
CLOCK_EQUALITY_TOLERANCE = 1e-6
CAMERA_NOMINAL_SECONDS = 5.
CAMERA_MAX_GAP_SECONDS = 7.
CAMERA_MIN_COVERAGE_FRACTION = .75
EXPECTED_CAPS = dict(format='S16LE', rate=48000, channels=2)
FORMAL_BACKENDS = ['old', 'new', 'new', 'old', 'old', 'new', 'new', 'old',
                   'old_nojpeg', 'new', 'new', 'old_nojpeg']
EXPECTED_SUMMARY_BACKEND = {'old': 'fresh-r3-remote16',
    'old_nojpeg': 'fresh-r3-remote16-nojpeg-control', 'new': 'new-yuki-native16'}


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def _check(status, reason, **evidence):
    return dict(status=status, reason=reason, evidence=evidence)


def _overall(checks):
    statuses = [item['status'] for item in checks.values()]
    return 'FAIL' if 'FAIL' in statuses else 'UNKNOWN' if 'UNKNOWN' in statuses else 'PASS'


def _range(values):
    return dict(min=min(values), max=max(values), span=max(values)-min(values)) if values else None


def _event_kind(event):
    return event.get('args', [None])[0] if event.get('method') == 'event' else event.get('method')


def _scenario(value):
    if isinstance(value, (str, Path)):
        path = Path(value)
        return _read(path), hashlib.sha256(path.read_bytes()).hexdigest()
    return value, None


def _event_time(index, events, commands, start):
    """Use the real enqueue time; fall back to scheduled time with no precision claim."""
    if index < len(commands) and _number(commands[index].get('enqueued_monotonic')) and _number(start):
        return commands[index]['enqueued_monotonic']-start
    return events[index]['at']


def _between(samples, begin, end):
    return [row for row in samples if _number(row.get('elapsed')) and begin <= row['elapsed'] < end]


def _stop_after(events, index, duration):
    return next((event['at'] for event in events[index+1:]
                 if _event_kind(event) in ('submit', 'cancel', 'reset')), duration)


def _camera_checks(os_rows, row, start, end):
    checks = {}
    attempts = [dict(at=item['at'], **item['camera']) for item in os_rows
                if _number(item.get('at')) and start <= item['at'] <= end
                and isinstance(item.get('camera'), dict)]
    from_raw = bool(os_rows)
    if not from_raw:
        # Aggregate camera_samples drops unavailable attempts. It may still
        # support counter observations but cannot prove request availability.
        attempts = row.get('resources', {}).get('camera_samples', [])
    valid = [item for item in attempts if item.get('available') is True
             and isinstance(item.get('numeric'), dict) and _number(item.get('at'))]
    valid.sort(key=lambda item: item['at'])
    missing = [dict(at=item.get('at'), error_type=item.get('error_type'))
               for item in attempts if item.get('available') is not True]
    span = valid[-1]['at']-valid[0]['at'] if len(valid) >= 2 else 0.
    duration = end-start
    gaps = [b['at']-a['at'] for a, b in zip(valid, valid[1:])]
    coverage = span/duration if duration > 0 else None
    edge_gaps = [valid[0]['at']-start, end-valid[-1]['at']] if valid else []
    adequate = (from_raw and not missing and len(valid) >= 2 and duration > 0
                and coverage >= CAMERA_MIN_COVERAGE_FRACTION
                and max(gaps+edge_gaps, default=math.inf) <= CAMERA_MAX_GAP_SECONDS)
    checks['camera_availability_coverage'] = _check('PASS' if adequate else 'UNKNOWN',
        'Camera health coverage is sufficient' if adequate else 'Camera availability/coverage is not fully proved; original run is retained',
        raw_os_samples_available=from_raw, attempted=len(attempts), available=len(valid), unavailable=missing,
        available_span_seconds=span, measured_span_seconds=duration, coverage_fraction=coverage,
        minimum_coverage_fraction=CAMERA_MIN_COVERAGE_FRACTION,
        maximum_adjacent_gap_seconds=max(gaps, default=None), edge_gaps_seconds=edge_gaps,
        allowed_maximum_gap_seconds=CAMERA_MAX_GAP_SECONDS)
    pids = sorted({item['numeric'].get('pid') for item in valid
                   if type(item['numeric'].get('pid')) is int})
    pid_missing = sum(type(item['numeric'].get('pid')) is not int for item in valid)
    status = 'FAIL' if len(pids) > 1 else 'PASS' if len(pids) == 1 and not pid_missing else 'UNKNOWN'
    checks['camera_same_pid'] = _check(status,
        'Camera PID must remain observable and constant; restart prevents a same-workload claim',
        pids=pids, missing_pid_samples=pid_missing)
    errors = [dict(at=item['at'], flags=[key for key, value in item['numeric'].items()
              if key.endswith('_error_present') and value]) for item in valid]
    errors = [item for item in errors if item['flags']]
    flag_keys = ('camera_error_present', 'detector_error_present', 'preview_error_present')
    flags_complete = bool(valid) and all(all(key in item['numeric'] for key in flag_keys) for item in valid)
    checks['camera_error_flags'] = _check('FAIL' if errors else 'PASS' if flags_complete else 'UNKNOWN',
        'Explicit camera/detector/preview health flags; absence is not treated as no error',
        error_samples=errors, complete_flag_coverage=flags_complete)
    counters = {}; resets = []; unavailable_counters = []; flat = []
    for key in ('capture_frames', 'detected_frames', 'preview_frames', 'identity.processed'):
        points = [(item['at'], item['numeric'][key]) for item in valid if _number(item['numeric'].get(key))]
        delta = points[-1][1]-points[0][1] if len(points) >= 2 else None
        elapsed = points[-1][0]-points[0][0] if len(points) >= 2 else None
        negative = [dict(before_at=a[0], after_at=b[0], before=a[1], after=b[1])
                    for a, b in zip(points, points[1:]) if b[1] < a[1]]
        counters[key] = dict(samples=len(points), delta=delta, span_seconds=elapsed,
                             per_second=delta/elapsed if elapsed and elapsed > 0 else None,
                             resets=negative)
        if negative:resets.append(key)
        if key != 'identity.processed':
            if len(points) != len(valid) or len(points) < 2:unavailable_counters.append(key)
            elif delta == 0:flat.append(key)
    status = 'FAIL' if resets else 'UNKNOWN' if unavailable_counters or flat else 'PASS'
    checks['camera_counter_continuity_and_work'] = _check(status,
        'Counter resets prevent a continuity claim; zero increments are UNKNOWN workload evidence, never a rule to delete a run. Identity zero is allowed when idle',
        counters=counters, reset_counters=resets, missing_counters=unavailable_counters,
        required_counters_with_zero_delta=flat)
    people = [dict(at=item['at'], count=item['numeric']['people_count']) for item in valid
              if _number(item['numeric'].get('people_count'))]
    checks['camera_people_context'] = _check('PASS' if valid and len(people) == len(valid) else 'UNKNOWN',
        'Observed people-count context only; missing counts are not inferred as zero or an identical scene',
        points=people, counts=sorted({item['count'] for item in people}), available_samples=len(valid))
    return checks


def check_case(case_dir, suite_case_row, scenario):
    """Return PASS/FAIL/UNKNOWN checks from local source evidence, with no edits."""
    case_dir = Path(case_dir)
    row = suite_case_row
    checks = {}; loaded = {}; read_errors = []
    try:
        scenario, scenario_sha = _scenario(scenario)
        events = scenario['events']; duration = scenario['duration_seconds']
    except (OSError, ValueError, TypeError, KeyError) as error:
        return dict(status='UNKNOWN', checks={'scenario': _check('UNKNOWN', str(error))},
                    original_run_retained=True, automatic_replacement_authorized=False)
    for name in ('summary', 'commands', 'samples', 'os-samples'):
        try:loaded[name] = _read(case_dir/(name+'.json'))
        except (OSError, ValueError) as error:read_errors.append(dict(file=name+'.json', error_type=type(error).__name__))
    summary = loaded.get('summary', row.get('summary', {}))
    samples = loaded.get('samples', [])
    commands = loaded.get('commands', [])
    os_rows = loaded.get('os-samples', [])
    if not isinstance(samples, list):samples = [];read_errors.append(dict(file='samples.json', error_type='NotAList'))
    if not isinstance(commands, list):commands = [];read_errors.append(dict(file='commands.json', error_type='NotAList'))
    if not isinstance(os_rows, list):os_rows = []
    backend = row.get('backend'); start = summary.get('stages', {}).get('measurement_start_monotonic')
    end = summary.get('stages', {}).get('measurement_end_monotonic')
    checks['source_evidence'] = _check('UNKNOWN' if read_errors else 'PASS',
        'All original files are read only; missing evidence does not remove the run',
        read_errors=read_errors, case_dir=str(case_dir), backend=backend,
        source_hashes=summary.get('source_hashes'), harness_hashes=summary.get('harness_hashes'),
        pcm_sha256=summary.get('pcm_sha256'), envelope_sha256=summary.get('envelope_sha256'))
    identity_ok = (backend in EXPECTED_SUMMARY_BACKEND and summary.get('backend') == EXPECTED_SUMMARY_BACKEND[backend]
                   and row.get('status') == 'COMPLETE' and summary.get('status') == 'COMPLETE'
                   and row.get('returncode', 0) == 0)
    checks['completed_expected_backend'] = _check('PASS' if identity_ok else 'FAIL',
        'Case completion and actual summary backend must match the selected backend',
        row_status=row.get('status'), summary_status=summary.get('status'), returncode=row.get('returncode'),
        actual_backend=summary.get('backend'), expected_backend=EXPECTED_SUMMARY_BACKEND.get(backend))
    checks['scenario_binding'] = _check('PASS' if scenario_sha and scenario_sha == summary.get('scenario_sha256') else 'UNKNOWN',
        'Scenario file hash binding' if scenario_sha else 'Loaded scenario dict has no raw-file hash binding',
        expected_sha256=scenario_sha, actual_sha256=summary.get('scenario_sha256'))
    expected_indexes = list(range(len(events)))
    actual_indexes = [command.get('index') for command in commands if isinstance(command, dict)]
    wrong = []; missing_outcomes = []; rejected = []; late = []; ids = []
    for index, command in enumerate(commands):
        if not isinstance(command, dict):wrong.append(index);continue
        if index >= len(events) or command.get('event') != events[index]:wrong.append(index)
        command_id = command.get('command_id');ids.append(command_id)
        outcome = command.get('outcome')
        if not isinstance(outcome, dict):missing_outcomes.append(index)
        elif outcome.get('command_id') != command_id or outcome.get('ok') is not True:
            rejected.append(dict(index=index, outcome=outcome))
        if _number(command.get('lateness_ms')) and command['lateness_ms'] > EVENT_GRACE_SECONDS*1000:
            late.append(dict(index=index, lateness_ms=command['lateness_ms']))
    commands_ok = (actual_indexes == expected_indexes and not wrong and len(set(ids)) == len(ids)
                   and all(isinstance(value, str) and value for value in ids)
                   and summary.get('events_enqueued') == len(events)
                   and summary.get('command_outcomes_observed') == len(events)
                   and not rejected and not missing_outcomes and not late)
    command_status = 'PASS' if commands_ok else 'UNKNOWN' if missing_outcomes and not (wrong or rejected or late) else 'FAIL'
    checks['commands_accepted_and_scheduled'] = _check(command_status,
        'Expected events, unique IDs, successful outcomes and coarse scheduling fidelity; accepting toggle_pause alone does not prove a pause',
        expected=len(events), observed=len(commands), expected_indexes=expected_indexes, actual_indexes=actual_indexes,
        wrong_events=wrong, missing_outcomes=missing_outcomes, rejected=rejected, late=late,
        allowed_enqueue_lateness_seconds=EVENT_GRACE_SECONDS)
    times = [item.get('elapsed') for item in samples if isinstance(item, dict) and _number(item.get('elapsed'))]
    gaps = [b-a for a, b in zip(times, times[1:])]
    ordered = len(times) == len(samples) and len(samples) >= 2 and all(gap > 0 for gap in gaps)
    duration_ok = (_number(start) and _number(end) and end > start and end-start >= duration
                   and end-start <= duration+max(EVENT_GRACE_SECONDS, 3*NOMINAL_SNAPSHOT_SECONDS))
    coverage_ok = ordered and times[0] <= NOMINAL_SNAPSHOT_SECONDS and times[-1] >= duration
    checks['snapshot_and_duration_coverage'] = _check('PASS' if coverage_ok and duration_ok and max(gaps, default=math.inf) <= 3*NOMINAL_SNAPSHOT_SECONDS else 'UNKNOWN',
        'Only sampled state is verified; no sub-frame response or physical scanout/audio latency is claimed',
        samples=len(samples), nominal_seconds=NOMINAL_SNAPSHOT_SECONDS,
        observed_median_seconds=statistics.median(gaps) if gaps else None, observed_maximum_gap_seconds=max(gaps, default=None),
        first_elapsed=times[0] if times else None, last_elapsed=times[-1] if times else None,
        measured_duration_seconds=end-start if _number(start) and _number(end) else None,
        requested_duration_seconds=duration)
    live_before = row.get('live_ui_before', {}); live_after = row.get('live_ui_after', {})
    live = [live_before, live_after]
    complete_live = all(item.get('available') is True for item in live)
    mode_ok = complete_live and all(item.get('portrait', {}).get('mode') == 'remote'
        and item['portrait'].get('target_fps') == 16 and item.get('playing') is False for item in live)
    settings_ok = complete_live and live_before.get('settings') == live_after.get('settings')
    checks['common_live_ui_boundaries'] = _check('PASS' if mode_ok and settings_ok else 'FAIL' if complete_live else 'UNKNOWN',
        'Common production UI is checked at run boundaries only; this does not prove its state between them',
        before=live_before, after=live_after)
    submit_results = []; toggle_results = []; cancel_results = []
    for index, event in enumerate(events):
        kind = _event_kind(event)
        if kind != 'submit':continue
        begin = _event_time(index, events, commands, start)
        stop = _stop_after(events, index, duration)
        points = _between(samples, begin, stop)
        playing = [point for point in points if point.get('playing') is True and point.get('paused') is False]
        clocks = [point['audio_time'] for point in playing if _number(point.get('audio_time'))]
        byte_points = [(point['elapsed'], point.get('audio', {}).get('converted_bytes')) for point in points
                       if _number(point.get('audio', {}).get('converted_bytes'))]
        prior = [point for point in samples if _number(point.get('elapsed')) and point['elapsed'] <= begin
                 and _number(point.get('audio', {}).get('converted_bytes'))]
        byte_begin = prior[-1]['audio']['converted_bytes'] if prior else byte_points[0][1] if byte_points else None
        byte_delta = byte_points[-1][1]-byte_begin if byte_points and byte_begin is not None else None
        caps = [item for point in points for item in point.get('audio', {}).get('caps', []) if isinstance(item, dict)]
        bad_caps = [item for item in caps if item != EXPECTED_CAPS]
        observed_caps = any(item == EXPECTED_CAPS for item in caps)
        enough = len(playing) >= MIN_STABLE_SAMPLES and len(clocks) >= MIN_STABLE_SAMPLES
        ok = enough and max(clocks)-min(clocks) >= NOMINAL_SNAPSHOT_SECONDS and byte_delta is not None and byte_delta > 0 and observed_caps and not bad_caps
        incomplete = not points or not byte_points or not caps or len(clocks) != len(playing)
        submit_results.append(dict(index=index, at=event['at'], until=stop,
            status='PASS' if ok else 'UNKNOWN' if incomplete else 'FAIL',
            playing_samples=len(playing), clock_range=_range(clocks), converted_byte_delta=byte_delta,
            observed_mouth_range=_range([point['mouth_level'] for point in playing if _number(point.get('mouth_level'))]),
            observed_gain_range=_range([point['speech_gain'] for point in playing if _number(point.get('speech_gain'))]),
            expected_caps=EXPECTED_CAPS, exact_expected_caps_observed=observed_caps, unexpected_caps=bad_caps[:2]))
    checks['actual_pcm_per_submit'] = _check(_overall({str(item['index']): item for item in submit_results}) if submit_results else 'UNKNOWN',
        'Each submit needs actual sampled playing/advancing audio clock and converted bytes at48k stereo S16LE; accepted commands alone are insufficient', turns=submit_results)
    toggles = [index for index, event in enumerate(events) if _event_kind(event) == 'toggle_pause']
    for pause_index, resume_index in zip(toggles[::2], toggles[1::2]):
        pause_at = _event_time(pause_index, events, commands, start)
        resume_at = _event_time(resume_index, events, commands, start)
        pause_window = _between(samples, pause_at+PAUSE_ENTRY_GUARD_SECONDS, resume_at)
        paused = [point for point in pause_window
                  if point.get('paused') is True and _number(point.get('audio_time'))]
        frozen_clocks = [point['audio_time'] for point in paused]
        after = [point for point in _between(samples, resume_at, _stop_after(events, resume_index, duration))
                 if point.get('paused') is False and point.get('playing') is True and _number(point.get('audio_time'))]
        resumed_clocks = [point['audio_time'] for point in after]
        resume_window = _between(samples, resume_at+EVENT_GRACE_SECONDS, _stop_after(events, resume_index, duration))
        wrong_pause = [point['elapsed'] for point in pause_window if point.get('paused') is False]
        wrong_resume = [point['elapsed'] for point in resume_window if point.get('paused') is True]
        enough = (len(paused) >= MIN_STABLE_SAMPLES and len(after) >= MIN_STABLE_SAMPLES
                  and len(paused) == len(pause_window) and bool(resume_window))
        frozen = bool(frozen_clocks) and max(frozen_clocks)-min(frozen_clocks) <= CLOCK_EQUALITY_TOLERANCE
        advanced = bool(resumed_clocks) and bool(frozen_clocks) and max(resumed_clocks)-max(frozen_clocks) >= NOMINAL_SNAPSHOT_SECONDS
        toggle_results.append(dict(pause_index=pause_index, resume_index=resume_index,
            status='FAIL' if wrong_pause or wrong_resume else 'PASS' if enough and frozen and advanced else 'UNKNOWN' if not enough else 'FAIL',
            paused_samples=len(paused), paused_clock_range=_range(frozen_clocks),
            resumed_playing_samples=len(after), resumed_clock_range=_range(resumed_clocks),
            unexpected_unpaused_samples_in_pause_window=wrong_pause,
            still_paused_after_resume_allowance=wrong_resume, resume_allowance_seconds=EVENT_GRACE_SECONDS,
            numeric_equality_tolerance=CLOCK_EQUALITY_TOLERANCE,
            note='Stored-value equality is not microsecond response precision; paused playing may remain true in the real old controller'))
    if len(toggles) % 2:toggle_results.append(dict(status='UNKNOWN', reason='Unpaired pause toggle'))
    checks['pause_clock_and_resume'] = _check(_overall({str(index): item for index, item in enumerate(toggle_results)}) if toggles else 'PASS',
        'A pause is proved only at sampled paused points with an unchanged clock, followed by sampled resumed progress', pairs=toggle_results)
    for index, event in enumerate(events):
        if _event_kind(event) not in ('cancel', 'reset'):continue
        begin = _event_time(index, events, commands, start)+CANCEL_SETTLE_SECONDS
        stop = next((item['at'] for item in events[index+1:] if _event_kind(item) in ('submit', 'cancel', 'reset')), duration)
        points = _between(samples, begin, stop)
        required = ('playing', 'paused', 'mouth_level', 'speech_gain', 'audio_time')
        missing_fields = any(any(key not in point for key in required) for point in points)
        native_mouth_missing = backend == 'new' and any(not _number((point.get('native_stats') or {}).get('mouth')) for point in points)
        violations = []
        for point in points:
            problems = []
            if point.get('playing') is not False:problems.append('playing_not_false')
            if point.get('paused') is not False:problems.append('paused_not_false')
            for key in ('mouth_level', 'speech_gain'):
                if not _number(point.get(key)) or abs(point[key]) > NUMERIC_ZERO_TOLERANCE:problems.append(key+'_not_zero')
            native = point.get('native_stats') or {}
            if backend == 'new' and _number(native.get('mouth')) and abs(native['mouth']) > NUMERIC_ZERO_TOLERANCE:
                problems.append('native_rendered_mouth_not_zero')
            if problems:violations.append(dict(elapsed=point.get('elapsed'), problems=problems))
        clocks = [point['audio_time'] for point in points if _number(point.get('audio_time'))]
        if clocks and max(clocks)-min(clocks) > CLOCK_EQUALITY_TOLERANCE:violations.append(dict(problem='post_cancel_clock_advanced'))
        complete = len(points) >= MIN_STABLE_SAMPLES and not missing_fields and not native_mouth_missing and len(clocks) == len(points)
        cancel_results.append(dict(index=index, at=event['at'], stable_window_begin=begin, until=stop,
            status='FAIL' if violations else 'PASS' if complete else 'UNKNOWN', samples=len(points),
            clock_range=_range(clocks), violations=violations[:10],
            native_mouth_evidence_missing=native_mouth_missing,
            settle_allowance_seconds=CANCEL_SETTLE_SECONDS))
    checks['cancel_stop_and_clear_mouth'] = _check(_overall({str(item['index']): item for item in cancel_results}) if cancel_results else 'UNKNOWN',
        'After a conservative0.5s settling allowance, verify sampled stopped/clear-mouth state and no clock progress until the next turn; not a37ms cancellation claim', events=cancel_results)
    jpeg = [point.get('jpeg_bytes') for point in samples if type(point.get('jpeg_bytes')) is int]
    if backend in ('new', 'old_nojpeg'):
        jpeg_ok = len(jpeg) == len(samples) and bool(jpeg) and all(size == 0 for size in jpeg)
    else:jpeg_ok = len(jpeg) == len(samples) and any(size > 0 for size in jpeg)
    checks['jpeg_feature_behavior'] = _check('PASS' if jpeg_ok else 'UNKNOWN' if len(jpeg) != len(samples) else 'FAIL',
        'B/C require zero recorded JPEG bytes; A must actually retain its preview feature',
        samples=len(jpeg), positive_samples=sum(size > 0 for size in jpeg), maximum_bytes=max(jpeg, default=None))
    if backend == 'old_nojpeg':
        patches = summary.get('source_patches', [])
        proven = any(item.get('symbol') == 'PreviewEncoder' and item.get('replacement') == 'old_harness_support.NoPreviewEncoder'
                     and item.get('applied_and_constructor_checked') is True and item.get('methods', {}).get('__bool__') == 'True'
                     for item in patches)
        checks['truthy_nojpeg_control_applied'] = _check('PASS' if proven else 'UNKNOWN',
            'The zero-JPEG control must preserve a truthy encoder branch and the original presenter/pixels', patches=patches)
    if _number(start) and _number(end) and end > start:
        checks.update(_camera_checks(os_rows, row, start, end))
    else:checks['camera_window'] = _check('UNKNOWN', 'Missing monotonic measurement boundaries')
    return dict(schema='aura.paired_ab.quality.case.v1', index=row.get('index'), backend=backend,
        status=_overall(checks), checks=checks, original_run_retained=True,
        status_meaning='FAIL/UNKNOWN limits workload comparability conclusions; it does not delete or hide measurements. PASS is not a cost-reduction verdict.',
        automatic_replacement_authorized=False,
        observation_limits=['200ms sampled controller/renderer state; no between-sample response precision',
            'A identity callback entry and B EGL swap completion are distinct stages; neither is scanout',
            'Synchronous fakesink proves the public PCM pipeline, not physical speaker/audio acceptance',
            'Camera health nominal5s; counters may describe different service work when scene/people context changes'])


def descriptive_jpeg_contribution(rows):
    """Unpaired A/C descriptive deltas only; no causal or additive JPEG estimate."""
    old = [row for row in rows if row.get('backend') == 'old']
    control = [row for row in rows if row.get('backend') == 'old_nojpeg']
    metrics = {}
    for key in ('renderer_family_cpu_seconds_per_second', 'whole_board_cpu_seconds_per_second',
                'board_excluding_collector_cpu_seconds_per_second'):
        a = [row.get('resources', {}).get(key) for row in old]
        c = [row.get('resources', {}).get(key) for row in control]
        a = [value for value in a if _number(value)];c = [value for value in c if _number(value)]
        metrics[key] = dict(A_values=a, C_values=c, A_mean=statistics.mean(a) if a else None,
            C_mean=statistics.mean(c) if c else None,
            A_minus_C_descriptive=statistics.mean(a)-statistics.mean(c) if a and c else None)
    return dict(status='UNKNOWN', reason='A and C are unpaired and time separated; descriptive differences cannot identify an exact causal or additive JPEG contribution',
        A_indices=[row.get('index') for row in old], C_indices=[row.get('index') for row in control], metrics=metrics,
        paired_effect_estimate=False, exact_additive_constant=False,
        CB_scope='C/B removes JPEG generation on both sides but still includes transport, presenter/Gst versus EGL, snapshot cadence, initialization and rendering differences',
        automatic_replacement_authorized=False)


def check_suite(suite_path, scenario, case_root=None):
    suite_path = Path(suite_path);suite = _read(suite_path)
    case_root = Path(case_root) if case_root is not None else suite_path.parent
    rows = suite.get('cases', [])
    backends = [row.get('backend') for row in rows]
    expected = backends == FORMAL_BACKENDS and [row.get('index') for row in rows] == list(range(1, 13))
    results = [check_case(case_root/(str(row['index']).zfill(2)+'-'+row['backend']), row, scenario) for row in rows]
    order = _check('PASS' if expected else 'UNKNOWN' if len(rows) < 12 else 'FAIL',
        'Formal order must be ABBAABBA C B B C; a short pilot is not formal evidence',
        expected=FORMAL_BACKENDS, observed=backends,
        main_pairs=[[1, 2], [4, 3], [5, 6], [8, 7]], control_pairs=[[9, 10], [12, 11]])
    pids = sorted({pid for item in results for pid in item['checks'].get('camera_same_pid', {}).get('evidence', {}).get('pids', [])})
    common_pid = _check('PASS' if len(pids) == 1 else 'FAIL' if len(pids) > 1 else 'UNKNOWN',
        'Common camera process must not silently restart between paired runs', pids=pids)
    common_inputs = {}
    for key in ('scenario_sha256', 'pcm_sha256', 'envelope_sha256', 'window_sha256', 'config_sha256'):
        values = [row.get('summary', {}).get(key) for row in rows]
        common_inputs[key] = dict(values=sorted({value for value in values if isinstance(value, str)}), complete=all(isinstance(value, str) for value in values))
    same_inputs = bool(rows) and all(item['complete'] and len(item['values']) == 1 for item in common_inputs.values())
    inputs = _check('PASS' if same_inputs else 'FAIL' if rows else 'UNKNOWN', 'All cases must use the same public workload/window/config hashes', fields=common_inputs)
    checks = dict(formal_order=order, common_camera_pid=common_pid, common_inputs=inputs)
    checks.update({str(item['index'])+'-'+str(item['backend']): dict(status=item['status']) for item in results})
    return dict(schema='aura.paired_ab.quality.suite.v1', status=_overall(checks), suite_status=suite.get('status'),
        suite_checks={key: value for key, value in checks.items() if key in ('formal_order', 'common_camera_pid', 'common_inputs')},
        cases=results, descriptive_A_C_only=descriptive_jpeg_contribution(rows),
        original_runs_retained=True, automatic_replacement_authorized=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, help='Local suite-result.json; all case files are read only')
    parser.add_argument('--case-root', type=Path, help='Local parent containing01-old etc; defaults to suite parent')
    parser.add_argument('--case-dir', type=Path, help='Single local case directory; also supply--row')
    parser.add_argument('--row', type=Path, help='Local paired-result.json for single-case checks')
    parser.add_argument('--scenario', type=Path, required=True)
    parser.add_argument('--output', type=Path, help='Optional NEW JSON file; never overwrite raw evidence or a previous report')
    args = parser.parse_args(argv)
    if args.suite is not None:
        if args.case_dir or args.row:parser.error('Use--suite or--case-dir/--row, not both')
        value = check_suite(args.suite, args.scenario, args.case_root)
    else:
        if args.case_dir is None or args.row is None:parser.error('Need--suite or both--case-dir and--row')
        value = check_case(args.case_dir, _read(args.row), args.scenario)
    encoded = json.dumps(value, ensure_ascii=True, indent=2)
    if args.output is not None:
        # Exclusive-create preserves all prior quality reports as well as runs.
        with args.output.open('x', encoding='utf8') as stream:stream.write(encoded)
    print(encoded)
    return 0  # Evidence status is data, never a signal to remove/filter a run.


if __name__ == '__main__':raise SystemExit(main())
