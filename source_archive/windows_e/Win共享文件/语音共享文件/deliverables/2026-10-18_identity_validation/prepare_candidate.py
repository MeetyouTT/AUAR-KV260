"""Isolate identity code/tests without opening a second camera or user DB."""
import base64
import hashlib
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

names=['aura/board/identity/__init__.py','aura/board/identity/store.py',
 'aura/board/identity/live.py','aura/board/identity/camera_faces.py',
 'aura/board/vision/reference_faces.py','aura/board/vision/ui_camera_service.py',
 'aura/board/interaction/ui_contract.py','aura/config/board_identity.json',
 'aura/tools/check_board_identity.py']
names += ['aura/tests/framework/'+n for n in ('test_camera_identity.py','test_camera_ui_service.py','test_board_ui_services.py')]
payload={name:base64.b64encode((ROOT/name).read_bytes()).decode() for name in names}
release=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:12]
remote=r'''
import base64,hashlib,json,os,re,shutil,subprocess,urllib.request
from pathlib import Path
p=PAYLOAD
def get(port,path):return json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=5))
health=get(8790,'/health');pid=health['pid'];source=Path('/proc/%d/cwd'%pid).resolve().parent
assert str(source).startswith('/home/root/') and (source/'aura/config/board_camera_ui.json').is_file()
old_config=json.loads((source/'aura/config/board_camera_ui.json').read_text())
config=dict(old_config);config['identity']={'enabled':True,'config':'config/board_identity.json'}
stage=Path('/home/root/aura-identity-validation-20261018')/('candidate-'+p['release'])
stage.mkdir(parents=True,exist_ok=False);runtime=stage/'runtime';runtime.mkdir()
changes={name:base64.b64decode(raw,validate=True) for name,raw in p['files'].items()}
changes['aura/config/board_camera_ui.json']=(json.dumps(config,indent=2)+'\n').encode()
for package in ('tools','board','common','host'):
 for path in (source/'aura'/package).rglob('*.py'):
  changes.setdefault(str(path.relative_to(source)),path.read_bytes())
def overlay(src,dst,prefix=''):
 dst.mkdir(parents=True,exist_ok=True)
 for item in src.iterdir():
  name=prefix+item.name;target=dst/item.name
  if name in changes:target.write_bytes(changes[name])
  elif any(key.startswith(name+'/') for key in changes):overlay(item,target,name+'/')
  else:target.symlink_to(item,target_is_directory=item.is_dir())
overlay(source,runtime)
for name,raw in changes.items():
 target=runtime/name
 if target.exists():continue
 target.parent.mkdir(parents=True,exist_ok=True)
 assert target.parent.resolve()==runtime.resolve() or runtime.resolve() in target.parent.resolve().parents
 target.write_bytes(raw)
for name in changes:
 if name.endswith('.py'):compile((runtime/name).read_bytes(),str(runtime/name),'exec')
# Test modules must be local, never written through the source runtime symlink.
tests=stage/'tests';tests.mkdir()
for name,raw in changes.items():
 if name.startswith('aura/tests/framework/'): (tests/Path(name).name).write_bytes(raw)
environment=dict(os.environ,PYTHONPATH=str(runtime/'aura'),PYTHONDONTWRITEBYTECODE='1')
run=subprocess.run(['python3','-B','-m','unittest','discover','-s',str(tests),'-v'],cwd=runtime/'aura',env=environment,capture_output=True,text=True,timeout=90)
(stage/'tests_board.log').write_text(run.stdout+run.stderr)
checks={}
for model in ('yunet_2022mar.onnx','sface_2021dec.onnx'):
 path=runtime/'aura/models/vision'/model
 checks[model]={'exists':path.is_file(),'resolved':str(path.resolve())}
 if path.is_file():checks[model].update(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
result={'stage':str(stage),'runtime':str(runtime),'source_runtime':str(source),
 'tests_passed':run.returncode==0,'old_camera_config':old_config,'candidate_camera_config':config,
 'models':checks,'files':{n:hashlib.sha256((runtime/n).read_bytes()).hexdigest() for n in p['files']},
 'camera_config_sha256':hashlib.sha256((runtime/'aura/config/board_camera_ui.json').read_bytes()).hexdigest(),
 'camera_before':health,'activated':False,'user_database_opened':False,'test_log':run.stdout+run.stderr}
(stage/'candidate.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('PAYLOAD',repr({'release':release,'files':payload}))
result=json.loads(ssh('python3 -',remote,timeout=140))
(HERE/'candidate.json').write_text(json.dumps({k:v for k,v in result.items() if k!='test_log'},ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'tests_board.log').write_text(result['test_log'],encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('test_log','camera_before','old_camera_config','candidate_camera_config')},ensure_ascii=True))
assert result['tests_passed'],result['test_log'][-5000:]
