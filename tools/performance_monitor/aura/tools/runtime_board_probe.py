"""One read-only KV260 snapshot. Run from SSH stdin using only the standard library."""
import http.client
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time


def public_fields(document, names):
    """Only bounded scalar metadata can leave the board."""
    if not isinstance(document, dict):
        return {}
    result = {}
    for key in names.split():
        value = document.get(key)
        if isinstance(value, bool) or (type(value) in (int, float) and math.isfinite(value)):
            result[key] = value
        elif isinstance(value, str) and re.fullmatch(r'[\w. /:+-]{1,90}', value, re.ASCII):
            result[key] = value
    return result


def local_get(port, route):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=0.85)
    try:
        connection.request('GET', route, headers={'Connection': 'close'})
        response = connection.getresponse()
        if response.status == 200:
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) <= 2 * 1024 * 1024:
                document = json.loads(raw)
                if isinstance(document, dict):
                    return document
    except (OSError, ValueError, http.client.HTTPException):
        pass
    finally:
        connection.close()
    return {}


def gui_status(document):
    if 'ui_page' not in document:
        return {'available': False}
    business = document.get('board_business') or {}
    dialogue = business.get('dialogue') or {}
    latency = dialogue.get('latency') or {}
    listening = document.get('handsfree_dialogue') or {}
    pan = document.get('manual_pan') or {}
    return {
        'available': True,
        **public_fields(document, 'ui_page phase playing'),
        'processing': public_fields(document.get('board_processing'), 'task_state asr_location memory_location'),
        'listening': public_fields(listening, 'enabled state microphone_open entry_mode conversation_mode'),
        'listen_counts': public_fields(listening.get('diagnostics'), 'armed speech_starts submitted entry_rejected'),
        'frontend': public_fields((document.get('audio_frontend') or {}).get('current'),
                                  'worker_pid worker_process_alive capture_failures'),
        'audio': public_fields(document.get('audio_output'), 'device_state queued_ms underrun_packets'),
        'avatar': public_fields(document.get('avatar_display'), 'frames visible target_fps presentation_state native_call_ms'),
        'pan': public_fields(pan, 'state pulse_us backend_pid automatic_following'),
        'follow': public_fields(pan.get('face_follow'), 'state phase reason commands_accepted segments heartbeat_mono_ms'),
        'motor': public_fields(pan.get('readback'), 'active armed flags lease_left_ms width_us'),
        'memory': public_fields(business.get('memory'), 'running completed discarded'),
        'retention': public_fields(business.get('retention'), 'enabled running'),
        'writer': public_fields(business.get('writer'), 'held'),
        'timeline': public_fields(business.get('visual_timeline'), 'enabled thread_alive steps errors'),
        'speaker': public_fields(business.get('speaker'), 'ready active single_cpu_worker queued_or_active submitted complete'),
        'dialogue': public_fields(dialogue, 'enabled streaming pending board_owned feedback_ready'),
        'ack': public_fields(dialogue.get('last_playback_ack'), 'committed'),
        'latency': public_fields(latency, 'asr_ms admission_ms route_ms first_audio_queued_ms worker_total_ms complete error_class'),
        'prepare': public_fields(latency.get('prepare'), 'context_ms llm_rpc_ms llm_calls tts_rpc_ms tts_calls tts_max_rpc_ms first_tts_ready_ms first_chunk_emitted_ms prepare_total_ms streamed_chunks complete'),
        'faults': public_fields(document.get('runtime_faults'), 'count'),
    }


def camera_status(document, boot_id):
    if document.get('board_boot_id') != boot_id:
        return {'available': False}
    identity = document.get('identity') or {}
    schedule = document.get('dpu_schedule') or {}
    optional = schedule.get('optional') or {}
    return {
        'available': True,
        **public_fields(document, 'pid capture_frames detected_frames capture_hz detection_hz capture_age_ms last_inference_ms'),
        'camera_fault': bool(document.get('camera_error') or document.get('detector_error')),
        'detector': public_fields(document.get('detector'), 'model tracking_backend'),
        'identity': public_fields(identity, 'ready backend processed'),
        'faces': public_fields(identity.get('face_targets'), 'worker_alive processed last_inference_ms source_age_ms'),
        'features': public_fields(identity.get('feature_inference'), 'ready completed features_returned'),
        'schedule': public_fields(schedule, 'primary_calls primary_period_overruns native_critical quiesced owner_fenced'),
        'optional': {key: public_fields(optional.get(key), 'calls native_completed native_failures disabled overruns')
                     for key in ('yunet', 'sface')},
    }


def proc_stat(raw):
    begin, end = raw.index('('), raw.rindex(')')
    fields = raw[end + 1:].split()
    return {'name': raw[begin + 1:end][:80], 'state': fields[0], 'ppid': int(fields[1]),
            'ticks': int(fields[11]) + int(fields[12]), 'threads': int(fields[17]),
            'birth': int(fields[19]), 'rss_pages': int(fields[21])}


def service_name(path):
    matches = re.findall(r'(?:^|/)([^/:\n]+\.service)(?=/|$)', path, re.MULTILINE)
    return matches[-1] if matches else ''


def process_role(unit, name, argv, manual_pid, pid):
    if unit.startswith('aura-'):
        scripts = {os.path.basename(arg) for arg in argv if arg.endswith('.py')}
        for script, role in (
                ('run_face_motion.py', 'follow'), ('board_frontend_process.py', 'frontend'),
                ('gstreamer_audio_worker.py', 'playback'), ('face_zone_editor.py', 'editor'),
                ('board_avatar_pan.py', 'gui'), ('board_avatar_gtk.py', 'gui'),
                ('launcher.py', 'supervisor')):
            if script in scripts:
                return role
        if unit == 'aura-camera-ui.service':
            return 'camera'
        if name == 'arecord':
            return 'capture'
        if pid == manual_pid:
            return 'manual'
        return 'auxiliary'
    if unit == 'dfx-mgr.service':
        return 'fabric'
    if name == 'pulseaudio':
        return 'sound'
    if unit == 'xserver-nodm.service':
        return 'display'
    return ''


def processes(manual_pid):
    result = []
    skipped = 0
    page_mib = os.sysconf('SC_PAGE_SIZE') / (1024 * 1024)
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit():
            continue
        try:
            pid = int(directory.name)
            item = proc_stat((directory / 'stat').read_text(errors='replace'))
            unit = service_name((directory / 'cgroup').read_text(errors='replace'))
            argv = []
            if unit.startswith('aura-'):
                with (directory / 'cmdline').open('rb') as handle:
                    argv = handle.read(16384).decode(errors='replace').split('\0')
            role = process_role(unit, item['name'], argv, manual_pid, pid)
            item.update(pid=pid, unit=unit, role=role,
                        rss_mib=round(max(0, item.pop('rss_pages')) * page_mib, 2))
            result.append(item)
        except (OSError, ValueError, IndexError):
            skipped += 1
    return result, skipped


def services():
    try:
        result = subprocess.run(['systemctl', 'list-units', '--all', '--type=service',
                                 '--no-legend', '--plain', '--no-pager'],
                                capture_output=True, text=True, timeout=1.5,
                                env=dict(os.environ, LC_ALL='C', SYSTEMD_COLORS='0'))
        if result.returncode:
            return None
        rows = []
        for line in result.stdout.splitlines():
            fields = line.split()
            if len(fields) >= 4 and fields[0].endswith('.service'):
                rows.append({'unit': fields[0], 'load': fields[1], 'active': fields[2], 'sub': fields[3]})
        return rows
    except (OSError, subprocess.SubprocessError):
        return None


def snapshot():
    started = time.monotonic()
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    cpu_lines = Path('/proc/stat').read_text().splitlines()
    ticks = list(map(int, cpu_lines[0].split()[1:9]))
    memory = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, _, raw = line.partition(':')
        if key in ('MemTotal', 'MemAvailable'):
            memory[key] = int(raw.split()[0]) / 1024
    gui = gui_status(local_get(8783, '/api/state'))
    camera = camera_status(local_get(8790, '/health'), boot_id)
    rows, skipped = processes(gui.get('pan', {}).get('backend_pid'))
    return {'schema': 1, 'boot_id': boot_id, 'monotonic': started,
            'logical_cpus': sum(bool(re.match(r'cpu\d+ ', line)) for line in cpu_lines),
            'total_ticks': sum(ticks), 'idle_ticks': sum(ticks[3:5]), 'memory': memory,
            'uptime_s': float(Path('/proc/uptime').read_text().split()[0]),
            'processes': rows, 'skipped_pids': skipped, 'services': services(),
            'camera': camera, 'gui': gui, 'sample_ms': round((time.monotonic() - started) * 1000, 1)}


if __name__ == '__main__':
    print(json.dumps(snapshot(), ensure_ascii=True, separators=(',', ':')))
