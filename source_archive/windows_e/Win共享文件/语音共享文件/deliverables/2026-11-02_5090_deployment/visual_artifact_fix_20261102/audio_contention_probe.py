"""Same source/page, original listening ON/OFF/ON; metadata only, no motion."""
import glob
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import struct
import time

BOOT = 'a6d4a069-e9b0-4065-8df7-dc23556b168e'
STARTUP = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
SHA = 'c3861fa3d2cbb10fee424804f7b3932eadd576819a2a6290c7ca406d900b9602'
OWNERS = [
    (394712, '3106155', '48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),
    (394720, '3106263', 'e81bf963d019b5b23293db8d863359ca706564b4e1fa74a69a212517dc08de48'),
    (362659, '2850120', 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'),
]
TX = Path('/home/root/aura-5090-recovery-20261102-a6d4a069/audio-contention-on-off-on-1')

def verify():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
    assert hashlib.sha256(STARTUP.read_bytes()).hexdigest() == SHA
    for pid, birth, command in OWNERS:
        p = Path('/proc') / str(pid)
        assert p.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19] == birth
        assert hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest() == command

def request(port, path, body=None):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
    try:
        headers = {'Origin': 'http://127.0.0.1:' + str(port), 'Host': '127.0.0.1:' + str(port)}
        method = 'GET'
        if body is not None:
            method = 'POST'
            headers['Content-Type'] = 'application/json'
            body = json.dumps(body).encode()
        before = time.monotonic_ns()
        c.request(method, path, body=body, headers=headers)
        r = c.getresponse()
        data = r.read(2097153)
        assert r.status == 200 and len(data) <= 2097152
        return json.loads(data), round((time.monotonic_ns() - before) / 1e6, 3)
    finally:
        c.close()

def ui():
    return request(8783, '/api/state')[0]

def intent(name, value):
    p = TX / name
    fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write((json.dumps(value, sort_keys=True) + '\n').encode())
        f.flush()
        os.fsync(f.fileno())
    fd = os.open(str(TX), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def listening(target, name):
    verify()
    v = ui()
    assert not v.get('playing') and not v.get('pending_job')
    assert not (v.get('manual_pan') or {}).get('automatic_following')
    h = v['handsfree_dialogue']
    sent = False
    if h['enabled'] != target:
        intent(name, {'target_enabled': target, 'single_original_toggle': True, 'mono_ns': time.monotonic_ns()})
        request(8783, '/api/command', {'type': 'conversation_toggle'})
        sent = True
    for _ in range(15):
        v = ui()
        h = v['handsfree_dialogue']
        if h['enabled'] == target and h['microphone_open'] == target:
            return sent
        time.sleep(.2)
    raise RuntimeError('Listening transition requires GET-only reconciliation')

def process(pid):
    p = Path('/proc') / str(pid)
    values = p.joinpath('stat').read_text().rsplit(')', 1)[1].split()
    result = {'utime_ticks': int(values[11]), 'stime_ticks': int(values[12]), 'threads': int(values[17])}
    if p.joinpath('schedstat').is_file():
        ss = [int(x) for x in p.joinpath('schedstat').read_text().split()]
        result.update(main_thread_runtime_ns=ss[0], main_thread_runqueue_ns=ss[1], main_thread_slices=ss[2])
    return result

def system():
    result = {}
    for pattern, label in [('/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq', 'frequency_khz'),
                           ('/sys/class/thermal/thermal_zone*/temp', 'temperature_millidegrees')]:
        rows = {}
        for path in glob.glob(pattern):
            try:
                key = Path(path).parent.parent.name if label == 'frequency_khz' else Path(path).parent.name
                rows[key] = int(Path(path).read_text().strip())
            except (OSError, ValueError):
                pass
        result[label] = rows
    return result

def header(preview):
    epoch = preview.get('camera_epoch')
    assert isinstance(epoch, str) and re.fullmatch('[0-9a-f]{32}', epoch)
    p = Path('/run') / ('aura-camera-ui-' + epoch + '.frame')
    fd = os.open(str(p), os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as f:
        prefix = f.read(10)
        magic, count = struct.unpack('!8sH', prefix)
        assert magic == b'AURABGR1' and 0 < count <= 1024
        value = json.loads(f.read(count))  # Pixel bytes are never read.
    assert value['board_boot_id'] == BOOT and value['camera_epoch'] == epoch
    now = int(time.monotonic() * 1000)
    return {'frame_id': value['frame_id'], 'captured_mono_ms': value['captured_mono_ms'],
            'raw_header_age_ms': now - value['captured_mono_ms']}

verify()
before = ui()
assert not before.get('playing') and not before.get('pending_job')
assert not (before.get('manual_pan') or {}).get('automatic_following')
assert before['handsfree_dialogue']['enabled'] is True
assert before['handsfree_dialogue']['microphone_open'] is True
TX.mkdir(mode=0o700)
intent('probe-intent.json', {'source_sha256': SHA, 'original_listening': True, 'phase_seconds': 6,
                             'pixel_bytes_read': False, 'axis_commands': False})
navigation_sent = False
if before.get('ui_page') != 'vision':
    intent('vision-page-intent.json', {'single_original_ui_page': 'vision'})
    request(8783, '/api/command', {'type': 'ui_page', 'page': 'vision'})
    navigation_sent = True
for _ in range(15):
    before = ui()
    if before.get('ui_page') == 'vision':
        break
    time.sleep(.2)
assert before.get('ui_page') == 'vision'
time.sleep(.5)
samples = []
phases = []
for tag, target in [('A_LISTEN_ON', True), ('B_LISTEN_OFF', False), ('C_LISTEN_ON', True)]:
    changed = listening(target, tag + '-intent.json')
    started = time.monotonic()
    count = 0
    while time.monotonic() - started < 6:
        sample_start = time.monotonic()
        v, gui_ms = request(8783, '/api/state')
        camera, camera_ms = request(8790, '/v1/ui/status')
        face, face_ms = request(8790, '/v1/motion/face/observation')
        now_ms = int(time.monotonic() * 1000)
        assert v.get('ui_page') == 'vision' and not (v.get('manual_pan') or {}).get('automatic_following')
        h = v['handsfree_dialogue']
        assert h['enabled'] == target and h['microphone_open'] == target
        preview = camera.get('preview') or {}
        metrics = (v.get('ui_runtime') or {}).get('preview_metrics') or {}
        business = v.get('board_business') or {}
        speaker = business.get('speaker') or {}
        rec = v.get('local_recording') or {}
        raw = header(preview)
        face_source = face.get('source_mono_ms')
        face_detect = face.get('face_detection_mono_ms')
        row = {'phase': tag, 'mono_ms': now_ms, 'ui_sequence': v.get('sequence'),
            'handsfree_state': h.get('state'), 'listening_enabled': target, 'microphone_open': h.get('microphone_open'),
            'playing': bool(v.get('playing')), 'pending_job': bool(v.get('pending_job')),
            'ui_phase': v.get('phase'), 'local_recording_state': rec.get('state'),
            'speaker_active': speaker.get('active'), 'speaker_queued_or_active': speaker.get('queued_or_active'),
            'recording_numeric': {k: rec[k] for k in ('captured_ms', 'buffered_ms', 'queued_chunks', 'dropped_chunks', 'overruns') if type(rec.get(k)) in (int, float)},
            'raw_header': raw, 'camera_preview_frame_id': preview.get('frame_id'),
            'face_source_age_ms': now_ms - face_source if type(face_source) is int else None,
            'face_detection_age_ms': now_ms - face_detect if type(face_detect) is int else None,
            'face_ready': face.get('state') == 'READY', 'face_present': bool(face.get('target')),
            'projection_frame_reference': metrics.get('frame_reference'), 'projection_frame_visible': metrics.get('frame_visible'),
            'sink_entry_age_ms': metrics.get('entry_age_ms'), 'displayed_frames': metrics.get('displayed_frames'),
            'preview_error_present': bool(metrics.get('error')), 'request_ms': {'GUI': gui_ms, 'camera': camera_ms, 'face': face_ms},
            'GUI_process': process(394720), 'camera_process': process(362659)}
        if count % 4 == 0:
            row['system'] = system()
        samples.append(row)
        count += 1
        time.sleep(max(0., .25 - (time.monotonic() - sample_start)))
    phases.append({'phase': tag, 'target_enabled': target, 'toggle_sent': changed,
                   'actual_seconds': round(time.monotonic() - started, 3), 'samples': count})
verify()
after = ui()
assert after['handsfree_dialogue']['enabled'] is True and after['handsfree_dialogue']['microphone_open'] is True
result = {'schema': 'aura-same-code-same-vision-listening-ABA-1', 'status': 'CONTROLLED_LISTENING_ON_OFF_ON_METADATA_COMPLETE',
    'boot_id': BOOT, 'startup_sha256': SHA, 'source_or_camera_or_model_or_axis_parameters_changed': False,
    'axis_commands_sent': False, 'pixel_audio_transcript_name_identity_score_or_vector_exported': False,
    'original_listening_restored': True, 'vision_page_held_for_all_samples': True, 'navigation_before_all_phases': navigation_sent,
    'clock_ticks_per_second': os.sysconf('SC_CLK_TCK'), 'phases': phases, 'samples': samples,
    'input_overrun_not_exposed_is_unknown': True, 'projection_age_is_not_physical_scanout_latency': True}
trial = Path('/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-stable150-35d5e154/runs/ui-31387162624166/trial.json')
try:
    assert trial.stat().st_size <= 8 * 1024 * 1024
    trial_raw = trial.read_bytes()
    trial_data = json.loads(trial_raw)
    result['existing_trial_telemetry'] = trial_data.get('telemetry')
    result['existing_trial_sha256'] = hashlib.sha256(trial_raw).hexdigest()
    result['existing_trial_telemetry_exposed'] = 'telemetry' in trial_data
except (OSError, ValueError, KeyError, TypeError) as error:
    result['existing_trial_telemetry_read_error_class'] = type(error).__name__
intent('probe-result.json', result)
print(json.dumps(result))
