"""KV260 baseline, executed from stdin: metadata reads only, no project imports."""
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess


def text(path, limit=1024 * 1024):
    try:
        with open(path, 'rb') as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            return {'error': 'size_limit'}
        return raw.rstrip(b'\0\r\n').decode('utf-8', errors='replace')
    except OSError as error:
        return {'error': type(error).__name__}


def digest(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as error:
        return {'error': type(error).__name__}


def command(argv):
    try:
        value = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, timeout=8)
        return dict(exit_code=value.returncode, stdout=value.stdout[:32768], stderr=value.stderr[:2048])
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'error': type(error).__name__}


SAFE_KEYS = set('ready alive status state ok pid birth_ticks source_pid source_birth_ticks '
                'boot_id frame_id source_frame_id frame_sequence frames captured_frames '
                'completed_frames detector_ready identity_ready camera_errors detector_errors '
                'identity_errors failures errors width height fps device model firmware '
                'enabled microphone_open playing running quarantined closed'.split())


def safe(value):
    if not isinstance(value, dict):
        return {}
    selected = {}
    for key, item in value.items():
        if key in SAFE_KEYS and isinstance(item, (str, bool, int, float, type(None))):
            selected[key] = item
        elif isinstance(item, dict):
            nested = safe(item)
            if nested:
                selected[key] = nested
    return selected


def health(port, path):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            return {'error': 'size_limit'}
        value = json.loads(raw)
        return dict(http_status=response.status, top_level_keys=sorted(value), metadata=safe(value))
    except (OSError, ValueError, http.client.HTTPException) as error:
        return {'error': type(error).__name__}
    finally:
        connection.close()


processes, dpu_users = [], []
for directory in Path('/proc').iterdir():
    if not directory.name.isdigit():
        continue
    try:
        raw = (directory / 'cmdline').read_bytes()
        arguments = [part.decode('utf-8', errors='replace') for part in raw.split(b'\0') if part]
        if not arguments:
            continue
        maps = (directory / 'maps').read_text(errors='replace')
        if 'libvart' in maps or 'libaura_native_operator' in maps:
            dpu_users.append(int(directory.name))
        if any('aura' in part.lower() or 'camera' in part.lower() for part in arguments):
            stat = (directory / 'stat').read_text()
            fields = stat.rsplit(')', 1)[1].split()
            # Hash full argv. Only executable/script paths and option names are exported.
            public_args = [part for part in arguments if part.startswith('/') or part.startswith('--')]
            processes.append(dict(pid=int(directory.name), birth_ticks=int(fields[19]),
                                  command_sha256=hashlib.sha256(raw).hexdigest(), public_paths_and_options=public_args))
    except (OSError, ValueError, IndexError):
        continue

business = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
preference = Path('/home/root/.local/share/aura-board-business/listening_preference.json')
try:
    listening = safe(json.loads(preference.read_bytes()))
except (OSError, ValueError) as error:
    listening = {'error': type(error).__name__}

result = dict(
    scope='fresh_boot_read_only_metadata_no_device_control',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    boot_id=text('/proc/sys/kernel/random/boot_id'),
    architecture=os.uname().machine,
    board_model=text('/proc/device-tree/model'),
    uptime=text('/proc/uptime'),
    firmware_name=text('/proc/device-tree/fpga-full/firmware-name'),
    fpga_state=text('/sys/class/fpga_manager/fpga0/state'),
    vart_configuration=text('/etc/vart.conf'),
    fdt_sha256=digest('/sys/firmware/fdt'),
    xmutil_apps=command(['/usr/bin/xmutil', 'listapps']),
    systemd=command(['systemctl', 'show', 'aura-camera-ui.service', 'aura-avatar-ui.service',
        '--no-pager', '--property=Id,MainPID,ActiveState,SubState,Job,Result,ExecMainStatus']),
    startup_config_sha256=digest(business / 'startup/config.json'),
    saved_listening=listening,
    camera_health=health(8790, '/health'),
    gui_state=health(8783, '/api/state'),
    dpu_user_pids=sorted(dpu_users),
    relevant_processes=sorted(processes, key=lambda value: value['pid']),
    project_imported=False, database_opened=False, audio_or_motion_requested=False)
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
