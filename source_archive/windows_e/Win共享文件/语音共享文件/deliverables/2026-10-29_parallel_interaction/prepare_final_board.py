"""Stage only the reviewed thin identity bridge over the actual pinned runtime."""
import base64,hashlib,json,sys,time
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];S=H.parent/'2026-10-29_speaker_visual_cooperation/board_bridge'
sys.path.insert(0,str(H.parent/'2026-10-29_audio_animation_polish'))
from board_guard import capture,same,ssh
b=capture();assert b['safe'] and not b['mismatches'];time.sleep(.6);same(b,capture())
(H/'board_preflight.json').write_text(json.dumps(b,indent=2),encoding='utf-8')
manifest=json.loads((S/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'));manifest=manifest.get('files',manifest)
changes={}
for name,item in manifest.items():
    raw=(S/'candidate'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['sha256']
    changes[name]=base64.b64encode(raw).decode()
assert len(changes)==9
script=r'''
import base64,hashlib,json,os,shutil,subprocess,uuid
from pathlib import Path
b=BASE;source=Path(b['actual_runtime']);changes=CHANGES
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==b['boot']
assert json.loads(Path(b['pending_config']).read_text())==b['pending']
assert b['pending']['runtime']==str(source) and b['pending']['component_sha256']==b['pins']
assert hashlib.sha256(Path(b['pending_launcher']).read_bytes()).hexdigest()==b['pending_launcher_sha256']
for name,digest in b['pins'].items():assert hashlib.sha256((source/'aura'/name).read_bytes()).hexdigest()==digest,name
stage=Path('/home/root/aura-identity-bridge-20261030')/uuid.uuid4().hex;stage.mkdir(parents=True)
root=stage/'runtime';files={}
for package in ('tools','board','common','host'):
 for path in (source/'aura'/package).rglob('*.py'):files['aura/'+path.relative_to(source/'aura').as_posix()]=path.read_bytes()
for path in (source/'aura/config').rglob('*'):
 if path.is_file():files['aura/config/'+path.relative_to(source/'aura/config').as_posix()]=path.read_bytes()
for name,data in changes.items():files['aura/'+name]=base64.b64decode(data)
def clone(src,dst,prefix=''):
 dst.mkdir()
 for item in src.iterdir():
  relative=prefix+item.name;target=dst/item.name
  if item.name=='__pycache__' or not prefix and item.name in ('managed-runs','launch.json','stage.log'):continue
  if relative in files:target.write_bytes(files[relative])
  elif any(name.startswith(relative+'/') for name in files):clone(item,target,relative+'/')
  elif not prefix and item.name.endswith('_settings.json'):shutil.copy2(item,target)
  else:target.symlink_to(item,target_is_directory=item.is_dir())
clone(source,root)
for name,data in files.items():
 path=root/name
 if not path.exists():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
(root/'managed-runs').mkdir()
startup=stage/'startup';startup.mkdir();shutil.copy2(b['pending_launcher'],startup/'launcher.py')
cfg=dict(b['pending']);cfg['runtime']=str(root);pins=dict(b['pins'])
for name in changes:pins[name]=hashlib.sha256((root/'aura'/name).read_bytes()).hexdigest()
cfg['component_sha256']=pins;(startup/'config.json').write_text(json.dumps(cfg,indent=2))
for name,digest in b['pins'].items():
 if name not in changes:assert hashlib.sha256((root/'aura'/name).read_bytes()).hexdigest()==digest,name
assert len(pins)==len(b['pins'])+7
assert hashlib.sha256((root/'aura/config/pan_manual.local.json').read_bytes()).hexdigest()==b['mechanical_sha256']
assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*_settings.json')}==b['settings']
pre=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],
 env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=30)
assert pre.returncode==0,pre.stdout+pre.stderr
for name in changes:
 if name.endswith('.py'):compile((root/'aura'/name).read_bytes(),name,'exec')
value=dict(status='STAGED',stage=str(stage),runtime=str(root),startup=str(startup),source_runtime=str(source),
 boot=b['boot'],pins=pins,changed_components=sorted(changes),preflight=pre.stdout.strip(),
 mechanical_sha256=b['mechanical_sha256'],next_start_launcher_preserved=True,
 launcher_sha256=b['pending_launcher_sha256'],production_changed=False,portrait_configuration_unchanged=True)
(stage/'candidate.json').write_text(json.dumps(value,indent=2));print(json.dumps(value))
'''.replace('BASE',repr(b)).replace('CHANGES',repr(changes))
v=json.loads(ssh('python3 -B -',script,timeout=100));(H/'board_candidate.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
print(json.dumps({k:v[k] for k in ('status','runtime','changed_components','next_start_launcher_preserved','production_changed')}))
