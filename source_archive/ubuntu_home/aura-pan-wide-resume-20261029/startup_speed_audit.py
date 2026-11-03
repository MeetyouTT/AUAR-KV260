import json
import base64
import gzip
import hashlib
import subprocess
from pathlib import Path


def run(args, timeout=18):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=timeout)
    return {'returncode': result.returncode, 'output': result.stdout[-16000:]}


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
uptime = Path('/proc/uptime').read_text().split()[0]
unit = run(['systemctl', 'show', 'aura-avatar-ui.service', '-p', 'LoadState',
            '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID', '-p', 'ExecStart',
            '-p', 'FragmentPath', '-p', 'DropInPaths', '-p', 'ActiveEnterTimestampMonotonic',
            '-p', 'ExecMainStartTimestampMonotonic', '-p', 'NRestarts'])
unit_files = run(['systemctl', 'cat', 'aura-avatar-ui.service'])
journal = run(['journalctl', '-b', '-u', 'aura-avatar-ui.service', '--no-pager',
               '-o', 'short-monotonic', '-n', '80'])
xserver = run(['systemctl', 'show', 'xserver-nodm.service', '-p', 'ActiveState',
               '-p', 'MainPID', '-p', 'ExecMainStartTimestampMonotonic'])

result = {'boot_id': boot, 'uptime_seconds': float(uptime), 'unit': unit,
          'unit_files': unit_files, 'journal': journal, 'xserver': xserver}
unit_text = unit.get('output', '')
config_path = None
for token in unit_text.split():
    if token.endswith('/config.json'):
        config_path = token
        break
config = read_json(config_path) if config_path else None
result['active_config_path'] = config_path
if config:
    config_bytes = Path(config_path).read_bytes()
    result['active_config_full'] = {
        'sha256': hashlib.sha256(config_bytes).hexdigest(),
        'bytes': len(config_bytes),
        'gzip_base64': base64.b64encode(gzip.compress(config_bytes, mtime=0)).decode('ascii'),
    }
    keys = ('runtime', 'display_wait_seconds', 'ready_wait_seconds', 'edid_grace_seconds',
            'display_stable_seconds', 'startup_display_retrain',
            'display_retrain_off_seconds', 'port', 'gui_sha256')
    result['active_config'] = {key: config.get(key) for key in keys}
    runtime = Path(config['runtime'])
    launcher = Path(config_path).parent/'launcher.py'
    try:
        launcher_bytes = launcher.read_bytes()
        result['active_launcher'] = {
            'path': str(launcher),
            'sha256': hashlib.sha256(launcher_bytes).hexdigest(),
            'bytes': len(launcher_bytes),
            'gzip_base64': base64.b64encode(gzip.compress(launcher_bytes, mtime=0)).decode('ascii'),
        }
    except OSError as exc:
        result['active_launcher_error'] = str(exc)
    gui_config = read_json(runtime/'aura/config/board_avatar_gtk.json')
    if gui_config:
        keys = ('native_avatar', 'cache_sequences', 'native_pixel_threads', 'tick_ms',
                'stable_avatar_fps', 'streaming_conversation', 'persistent_audio',
                'handsfree_dialogue', 'voice_barge_in', 'audio_frontend', 'portrait_offload')
        result['gui_config'] = {key: gui_config.get(key) for key in keys}
    launch = read_json(runtime/'launch.json')
    result['launch'] = launch
    if launch and launch.get('boot_id') == boot:
        session = Path(launch.get('session', ''))
        result['setup'] = read_json(session/'setup.json')
        result['ready'] = read_json(session/'ready.json')
        log_path = session/'stage.log'
        try:
            result['stage_log_tail'] = log_path.read_text(errors='replace')[-8000:]
        except OSError as exc:
            result['stage_log_error'] = str(exc)
        audio_log = session/'evidence/audio_worker.log'
        try:
            result['audio_worker_log_tail'] = audio_log.read_text(errors='replace')[-8000:]
            result['audio_worker_log_bytes'] = audio_log.stat().st_size
        except OSError as exc:
            result['audio_worker_log_error'] = str(exc)
        total = 0
        missing = []
        sizes = []
        for relative in config.get('component_sha256', {}):
            path = runtime/'aura'/relative
            try:
                size = path.stat().st_size
                total += size
                sizes.append((size, relative))
            except OSError:
                missing.append(relative)
        result['component_inventory'] = {
            'count': len(config.get('component_sha256', {})),
            'total_bytes': total,
            'largest': [{'bytes': size, 'path': name} for size, name in sorted(sizes, reverse=True)[:12]],
            'missing': missing[:20],
        }
print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
