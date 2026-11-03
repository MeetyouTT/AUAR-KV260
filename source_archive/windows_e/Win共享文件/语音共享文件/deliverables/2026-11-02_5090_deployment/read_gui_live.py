"""Read service and filtered health metadata; no device or business actions."""
import datetime
import http.client
import json
from pathlib import Path
import subprocess

def get(port, path):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        raw = response.read(1048577)
        assert len(raw) <= 1048576
        value = json.loads(raw)
        keys = ('ready', 'ok', 'status', 'page', 'presentation_state', 'avatar_visible',
                'pid', 'board_boot_id', 'capture_frames', 'detected_frames',
                'camera_error', 'detector_error', 'preview_error', 'motion_command_emitted')
        return {'http_status': response.status,
                'metadata': {key:value[key] for key in keys if key in value}}
    except (OSError, ValueError, http.client.HTTPException) as error:
        return {'error_type': type(error).__name__}
    finally:
        connection.close()

units = subprocess.run(['systemctl', 'show', 'aura-avatar-ui.service', 'aura-camera-ui.service',
    '--property=Id,ActiveState,SubState,MainPID,Result,ExecMainStatus,Job'],
    capture_output=True, text=True, timeout=6)
preference = json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())
assert set(preference) == {'version', 'enabled'}
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'units':units.stdout, 'units_exit_code':units.returncode,
    'saved_listening':preference['enabled'], 'gui_api':get(8783, '/api/state'),
    'camera':get(8790, '/health'), 'mutation_requested':False}))
