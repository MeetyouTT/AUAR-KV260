"""Stage an isolated runtime from the actual automatic-dialogue baseline."""
import ast,hashlib,json,os,shutil,subprocess,zipfile
from pathlib import Path
assert os.uname().machine=='aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
ROOT=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
archive=ROOT/'runtime.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='858950aebbc11e1fd44f87f31b212455be6c519b3ee581ea249d81af107457c3'
old=Path(subprocess.run(['systemctl','show','aura-avatar-ui.service','-p','WorkingDirectory','--value'],stdout=subprocess.PIPE,text=True,check=True,timeout=5).stdout.strip()).resolve()
assert str(old).startswith('/home/root/aura-automatic-conversation-') and old.name=='aura'
current=old.parent.parent
new=ROOT/'candidate'
assert not new.exists(),'Use a new immutable candidate'
shutil.copytree(current,new)
app=new/'runtime/aura'
with zipfile.ZipFile(archive) as z:
 manifest=json.loads(z.read('manifest.json'))
 assert set(z.namelist())=={'aura/'+r['path'] for r in manifest['files']}|{'manifest.json'}
 for row in manifest['files']:
  rel=Path(row['path']);assert not rel.is_absolute() and '..' not in rel.parts
  data=z.read('aura/'+row['path']);assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
  if rel.suffix=='.py':ast.parse(data.decode(),filename=str(rel))
  target=app/rel;target.parent.mkdir(parents=True,exist_ok=True);assert not target.is_symlink();target.write_bytes(data)
model=app/'models/vision/yunet_2022mar.onnx'
if not model.exists():
 model.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile('/home/root/aura-adaptation-20261006/identity/models/yunet_2022mar.onnx',model)
assert hashlib.sha256(model.read_bytes()).hexdigest()=='50ef07f702a31741ca46a4c0d947773b64143b9362780237bf0d427d6c79bab7'
protected=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura/config/board_camera_ui.json')
config=json.loads(protected.read_text());config['identity']={'enabled':True,'config':'config/board_identity.dpu_engineering.json'}
(app/'config/board_camera_ui.json').write_text(json.dumps(config,indent=2)+'\n')
config=json.loads((app/'config/board_avatar_gtk.json').read_text());assert config['automatic_turns'] and config['persistent_audio'] and config['streaming_conversation']
config['voice_identity_enrollment']=False
(app/'config/board_avatar_gtk.json').write_text(json.dumps(config,indent=2)+'\n')
for path in (new/'startup').rglob('*'):
 if path.is_file() and path.suffix in ('.json','.py'):
  text=path.read_text();path.write_text(text.replace(str(current),str(new)))
for unit in ['aura-camera-ui.service','aura-avatar-ui.service']:
 text=Path('/etc/systemd/system',unit).read_text()
 if unit=='aura-avatar-ui.service':text=text.replace(str(current),str(new))
 else:text=text.replace('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura',str(app))
 (ROOT/(unit+'.candidate')).write_text(text)
(ROOT/'staged-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'status':'STAGED_NOT_ENABLED','candidate_root':str(new),'active_baseline':str(current),'files_verified':len(manifest['files']),'voice_identity_enabled':False,'dpu_config':str(app/'config/board_identity.dpu_engineering.json'),'production_services_changed':False}),flush=True)
