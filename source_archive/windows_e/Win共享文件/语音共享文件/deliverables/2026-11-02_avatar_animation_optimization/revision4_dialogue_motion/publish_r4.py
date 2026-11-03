"""CAS only five reviewed animation components; GUI remains stopped."""
from pathlib import Path
import json,hashlib,subprocess,os,stat,copy,argparse
HERE=Path(__file__).resolve().parent;E=json.loads((HERE/'expected.json').read_bytes());M=json.loads((HERE/'release/MANIFEST.json').read_bytes())
P=Path(E['startup_path']);R=Path(E['runtime'])
NAMES={'tools/libaura_yuki.so','config/yuki_pair.formal.json','tools/formal_yuki.py','config/board_avatar_gtk.json','tools/native_yuki.py'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def create(p,raw,mode=0o600,uid=None,gid=None):
 assert p.parent.resolve()==p.parent
 fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,mode)
 try:
  os.fchmod(fd,mode)
  if uid is not None:os.fchown(fd,uid,gid)
  with os.fdopen(fd,'wb',closefd=False) as f:f.write(raw);f.flush();os.fsync(f.fileno())
 finally:os.close(fd)
def save(p,x):create(p,(json.dumps(x,sort_keys=True,indent=2)+'\n').encode())
def directory_sync(p):
 fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def guard():
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==E['boot_id']
 def unit(n):
  s=subprocess.check_output(['systemctl','show',n,'--property=MainPID,ActiveState,SubState,Job']).decode();return dict(x.split('=',1) for x in s.splitlines() if '=' in x)
 g=unit('aura-avatar-ui.service');assert g['MainPID']=='0' and g['ActiveState']=='inactive' and g['SubState']=='dead' and not g['Job']
 c=unit('aura-camera-ui.service');p=Path('/proc')/str(E['camera_owner']['pid'])
 assert c['MainPID']==str(E['camera_owner']['pid']) and c['ActiveState']=='active' and not c['Job']
 assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==E['camera_owner']['birth_ticks'] and sha(p/'cmdline')==E['camera_owner']['command_sha256']
 stop=json.loads((HERE/'STOP_RESULT_original.json').read_bytes());assert stop['status']=='GUI_NORMAL_STOPPED' and stop['original_properties_restored']
 assert json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())==stop['saved_listening']
def main():
 p=argparse.ArgumentParser();p.add_argument('--rollback',action='store_true');a=p.parse_args();guard()
 assert set(M['components'])==NAMES and M['total_components']==380
 quality=json.loads((HERE/'release/QUALITY_GATE.json').read_bytes());assert quality['release_gate_passed'] is True
 raw=P.read_bytes();cfg=json.loads(raw);assert len(cfg['component_sha256'])==380
 expected_start=M['startup_after'] if a.rollback else M['startup_before'];assert hashlib.sha256(raw).hexdigest()==expected_start
 assert all(sha(R/k)==h for k,h in cfg['component_sha256'].items())
 desired=(HERE/'backup/startup.json').read_bytes() if a.rollback else (HERE/'release/startup.after.json').read_bytes()
 new=json.loads(desired);assert set(k for k in cfg if k!='component_sha256')==set(k for k in new if k!='component_sha256')
 assert all(cfg[k]==v for k,v in new.items() if k!='component_sha256')
 assert {k for k,v in cfg['component_sha256'].items() if new['component_sha256'][k]!=v}==NAMES
 changes=[]
 for name,row in M['components'].items():
  target=R/name;assert target.resolve()==target and not target.is_symlink()
  before=row['after_sha256'] if a.rollback else row['before_sha256'];after=row['before_sha256'] if a.rollback else row['after_sha256']
  source=HERE/'backup'/name if a.rollback else HERE/'release/runtime'/name
  assert sha(target)==before and sha(source)==after
  if name.endswith('.py'):compile(source.read_bytes(),str(target),'exec')
  metadata=target.stat();changes.append((name,target,source.read_bytes(),metadata,before,after))
 name='ROLLBACK' if a.rollback else 'PUBLICATION'
 save(HERE/(name+'_INTENT.json'),dict(startup_before=sha(P),startup_after=hashlib.sha256(desired).hexdigest(),files={n:{'before':b,'after':v} for n,t,x,m,b,v in changes},camera_owner=E['camera_owner'],GUI_stopped=True))
 for n,target,data,metadata,before,after in changes:
  guard();assert sha(target)==before and P.read_bytes()==raw
  tmp=target.with_name(target.name+'.avatar-R4-'+HERE.name+'.tmp')
  create(tmp,data,stat.S_IMODE(metadata.st_mode),metadata.st_uid,metadata.st_gid)
  assert sha(target)==before;os.replace(tmp,target);directory_sync(target.parent)
  save(HERE/(name+'_'+n.replace('/','_')+'.json'),dict(name=n,before=before,after=sha(target)))
 guard();assert P.read_bytes()==raw
 tmp=P.with_name(P.name+'.avatar-R4-'+HERE.name+'.tmp');meta=P.stat();create(tmp,desired,stat.S_IMODE(meta.st_mode),meta.st_uid,meta.st_gid)
 assert P.read_bytes()==raw;os.replace(tmp,P);directory_sync(P.parent)
 assert all(sha(R/k)==h for k,h in new['component_sha256'].items());guard()
 result=dict(status='ANIMATION_ROLLED_BACK_GUI_STOPPED' if a.rollback else 'ANIMATION_R4_CAS_APPLIED_GUI_STOPPED',startup_before=hashlib.sha256(raw).hexdigest(),startup_after=sha(P),changed_components=M['components'],all_380_pins_match=True,other_375_components_unchanged=True,mode_uid_gid_preserved=True,original_camera_owner=E['camera_owner'],audio_eye_business_persona_data_axis_unchanged=True,GUI_started=False)
 save(HERE/(name+'.json'),result);print(json.dumps(result))
if __name__=='__main__':main()
