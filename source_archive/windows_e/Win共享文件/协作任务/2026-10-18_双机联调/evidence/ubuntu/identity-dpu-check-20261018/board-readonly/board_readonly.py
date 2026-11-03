"""Read active runtime and health; never request recording or deployment."""
import json
import os
from pathlib import Path
import subprocess
import urllib.request

assert os.uname().machine == 'aarch64', 'Unexpected machine'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100', 'Unexpected SD card'
out = {'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
for name in ('aura-avatar-ui.service', 'aura-camera-ui.service'):
    p = subprocess.run(['systemctl', 'show', name, '-p', 'MainPID', '-p', 'ActiveState', '-p', 'FragmentPath'], stdout=subprocess.PIPE, timeout=5)
    info = dict(line.split('=', 1) for line in p.stdout.decode().splitlines() if '=' in line)
    pid = info.get('MainPID', '0')
    if pid.isdigit() and int(pid):
        proc = Path('/proc')/pid
        info['cwd'] = str((proc/'cwd').resolve())
        args = (proc/'cmdline').read_bytes().decode().split('\0')
        info['python_sources'] = [a for a in args if a.endswith('.py')]
    out[name] = info
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for name, port, route in [('ui', 8783, '/api/state'), ('camera', 8790, '/health')]:
    try:
        with opener.open('http://127.0.0.1:%d%s' % (port, route), timeout=4) as reply:
            state = json.load(reply)
        if name == 'ui':
            value = {k: state.get(k) for k in ('ui_layer', 'ui_page', 'phase', 'playing', 'paused')}
            for key in ('local_recording', 'local_transcription'):
                part = state.get(key) or {}
                value[key] = {k: part.get(k) for k in ('state', 'can_start', 'sample_count')}
        else:
            value = {k: state.get(k) for k in ('pid', 'service_epoch', 'capture_frames', 'detected_frames', 'detection_hz', 'observation_age_ms', 'last_inference_ms', 'role', 'identity_recognition')}
        out[name] = value
    except Exception as exc:
        out[name] = {'error_type': type(exc).__name__}
out['recording_or_deployment_requested'] = False
print(json.dumps(out, ensure_ascii=False))
