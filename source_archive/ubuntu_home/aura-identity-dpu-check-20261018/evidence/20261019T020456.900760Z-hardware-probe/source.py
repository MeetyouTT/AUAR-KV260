"""Read hardware/runtime availability without inference, capture or deployment."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import urllib.request

assert os.uname().machine == 'aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
out = {'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
       'vart': importlib.util.find_spec('vart') is not None,
       'xir': importlib.util.find_spec('xir') is not None}
p = subprocess.run(['xdputil', 'query'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=8)
out['xdputil_exit'] = p.returncode
out['xdputil_query'] = json.loads(p.stdout)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for kind, port, route in [('camera', 8790, '/health'), ('ui', 8783, '/api/state')]:
    try:
        with opener.open('http://127.0.0.1:%d%s' % (port, route), timeout=3) as response:
            s = json.load(response)
        fields = ('pid', 'service_epoch', 'capture_frames', 'detected_frames', 'detection_hz', 'observation_age_ms', 'last_inference_ms', 'identity_recognition') if kind == 'camera' else ('ui_page', 'phase', 'playing', 'paused')
        out[kind] = {k: s.get(k) for k in fields}
    except Exception as exc:
        out[kind] = {'error_type': type(exc).__name__}
out['inference_or_camera_capture_requested'] = False
print(json.dumps(out))
