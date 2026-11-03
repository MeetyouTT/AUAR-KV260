import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import urllib.request

def get(port, endpoint):
    with urllib.request.urlopen('http://127.0.0.1:%s/%s' % (port, endpoint), timeout=4) as response:
        return json.load(response)

root = Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
health = get(8790, 'health')
ui = get(8783, 'api/state')
print(json.dumps({'boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'health': health, 'ui_settings': ui['ui_settings'], 'gui': json.loads((root/'launch.json').read_text()),
    'modules': {s: bool(importlib.util.find_spec(s)) for s in ['numpy','scipy','lap','cython_bbox','torch']},
    'numpy_probe': subprocess.check_output(['python3','-B','-c','import numpy as np;print(np.__version__);print(np.linalg.solve(np.eye(2),np.ones(2)))'],text=True),
    'model_config': Path('/usr/share/vitis_ai_library/models/yolox_nano_pt/yolox_nano_pt.prototxt').read_text(),
    'xmodel_sha256': hashlib.sha256(Path('/usr/share/vitis_ai_library/models/yolox_nano_pt/yolox_nano_pt.xmodel').read_bytes()).hexdigest()},ensure_ascii=False))
