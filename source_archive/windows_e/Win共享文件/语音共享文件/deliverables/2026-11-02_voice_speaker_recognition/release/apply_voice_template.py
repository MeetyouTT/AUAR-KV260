"""CAS only the two reviewed voice sources and their original startup pins."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

E=None  # VOICE_CAS_EXPECTED

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def unit(name):
    r=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job,Restart,KillMode,SendSIGKILL,TimeoutStopUSec'],capture_output=True,text=True,timeout=4);assert r.returncode==0
    return dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
def owner(v):
    p=Path('/proc')/str(v['pid']);assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==v['birth_ticks'];assert sha(p/'cmdline')==v['command_sha256']
def create(p,data,mode=0o600):
    fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    sync(p.parent)
def sync(p):
    fd=os.open(str(p),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def camera():
    owner(E['camera_owner']);u=unit('aura-camera-ui.service');assert u['MainPID']==str(E['camera_owner']['pid']) and u['ActiveState']=='active' and not u['Job'];assert sha(E['camera_config']['path'])==E['camera_config']['sha256']

assert isinstance(E,dict) and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==E['boot_id']
tx=Path(E['stop_transaction']);stop=json.loads((tx/'stop-result.json').read_bytes());assert stop['status']=='GUI_NORMAL_STOPPED' and stop['original_GUI_stop_properties_restored'] is True
u=unit('aura-avatar-ui.service');assert u['MainPID']=='0' and u['ActiveState']=='inactive' and u['SubState']=='dead' and not u['Job'];assert {k:u[k] for k in E['original_GUI_properties']}==E['original_GUI_properties'];camera()
p=Path(E['startup_path']);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==E['startup_before_sha256'];cfg=json.loads(raw);aura=Path(cfg['runtime'])/'aura';pins=cfg['component_sha256'];assert pins==E['component_sha256'] and len(pins)==380 and all(sha(aura/k)==v for k,v in pins.items())
rows=[]
for row in E['payload']:
    path=aura/row['path'];assert path.is_file() and not path.is_symlink() and path.resolve()==path
    old=path.read_bytes();assert hashlib.sha256(old).hexdigest()==row['before_sha256']==pins[row['path']]
    new=base64.b64decode(row['content_base64']);assert hashlib.sha256(new).hexdigest()==row['after_sha256'];compile(new,str(path),'exec');rows.append((row,path,old,new,stat.S_IMODE(path.stat().st_mode)))
assert {r[0]['path'] for r in rows}=={'board/runtime/board_speaker_business.py','board/runtime/board_dialogue.py'}
updated=copy.deepcopy(cfg)
for row,_,_,_,_ in rows:updated['component_sha256'][row['path']]=row['after_sha256']
newraw=(json.dumps(updated,sort_keys=True,indent=2)+'\n').encode();assert hashlib.sha256(newraw).hexdigest()==E['startup_after_sha256']
create(tx/'voice-apply-intent.json',(json.dumps({'single_CAS':True,'mono_ms':int(time.monotonic()*1000),'startup_before':E['startup_before_sha256'],'startup_after':E['startup_after_sha256'],'files':[{k:v for k,v in row.items() if k!='content_base64'} for row,_,_,_,_ in rows]},sort_keys=True,indent=2)+'\n').encode())
create(tx/'voice-startup.before.json',raw)
for i,(_,_,old,_,_) in enumerate(rows):create(tx/('voice-source-'+str(i)+'.before.py'),old)
for row,path,old,new,mode in rows:
    assert path.read_bytes()==old;temp=path.with_name(path.name+'.'+tx.name+'.tmp');create(temp,new,mode);assert path.read_bytes()==old;os.replace(temp,path);sync(path.parent)
assert p.read_bytes()==raw;temp=p.with_name(p.name+'.'+tx.name+'.tmp');create(temp,newraw,stat.S_IMODE(p.stat().st_mode));assert p.read_bytes()==raw;os.replace(temp,p);sync(p.parent)
assert sha(p)==E['startup_after_sha256'] and all(sha(aura/k)==v for k,v in updated['component_sha256'].items())
assert all(updated['component_sha256'][k]==v for k,v in pins.items() if k not in {row['path'] for row,_,_,_,_ in rows});camera();assert unit('aura-avatar-ui.service')['MainPID']=='0'
result={'schema':'aura-per-utterance-voice-CAS-result-1','status':'TWO_VOICE_FILES_AND_STARTUP_PINS_APPLIED_GUI_STOPPED','startup_before_sha256':E['startup_before_sha256'],'startup_sha256':E['startup_after_sha256'],'changed_files':[{k:v for k,v in row.items() if k!='content_base64'} for row,_,_,_,_ in rows],'other378_actual_components_preserved':True,'R4_animation_components_preserved':True,'camera_owner_unchanged':True,'models_thresholds_identity_stores_axis_or_boot_changed':False,'transaction':str(tx)}
create(tx/'voice-applied.json',(json.dumps(result,sort_keys=True,indent=2)+'\n').encode());print(json.dumps(result))
