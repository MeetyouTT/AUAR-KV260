import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
before=json.loads((HERE/'BASELINE_PREPARED.json').read_text(encoding='utf-8'))['component_pins']
code='BEFORE = '+repr(before)+'\n'+r'''
import datetime,hashlib,json
from pathlib import Path
path=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
raw=path.read_bytes();startup=json.loads(raw);aura=Path(startup['runtime'])/'aura'
diff=[];invalid=[]
for key,sha in startup['component_sha256'].items():
    actual=hashlib.sha256((aura/key).read_bytes()).hexdigest()
    if actual!=sha:invalid.append(key)
    if BEFORE.get(key)!=sha:diff.append({'key':key,'old':BEFORE.get(key),'new':sha,'actual':actual,
        'mtime_utc':datetime.datetime.fromtimestamp((aura/key).stat().st_mtime,datetime.timezone.utc).isoformat()})
recent=[]
root=Path('/home/root/aura-5090-recovery-20261102-903cfade')
for child in root.iterdir():
    if child.stat().st_mtime>1793612000:
        recent.append({'name':child.name,'mtime_utc':datetime.datetime.fromtimestamp(child.stat().st_mtime,datetime.timezone.utc).isoformat()})
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'startup_sha256':hashlib.sha256(raw).hexdigest(),
    'components':len(startup['component_sha256']),'changed_components':diff,'invalid_components':invalid,
    'recent_recovery_entries':recent,'read_only':True}))
'''
helper=HERE.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('source_change_transport',helper)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
value=json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=15))
with (HERE/'SOURCE_CHANGE_RECONCILE.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(value))
