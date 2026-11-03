"""Seal reviewed two-file candidate and bounded GUI-only trial controller."""
import ast,base64,gzip,hashlib,json,re
from pathlib import Path

HERE=Path(__file__).resolve().parent
names=('tools/board_avatar_gtk.py','tools/board_camera_preview.py')
real=json.loads((HERE/'real-gtk-result.json').read_text())['launch']
assert real['passed'] and real['worker_stopped']
pins={name:hashlib.sha256((HERE/'candidate/aura'/name).read_bytes()).hexdigest() for name in names}
assert real['candidate_pins']==pins
protocol_count=lifecycle_count=0
for name,count in (('lifecycle-tests.log',14),('trial-review-tests-final.log',9)):
    log=(HERE/'independent-review'/name).read_text()
    match=re.search(r'Ran (\d+) tests',log)
    assert match and int(match.group(1))>=count and log.rstrip().endswith('OK'),name
    if name.startswith('trial-'):protocol_count=int(match.group(1))
    else:lifecycle_count=int(match.group(1))
review=json.loads((HERE/'independent-review/trial-reviewed-manifest.json').read_text())
assert review['files']['gui_trial.py']==hashlib.sha256((HERE/'gui_trial.py').read_bytes()).hexdigest()
files={}
for name in names:
    raw=(HERE/'candidate/aura'/name).read_bytes();ast.parse(raw)
    files['candidate/aura/'+name]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
raw=(HERE/'gui_trial.py').read_bytes();ast.parse(raw)
files['gui_trial.py']={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
baseline=json.loads((HERE/'current-source-proof.json').read_text())['files']
raw=json.dumps({name:row['sha256'] for name,row in baseline.items()},sort_keys=True).encode()
files['baseline-pins.json']={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
data=json.dumps(files,sort_keys=True,separators=(',',':')).encode()
code='PAYLOAD='+repr(base64.b64encode(gzip.compress(data,mtime=0)).decode())+'\nPAYLOAD_SHA='+repr(hashlib.sha256(data).hexdigest())+'\nPINS='+repr(pins)+'\n'+'''
import ast,base64,gzip,hashlib,json,subprocess,sys
from pathlib import Path
assert not sys.flags.optimize
sys.dont_write_bytecode=True
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
wrapper=Path(sys._getframe().f_code.co_filename).resolve();digest=hashlib.sha256(wrapper.read_bytes()).hexdigest()
folder=Path('/home/root/aura-video-cpu-20261023')/digest[:16]
folder.mkdir(parents=True,exist_ok=True,mode=0o700);assert folder.resolve()==folder
data=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(data).hexdigest()==PAYLOAD_SHA
for name,record in json.loads(data).items():
 p=folder/name;assert '..' not in Path(name).parts and folder in p.parents
 raw=base64.b64decode(record['base64']);assert hashlib.sha256(raw).hexdigest()==record['sha256']
 if p.suffix=='.py':ast.parse(raw)
 p.parent.mkdir(parents=True,exist_ok=True);assert p.parent.resolve()==p.parent and not p.is_symlink()
 if p.exists():assert p.read_bytes()==raw
 else:
  with p.open('xb') as stream:stream.write(raw)
assert sys.argv[1:] in ([],['--run'])
assert not (folder/'report.json').exists(),'Never overwrite trial evidence'
if sys.argv[1:]==['--run']:
 sys.path.insert(0,str(folder));from gui_trial import run
 print(json.dumps(run(folder,wrapper,PINS)))
else:
 unit='aura-video-trial-'+digest[:16]
 result=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=420',
  '--setenv=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
  '/usr/bin/python3','-B',str(wrapper),'--run'],capture_output=True,text=True,timeout=10)
 assert result.returncode==0,result.stderr
 print(json.dumps({'started':True,'unit':unit,'report':str(folder/'report.json'),'helper_sha256':digest}))
'''
ast.parse(code);(HERE/'activate_gui.py').write_text(code)
(HERE/'activation-manifest.json').write_text(json.dumps({'helper_sha256':hashlib.sha256(code.encode()).hexdigest(),
    'payload_sha256':hashlib.sha256(data).hexdigest(),'candidate_pins':pins,'controller_sha256':files['gui_trial.py']['sha256'],
    'real_gtk_checks':5,'software_lifecycle_tests':lifecycle_count,'protocol_tests':protocol_count,'deployed':False},indent=2)+'\n')
print(json.dumps({'helper_sha256':hashlib.sha256(code.encode()).hexdigest(),'bytes':len(code)}))
