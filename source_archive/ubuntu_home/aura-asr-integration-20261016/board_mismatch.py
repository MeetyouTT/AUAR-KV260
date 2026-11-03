"""Read the installed startup manifest and mismatching source; no mutations."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
config=json.loads(Path('/home/root/aura-ui-startup-20261009/releases/dc3fb02b00f4783b/config.json').read_text())
rows={};artifacts={}
for rel,expected in config['component_sha256'].items():
    data=(ROOT/'aura'/rel).read_bytes();actual=hashlib.sha256(data).hexdigest()
    if actual!=expected:
        rows[rel]={'expected':expected,'actual':actual}
        name=rel.replace('/','__')
        artifacts[name]={'bytes':len(data),'sha256':actual,'base64':base64.b64encode(data).decode()}
print(json.dumps({'mismatches':rows,'services':subprocess.check_output(['systemctl','show',
    'aura-avatar-ui.service','aura-camera-ui.service','-p','Id','-p','ActiveState','-p','MainPID',
    '-p','SubState','-p','NRestarts'],text=True),'journal':subprocess.check_output(['journalctl','-u',
    'aura-avatar-ui.service','-n','12','--no-pager','-o','cat'],text=True),'artifacts':artifacts}))
