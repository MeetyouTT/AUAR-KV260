import hashlib
import http.client
import json
from pathlib import Path
import subprocess

B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
A=B/'runtime/aura';ROOT=Path('/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-aaaa15bf')
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
try:
    c.request('GET','/api/state');r=c.getresponse();assert r.status==200;state=json.loads(r.read(2097152))
finally:c.close()
pan=state['manual_pan'];report=Path(pan['face_follow']['report']);assert report.is_relative_to(ROOT/'runs')
files=[]
for p in sorted(report.parent.iterdir()) if report.parent.is_dir() else ():
    row=dict(name=p.name,bytes=p.stat().st_size)
    if p.is_file() and p.suffix in ('.log','.txt','.err','.out') and p.stat().st_size<24000:
        row['text']=p.read_text(errors='replace')
    files.append(row)
sources=[]
pins=json.loads((B/'startup/config.json').read_bytes())['component_sha256']
for name in pins:
    if name.endswith('.py'):
        p=A/name;text=p.read_text();needle='class FacePanProcess'
        if needle in text:
            start=text.index(needle);sources.append(dict(path=str(p),excerpt=text[start:start+20000]))
probe=subprocess.run(['python3','-B','-c',
    'import sys;sys.path.insert(0,'+repr(str(ROOT))+');import continuous_face_control;print("PURE_CORE_IMPORT_OK")'],
    capture_output=True,text=True,timeout=5)
out=dict(manual_pan=pan,run_directory_exists=report.parent.is_dir(),run_files=files,
    face_process_source=sources,state_keys=sorted(state),pure_core_import=dict(returncode=probe.returncode,stdout=probe.stdout,stderr=probe.stderr))
print(json.dumps(out))
