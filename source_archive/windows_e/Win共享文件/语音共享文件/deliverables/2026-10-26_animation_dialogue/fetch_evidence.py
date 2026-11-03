"""Fetch an explicit list of small test reports and Python sources, never models."""
import base64, hashlib, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
names=['tests.xml','renderer_retry.xml','deployment.json','startup/launcher.py','startup/config.json','guardian.py']
names+=['runtime/aura/'+name for name in c['changes']]
script=r'''
import base64,hashlib,json
from pathlib import Path
stage=Path(STAGE);names=NAMES;data={}
for name in names:
    target=stage/name
    assert target.resolve().is_relative_to(stage.resolve()),name
    raw=target.read_bytes();assert len(raw)<2_000_000,name
    data[name]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
print(json.dumps(data))
'''.replace('STAGE',repr(c['stage'])).replace('NAMES',repr(names))
data=json.loads(ssh('python3 -B -',script,timeout=30));manifest=[]
for name,item in data.items():
    raw=base64.b64decode(item['base64']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
    dest=HERE/'board_evidence'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    if name=='deployment.json':(HERE/name).write_bytes(raw)
    manifest.append({'path':dest.relative_to(HERE).as_posix(),'sha256':item['sha256'],'bytes':len(raw)})
(HERE/'board_evidence_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'files':len(manifest),'bytes':sum(item['bytes'] for item in manifest)}))
