"""Bounded metadata-only A/B/A camera sample while the GUI is normally closed."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import restored_readback as adapter


GUI_PREDECESSORS = (171266, 171274)
PHASES = {'A1': ('GUARDED', 'baseline'), 'B': ('CANDIDATE_RUNNING', 'candidate'),
          'A2': ('BASELINE_RESTORED', 'restored')}


def gui_closed():
    command = ['systemctl', 'show', '--all', 'aura-avatar-ui.service',
               '-p', 'MainPID', '-p', 'ActiveState', '-p', 'SubState', '-p', 'Job']
    result = subprocess.run(command, capture_output=True, timeout=5, check=True, text=True)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if (values.get('MainPID') != '0' or values.get('ActiveState') not in ('inactive', 'failed')
            or values.get('Job', '') not in ('', '0')
            or any((Path('/proc') / str(pid)).exists() for pid in GUI_PREDECESSORS)):
        raise ValueError('GUI must remain normally closed throughout all three arms')


def process_sample(pid):
    fields = (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()
    if fields[0] in ('Z', 'X'):
        raise ValueError('Camera process is no longer live')
    cpu = [int(value) for value in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    return {'mono': time.monotonic(), 'ticks': int(fields[11]) + int(fields[12]),
            'birth': fields[19], 'rss_bytes': int(fields[21]) * os.sysconf('SC_PAGE_SIZE'),
            'system_busy_ticks': sum(cpu) - cpu[3] - cpu[4]}


def health_projection(health, executor):
    native, _ = executor.native_health(health.get('dpu_schedule'))
    identity = health.get('identity', {})
    face = identity.get('face_targets', {})
    if (health.get('camera_error') or health.get('detector_error') or health.get('preview_error')
            or native.get('fenced') or not native.get('seed_loaded')
            or identity.get('ready') is not True or identity.get('error')
            or face.get('ready') is not True or face.get('error') or face.get('fault_latched')):
        raise ValueError('Camera, preview, identity or native health failed')
    return {
        'pid': health['pid'], 'board_boot_id': health['board_boot_id'],
        'service_epoch': health['service_epoch'], 'camera_epoch': health['camera_epoch'],
        'capture_frames': health['capture_frames'], 'detected_frames': health['detected_frames'],
        'preview_frames': health['preview_frames'], 'preview_buffers': health['preview_buffers'],
        'capture_age_ms': health.get('capture_age_ms'), 'observation_age_ms': health.get('observation_age_ms'),
        'people_count': health.get('people_count'), 'face_source_age_ms': face.get('source_age_ms'),
        'face_processed': face.get('processed'), 'native_primary_calls': native['primary_calls'],
        'native_primary_overruns': native['primary_period_overruns'],
        'native_optional_overruns': native['optional_overruns'],
        'camera_error_present': False, 'detector_error_present': False, 'preview_error_present': False,
    }


def summarize(rows, hz):
    first, last = rows[0], rows[-1]
    seconds = last['process']['mono'] - first['process']['mono']
    if seconds <= 0 or hz <= 0:
        raise ValueError('Positive sampling duration and clock ticks required')
    if any(row['process']['birth'] != first['process']['birth']
           or any(row['health'][key] != first['health'][key]
                  for key in ('pid', 'board_boot_id', 'service_epoch', 'camera_epoch')) for row in rows):
        raise ValueError('Camera owner or epoch changed during sample')
    rates = {}
    for key in ('capture_frames', 'detected_frames', 'preview_frames'):
        delta = last['health'][key] - first['health'][key]
        if delta <= 0:
            raise ValueError('Camera pipeline did not progress')
        rates[key + '_per_second'] = delta / seconds
    camera_ticks = last['process']['ticks'] - first['process']['ticks']
    system_ticks = last['process']['system_busy_ticks'] - first['process']['system_busy_ticks']
    if camera_ticks < 0 or system_ticks < 0:
        raise ValueError('CPU counters went backwards')
    return {'seconds': seconds, 'camera_cpu_cores': camera_ticks / hz / seconds,
            'whole_system_busy_cores': system_ticks / hz / seconds,
            'camera_rss_min_bytes': min(row['process']['rss_bytes'] for row in rows),
            'camera_rss_max_bytes': max(row['process']['rss_bytes'] for row in rows),
            'people_counts': [row['health']['people_count'] for row in rows],
            'face_source_age_ms': [row['health']['face_source_age_ms'] for row in rows], **rates}


def observe(label, journal_sha, seconds):
    helper = adapter.load_helper()
    executor = helper.load_executor(adapter.FIXED['executor_path'], adapter.FIXED['executor_sha256'],
                                    authority=adapter.FIXED)
    system = helper.readonly_system(executor)
    path = adapter.FIXED['journal_path']
    raw = helper.private_read(path)
    helper.need(helper.sha(journal_sha) and helper.digest(raw) == journal_sha, 'explicit_current_journal_sha_required')
    data = helper.parse(raw)
    phase, owner_key = PHASES[label]
    helper.need(data.get('phase') == phase and data.get('boot') == adapter.FIXED['boot']
                and data.get('manifest_sha256') == adapter.MANIFEST_SHA
                and data.get('readback_sha256') == adapter.FIXED['baseline_sha256']
                and data.get('baseline', {}).get('pid') == adapter.FIXED['baseline_pid'],
                'exact_A_B_A_phase_and_original_baseline_required')
    trial = executor.Trial(system, helper.FrozenJournal(data))
    owner = data[owner_key]
    argv = trial.candidate_argv() if label == 'B' else data['baseline_argv']
    trial.exact_owner(trial.invariants(argv=argv), owner, argv)
    if label != 'A1':
        trial.running_health(owner, data['handoff'])
    rows = []
    start = time.monotonic()
    for index in range(seconds + 1):
        time.sleep(max(0, start + index - time.monotonic()))
        gui_closed()
        helper.need(system.owner(owner['pid']) == owner, 'camera_owner_changed')
        health = health_projection(system.health(), executor)
        process = process_sample(owner['pid'])
        helper.need(health['pid'] == owner['pid'] and health['board_boot_id'] == data['boot']
                    and process['birth'] == owner['birth'], 'health_or_process_owner_changed')
        rows.append({'process': process, 'health': health})
    trial.exact_owner(trial.invariants(argv=argv), owner, argv)
    if label != 'A1':
        trial.running_health(owner, data['handoff'])
    helper.need(helper.digest(helper.private_read(path)) == journal_sha, 'trial_journal_changed_during_sample')
    return {'status': 'METADATA_SAMPLE_COMPLETE', 'label': label, 'owner': owner,
            'manifest_sha256': adapter.MANIFEST_SHA, 'journal_sha256': journal_sha,
            'summary': summarize(rows, os.sysconf('SC_CLK_TCK')), 'samples': rows,
            'GUI_normally_closed_all_samples': True, 'sampler_JPEG_GET_requests': 0,
            'camera_frames_or_private_database_read': False, 'production_mutated': False,
            'limits': ['All three arms require the same closed GUI state. GUI keepalive is inactive during this window.',
                       'Process CPU and RSS describe this camera workload. Scene and face-load changes remain confounders.',
                       'No JPEG request traffic is generated. The independent public screen covers demand-side encoding cost.',
                       'Counts per second describe pipeline completion. Physical display refresh and conversation latency are unmeasured.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('label', choices=tuple(PHASES))
    parser.add_argument('--journal-sha256', required=True)
    parser.add_argument('--seconds', type=int, choices=(20, 30, 60), default=30)
    args = parser.parse_args()
    try:
        result = observe(args.label, args.journal_sha256, args.seconds)
    except Exception as exc:
        result = {'status': 'REFUSED', 'error_type': type(exc).__name__, 'production_mutated': False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'METADATA_SAMPLE_COMPLETE' else 2


if __name__ == '__main__':
    sys.exit(main())
