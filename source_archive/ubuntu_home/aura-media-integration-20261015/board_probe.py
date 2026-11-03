"""Read-only board inventory for the next audio integration milestone."""
import glob
import importlib.util
import json
from pathlib import Path
import subprocess
import urllib.request


def run(args):
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=6)
        return {'exit_code': p.returncode, 'output': p.stdout[-6000:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'error': str(exc)}


result = {'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          'uname': run(['uname', '-a']), 'addresses': run(['ip', '-j', 'address']),
          'route': run(['ip', 'route']), 'capture': run(['arecord', '-l']),
          'playback': run(['aplay', '-l']),
          'sound_cards': Path('/proc/asound/cards').read_text(),
          'sound_owners': run(['fuser'] + glob.glob('/dev/snd/pcm*')),
          'modules': {name: bool(importlib.util.find_spec(name))
                      for name in ('numpy', 'sherpa_onnx', 'gi')}}
result['services'] = run(['systemctl', 'show', 'aura-avatar-ui.service',
    'aura-camera-ui.service', '-p', 'Id', '-p', 'ActiveState', '-p', 'SubState',
    '-p', 'MainPID', '-p', 'NRestarts'])
for name, url in [('camera', 'http://127.0.0.1:8790/health'),
                  ('ui', 'http://127.0.0.1:8783/api/state')]:
    try:
        with urllib.request.urlopen(url, timeout=4) as response:
            state = json.load(response)
        if name == 'ui':
            state = {key: state.get(key) for key in
                     ('phase', 'playing', 'paused', 'ui_settings', 'error')}
        result[name] = state
    except Exception as exc:
        result[name] = {'error': str(exc)}
print(json.dumps(result, ensure_ascii=False))
