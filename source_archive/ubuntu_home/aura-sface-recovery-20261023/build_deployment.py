"""Seal only recovery sources and owned runtime-promotion controller."""
import ast,base64,gzip,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
names=['board/vision/'+name for name in ('dpu_vision_schedule.py','dpu_sface.py','ui_camera_service.py','dpu_protection_handoff.py')]
files={};pins={}
for name in names:
    p=ROOT/'candidate/aura'/name;raw=p.read_bytes();ast.parse(raw)
    key=str(p.relative_to(ROOT));digest=hashlib.sha256(raw).hexdigest()
    files[key]={'sha256':digest,'base64':base64.b64encode(raw).decode()};pins[name]=digest
for name in ('deploy_control.py','protected_rollback_entry.py','baseline-manifest.json'):
    raw=(ROOT/name).read_bytes()
    if name.endswith('.py'):ast.parse(raw)
    files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
data=json.dumps(files,sort_keys=True,separators=(',',':')).encode()
body='''import ast,base64,gzip,hashlib,json,subprocess,sys
from pathlib import Path
assert not sys.flags.optimize
sys.dont_write_bytecode=True
source=Path(sys._getframe().f_code.co_filename).resolve()
digest=hashlib.sha256(source.read_bytes()).hexdigest()
root=Path('/home/root/aura-sface-recovery-20261023/promotion')/digest[:16]
root.mkdir(parents=True,exist_ok=True,mode=0o700)
data=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(data).hexdigest()==PAYLOAD_SHA
for name,meta in json.loads(data).items():
 p=root/name;assert '..' not in Path(name).parts and root in p.parents
 raw=base64.b64decode(meta['base64']);assert hashlib.sha256(raw).hexdigest()==meta['sha256']
 p.parent.mkdir(parents=True,exist_ok=True);assert p.parent.resolve()==p.parent and not p.is_symlink()
 if p.exists():assert p.read_bytes()==raw
 else:
  with p.open('xb') as f:f.write(raw)
assert sys.argv[1:] in ([],['--run'],['--guard'],['--restore'])
if sys.argv[1:]:
 sys.path.insert(0,str(root));from deploy_control import run
 print(json.dumps(run(root,source,PINS,guard=sys.argv[1:] in (['--guard'],['--restore']),manual=sys.argv[1:]==['--restore'])))
else:
 assert not (root/'report.json').exists()
 unit='aura-sface-recovery-promotion-'+root.name
 subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=300',
  '--setenv=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
  '/usr/bin/python3','-B',str(source),'--run'],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 print(json.dumps({'started':True,'unit':unit,'report':str(root/'report.json'),'helper_sha256':digest}))
'''
out=ROOT/'board_promote.py'
out.write_text('PAYLOAD='+repr(base64.b64encode(gzip.compress(data,mtime=0)).decode())+'\nPAYLOAD_SHA='+repr(hashlib.sha256(data).hexdigest())+'\nPINS='+repr(pins)+'\n'+body)
ast.parse(out.read_text())
(ROOT/'deployment-manifest.json').write_text(json.dumps({'helper_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'candidate_pins':pins,'sources':{k:v['sha256'] for k,v in files.items()},'scope':'SAME_BOOT_RUNTIME_DROP_IN_ONLY'},indent=2)+'\n')
print(json.dumps({'bytes':out.stat().st_size,'files':len(files),'changed_runtime_files':len(pins)}))
