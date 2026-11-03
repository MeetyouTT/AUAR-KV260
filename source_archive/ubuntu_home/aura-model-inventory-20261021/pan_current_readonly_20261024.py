"""Cached motion status only; never opens transport/MMIO or issues movement."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.request

op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port, path):
    with op.open('http://127.0.0.1:'+str(port)+path, timeout=3) as response:
        return json.load(response)
gui = get(8783, '/api/state'); h = get(8790, '/health'); s = h['dpu_schedule']
root = Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce/runtime/aura')
files = ['board/motion/manual.py', 'board/motion/manual_process.py',
         'board/motion/manual_vsrv.py', 'config/board_avatar_ui.json']
print(json.dumps(dict(scope='CACHED_API_AND_SOURCE_HASH_READ_ONLY_NO_MOTION_OR_MMIO',
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), mono_ns=time.monotonic_ns(),
    manual_pan=gui.get('manual_pan'), gui={k:gui.get(k) for k in ['phase','ui_page','playing']},
    camera=dict(pid=h['pid'], frames=h['detected_frames'], yolo_hz=h['detection_hz'],
        native_critical=s.get('native_critical'), owner_fenced=s['owner_fenced'],
        primary_overruns=s['primary_period_overruns'],
        optional_overruns={k:v['overruns'] for k,v in s['optional'].items()},
        face_worker_alive=h['identity']['face_targets']['worker_alive']),
    motion_source_sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
        for name in files if (root/name).is_file()},
    services=subprocess.check_output(['systemctl','show','aura-camera-ui.service',
        'aura-avatar-ui.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'], text=True))))
