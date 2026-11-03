"""Inspect the current GUI and failed camera startup without changing them."""
import json
import os
import subprocess
import urllib.request
from pathlib import Path


def run(args):
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=8, env=dict(os.environ, DISPLAY=':0'))
        return {'exit_code': p.returncode, 'output': p.stdout[-12000:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'error': str(exc)}


result = {
    'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'camera_unit': run(['systemctl', 'cat', 'aura-camera-ui.service']),
    'camera_journal': run(['journalctl', '-b', '-u', 'aura-camera-ui.service', '-n', '30', '--no-pager']),
    'camera_owners': run(['fuser', '/dev/video0']),
    'display': run(['xrandr', '--current']),
    'windows': run(['xwininfo', '-root', '-tree']),
}
with urllib.request.urlopen('http://127.0.0.1:8783/api/state', timeout=4) as f:
    state = json.load(f)
result['ui'] = {k: state.get(k) for k in ['ui_page', 'ui_layer', 'error', 'ui_runtime', 'avatar_renderer']}
print(json.dumps(result, ensure_ascii=False))
