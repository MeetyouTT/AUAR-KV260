"""Read model health and backend implementation references only."""
import json, subprocess, urllib.request
from pathlib import Path
out={}
pid=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
args=Path('/proc/'+pid+'/cmdline').read_bytes().decode().strip('\0').split('\0')
root=next(Path(a).parent.parent for a in args if a.endswith('.py'))
try:
    with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=5) as r:d=json.load(r)
    out['health']={k:d.get(k) for k in ['ready','pid','detection_hz','detector_backend','identity_recognition','identity_ready','identity_error','camera_error','detector_error','identity_backend'] if k in d}
    out['health_keys']=list(d)
except Exception as e:out['health_error']=str(e)
out['backend_sources']=[]
for p in (root/'board').rglob('*.py'):
    if 'identity' not in str(p).lower():continue
    lines=p.read_text().splitlines()
    for i,line in enumerate(lines):
        if any(s in line for s in ['windows_sface','feature_backend','FaceDetectorYN','FaceRecognizerSF','/v1/identity','/api/identity','/identity/features']):
            out['backend_sources'].append({'file':str(p.relative_to(root)),'line':i+1,'text':line.strip()})
out['backend_sources']=out['backend_sources'][:30]
print(json.dumps(out),flush=True)
