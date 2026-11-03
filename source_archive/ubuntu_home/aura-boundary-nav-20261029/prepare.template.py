import base64,hashlib,json,os,shutil,subprocess,urllib.request
from pathlib import Path
BOOT='55152f95-ea3a-4c6c-82e6-51bd553d96fd'
OLD=Path('/home/root/aura-pan-wide-resume-20261029/gui-wide-v1')
G=Path('/home/root/aura-boundary-nav-20261029/gui-page-sync-v1')
E=Path('/home/root/aura-boundary-nav-20261029/editor-page-sync-v1')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as f:return json.load(f)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert sha(OLD/'startup/config.json')=='431fb21d93b410bfb55fbb8c41482cb82a0edbcaf91b8ca08b18c48bda4a875f'
startup=json.loads((OLD/'startup/config.json').read_text());A=Path(startup['runtime'])/'aura'
assert all(sha(A/n)==v for n,v in startup['component_sha256'].items())
assert sha(A/'tools/board_avatar_gtk.py')=='c91b13145bb4d49f95324b516a8eeacfe9f4801715fea8cf613d614208e09ed8'
u=get(8783,'/api/state');h=get(8790,'/health')
assert u['phase']=='IDLE' and not u['playing'] and u['audio_output_state']=='IDLE_READY'
assert not u['manual_pan']['automatic_following'] and u['manual_pan']['state']=='READY' and u['manual_pan']['readback']['flags']==0
assert not u['handsfree_dialogue']['enabled']
assert not G.exists() and not E.exists();G.mkdir(parents=True);E.mkdir()
(G/'runtime').mkdir();(G/'startup').mkdir()
def clone(src,dst):
 for p in src.iterdir():
  if p.name in {'stage.log','managed-runs','launch.json','__pycache__'} or p.suffix=='.pyc':continue
  q=dst/p.name
  if p.is_symlink():
   if p.name=='config' and p.is_dir():q.mkdir();clone(p.resolve(),q)
   else:q.symlink_to(p.resolve(strict=True),target_is_directory=p.is_dir())
  elif p.is_dir():q.mkdir();clone(p,q)
  else:shutil.copy2(p,q)
clone(OLD/'runtime',G/'runtime');NEW=G/'runtime/aura'
assert (NEW/'tools').resolve()==NEW/'tools'
for n,b64 in PAYLOAD.items():
 raw=base64.b64decode(b64);assert hashlib.sha256(raw).hexdigest()==PINS[n]
 if n=='face_zone_editor.py':dest=E/n
 elif n=='boundary_visibility.py':
  (E/n).write_bytes(raw);dest=NEW/'tools'/n
 else:dest=NEW/'tools'/n
 if dest.is_symlink():dest.unlink()
 dest.write_bytes(raw)
startup['runtime']=str(G/'runtime')
for n in ['tools/board_avatar_gtk.py','tools/boundary_visibility.py']:startup['component_sha256'][n]=sha(NEW/n)
assert all(sha(NEW/n)==v for n,v in startup['component_sha256'].items())
shutil.copy2(OLD/'startup/launcher.py',G/'startup/launcher.py');(G/'startup/config.json').write_text(json.dumps(startup,indent=2)+'\n')
manual=json.loads((A/'config/pan_manual.local.json').read_text());face=json.loads(Path(manual['face_follow_config']).read_text());settings=Path(face['arguments']['zone-settings'])
old_settings=Path('/home/root/aura-pan-current-20261024/da36c36a/face-zone-settings.json')
current=json.loads(settings.read_text());visible=json.loads(old_settings.read_text())
geometry=['left_camera_ratio','right_ratio','target_center_ratio','recenter_on_edge','viewport','frame_width','frame_height']
assert all(current.get(k)==visible.get(k) for k in geometry),'Boundary geometry differs; preserve before deciding merge'
env=dict(os.environ,PYTHONPATH=str(NEW),PYTHONDONTWRITEBYTECODE='1')
p=subprocess.run(['/usr/bin/python3','-B',str(G/'startup/launcher.py'),'--config',str(G/'startup/config.json'),'--preflight'],env=env,capture_output=True,text=True,timeout=30);assert p.returncode==0,p.stderr[-1000:]
assert all(sha(A/n)==v for n,v in json.loads((OLD/'startup/config.json').read_text())['component_sha256'].items())
state={'phase':'PREPARED','boot_id':BOOT,'old_gui':str(OLD),'gui':str(G),'editor':str(E),'editor_settings':str(settings),'settings_sha256':sha(settings),'old_editor_settings':str(old_settings),'old_editor_settings_sha256':sha(old_settings),'old_editor_unit_sha256':sha('/etc/systemd/system/aura-face-zone-editor.service'),'gui_config_sha256':sha(G/'startup/config.json'),'camera_pid':h['pid'],'gui_pid':int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)),'components':len(startup['component_sha256']),'preserved_components':len(startup['component_sha256'])-2,'payload_pins':PINS,'motion_commands':0}
(G.parent/'state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state))
