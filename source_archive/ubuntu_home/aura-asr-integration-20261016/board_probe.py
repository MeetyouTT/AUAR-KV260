"""Read-only ASR integration prerequisites on the current board."""
import glob
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import urllib.request

def run(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
    return {'code':p.returncode,'output':p.stdout[-3000:]}
result={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'machine':platform.machine(),'python':platform.python_version(),
        'addresses':run(['ip','-j','address']),'route':run(['ip','route']),
        'memory':run(['free','-m']),
        'dependencies':{key:bool(importlib.util.find_spec(key)) for key in ('numpy','sherpa_onnx','onnxruntime')},
        'models':[]}
root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
for folder in (root/'aura/models/asr',Path('/home/root/models/asr')):
    if folder.exists():result['models'] += [str(p) for p in folder.rglob('*') if p.suffix in ('.onnx','.txt')]
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as r:state=json.load(r)
result['ui']={k:state.get(k) for k in ('ui_page','ui_layer','phase','playing','paused','error','local_recording','ui_settings')}
print(json.dumps(result,ensure_ascii=False))
