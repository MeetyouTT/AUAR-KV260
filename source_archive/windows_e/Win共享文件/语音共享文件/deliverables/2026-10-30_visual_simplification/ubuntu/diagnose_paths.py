"""Confirm stale pointers and return only relevant public source/config evidence."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess

pid = subprocess.check_output(['systemctl','show','aura-avatar-ui.service',
                               '-p','MainPID','--value'],text=True).strip()
args = (Path('/proc')/pid/'cmdline').read_bytes().decode().split('\0')
config_path = Path(args[args.index('--config')+1])
config = json.loads(config_path.read_text())
root = Path(config['runtime'])
launcher = next(Path(a) for a in args[:args.index('--config')] if a.endswith('.py'))
files = {'launcher.py':launcher,
         'device_observer.py':root/'aura/board/runtime/device_observer.py',
         'board_avatar_gtk.py':root/'aura/tools/board_avatar_gtk.py'}
sources = {}
for name,path in files.items():
    raw = path.read_bytes()
    sources[name] = dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),
                         base64=base64.b64encode(raw).decode())
links = []
for parent,dirs,files in os.walk(root,followlinks=False):
    dirs[:] = [d for d in dirs if d not in ('managed-runs','__pycache__')]
    for name in dirs+files:
        path = Path(parent)/name
        if path.is_symlink():
            links.append(dict(path=str(path.relative_to(root)),target=os.readlink(path)))
print(json.dumps(dict(actual_runtime=str(root),sources=sources,symlinks=links,
                     root_entries=sorted(p.name for p in root.iterdir()),readonly=True)))
