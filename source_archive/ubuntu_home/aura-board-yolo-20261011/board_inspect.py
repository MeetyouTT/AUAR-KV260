import importlib.util
import json
import os
from pathlib import Path
import subprocess
import urllib.request

def run(args, timeout=18):
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return {'rc': p.returncode, 'output': p.stdout[:16000]}
    except Exception as exc:
        return {'error': type(exc).__name__ + ': ' + str(exc)}

models = []
for root in ['/usr/share/vitis_ai_library/models', '/home/root', '/run/media']:
    for directory, folders, files in os.walk(root):
        if directory.count('/') - root.count('/') >= 7:
            folders[:] = []
        folders[:] = [d for d in folders if d not in ['.cache', '.git', 'managed-runs', 'backup', 'proc', 'sys', 'dev']]
        for name in files:
            if name.endswith(('.xmodel', '.onnx')):
                p = Path(directory) / name
                models.append({'path': str(p), 'bytes': p.stat().st_size})
        if len(models) > 120:
            break

processes = []
for p in Path('/proc').iterdir():
    if not p.name.isdigit() or int(p.name) == os.getpid():
        continue
    try:
        args = (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
        if any(s in args for s in ['yolo', 'resnet', 'vision.py', 'ui_camera_service', 'board_avatar_gtk', 'dfx-mgrd', 'Xorg']):
            processes.append({'pid': int(p.name), 'argv': args[:350]})
    except OSError:
        pass
result = {'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'models': models,
    'modules': {s: bool(importlib.util.find_spec(s)) for s in ['vart', 'xir', 'vitis_ai_library', 'numpy', 'cv2', 'onnxruntime', 'torch']},
    'dpu': run(['xdputil', 'query']), 'apps': run(['xmutil', 'listapps']),
    'network': run(['ip', '-4', 'addr']), 'routes': run(['ip', 'route']),
    'mounts': run(['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT']), 'processes': processes}
for name, url in [('camera', 'http://127.0.0.1:8790/health'), ('ui', 'http://127.0.0.1:8783/api/state')]:
    try:
        with urllib.request.urlopen(url, timeout=4) as response:
            value = json.load(response)
        result[name] = value if name == 'camera' else {k: value[k] for k in ['phase', 'playing', 'paused', 'ui_settings']}
    except Exception as exc:
        result[name] = {'error': str(exc)}
print(json.dumps(result, ensure_ascii=False))
