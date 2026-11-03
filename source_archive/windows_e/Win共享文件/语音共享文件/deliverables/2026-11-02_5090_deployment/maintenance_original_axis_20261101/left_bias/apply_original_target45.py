"""Version the original follower with one target option and select it in GUI."""
import base64
import copy
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import stat
import uuid

CANDIDATE=base64.b64decode('CANDIDATE_BASE64')
assert hashlib.sha256(CANDIDATE).hexdigest()=='9adb90c31efbf9c57d5e60f497c429bfcb3523be04ea6503d37552cfba3d4be9'
BOOT='903cfade-b93c-48fa-804e-379be1967313'
BUSINESS=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
AURA=BUSINESS/'runtime/aura';STARTUP=BUSINESS/'startup/config.json'
FACE=AURA/'config/pan_face.local.json'
OLD=Path('/home/root/aura-pan-wide-20261028/control-10282601')
NEW=OLD.with_name('control-10282601-target45-9adb90c3')
TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-follow-target45-v1')

def raw(path):
    p=Path(path);assert p.is_file() and not p.is_symlink() and p.stat().st_size<64000000
    assert p.suffix not in ('.db','.sqlite','.sqlite3')
    return p.read_bytes()
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(path):return digest(raw(path))
def enc(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def sync(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def create(path,data,mode=0o600):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    sync(path.parent)
def replace(path,expected,data):
    st=path.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_uid==0
    assert raw(path)==expected
    tmp=path.with_name('.'+path.name+'.target45-'+uuid.uuid4().hex+'.tmp')
    create(tmp,data,stat.S_IMODE(st.st_mode))
    assert raw(path)==expected
    os.replace(tmp,path);sync(path.parent)
def stopped_gui():
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
    try:
        c.request('GET','/api/state');r=c.getresponse();body=r.read(2097153)
        assert r.status==200 and len(body)<=2097152
        value=json.loads(body);pan=value['manual_pan'];rb=pan.get('readback') or {}
        assert pan.get('automatic_following') is False and pan.get('state')=='READY' and not pan.get('error')
        assert rb.get('flags')==0 and rb.get('lease_left_ms')==0
        return rb
    finally:c.close()

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert sha(STARTUP)=='092c2ccf0872cae2f6e13c81e2d8b8a2ffe3b0800ab701566128b5c7947159af'
for pid,birth in ((97308,'2694906'),(97312,'2695022'),(79866,'2265436')):
    assert (Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19]==birth
startup=json.loads(raw(STARTUP));pins=startup['component_sha256']
assert len(pins)==380 and all(sha(AURA/key)==value for key,value in pins.items())
before={FACE:raw(FACE),STARTUP:raw(STARTUP)}
face=json.loads(before[FACE]);assert face['release_root']==str(OLD)
assert sha(OLD/'deployment-manifest.json')==face['manifest_sha256']=='5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562'
zone=Path(face['arguments']['zone-settings']);zone_before=raw(zone)
assert json.loads(zone_before)['target_center_ratio']==.5
manifest=json.loads(raw(OLD/'deployment-manifest.json'));assert len(manifest['files'])==25
payload={};candidate_manifest=copy.deepcopy(manifest)
for old,item in zip(manifest['files'],candidate_manifest['files']):
    source=Path(old['destination']);relative=source.relative_to(OLD)
    assert not relative.is_absolute() and '..' not in relative.parts and str(relative) not in payload
    data=raw(source);assert digest(data)==old['sha256'] and len(data)==old['bytes']
    if str(relative)=='run_face_motion.py':data=CANDIDATE
    payload[str(relative)]=data
    item.update(destination=str(NEW/relative),sha256=digest(data),bytes=len(data))
assert [name for name,data in payload.items() if digest(data)!=sha(OLD/name)]==['run_face_motion.py']
candidate_manifest['scope']=manifest['scope']+'; optional target-center-ratio, legacy default 0.5'
manifest_bytes=enc(candidate_manifest);manifest_sha=digest(manifest_bytes)
new_face=copy.deepcopy(face);new_face.update(release_root=str(NEW),manifest_sha256=manifest_sha)
new_face['arguments']['target-center-ratio']='0.45'
predecessor={'root':str(OLD),'sha256':face['manifest_sha256']}
assert predecessor not in new_face.get('stopped_readback_predecessors',[])
new_face.setdefault('stopped_readback_predecessors',[]).insert(0,predecessor)
new_startup=copy.deepcopy(startup);new_startup['component_sha256']['config/pan_face.local.json']=digest(enc(new_face))
after={FACE:enc(new_face),STARTUP:enc(new_startup)}
assert {k:v for k,v in new_startup.items() if k!='component_sha256'}=={k:v for k,v in startup.items() if k!='component_sha256'}
assert [k for k,v in pins.items() if new_startup['component_sha256'][k]!=v]==['config/pan_face.local.json']
assert not TX.exists() and not NEW.exists()
before_stop=stopped_gui()
TX.mkdir(mode=0o700);NEW.mkdir(mode=0o700);sync(TX.parent);sync(NEW.parent)
create(TX/'startup.before.json',before[STARTUP]);create(TX/'pan_face.before.json',before[FACE])
create(TX/'original-deployment-manifest.json',raw(OLD/'deployment-manifest.json'))
for name,data in payload.items():
    destination=NEW/name;destination.parent.mkdir(parents=True,exist_ok=True)
    assert destination.parent.resolve().is_relative_to(NEW.resolve())
    create(destination,data,stat.S_IMODE((OLD/name).stat().st_mode))
create(NEW/'deployment-manifest.json',manifest_bytes)
assert all(sha(item['destination'])==item['sha256'] for item in candidate_manifest['files'])
compile(CANDIDATE,str(NEW/'run_face_motion.py'),'exec')
assert raw(zone)==zone_before
changed=[]
try:
    stopped_gui()
    for path,data in after.items():changed.append(path);replace(path,before[path],data)
    assert all(sha(AURA/key)==value for key,value in new_startup['component_sha256'].items())
    assert all(sha(item['destination'])==item['sha256'] for item in candidate_manifest['files'])
    assert sha(OLD/'deployment-manifest.json')==face['manifest_sha256']
    assert raw(zone)==zone_before and json.loads(raw(zone))['target_center_ratio']==.5
    last_stop=stopped_gui()
except BaseException:
    for path in reversed(changed):
        if raw(path)==after[path]:replace(path,after[path],before[path])
    raise
result={'status':'ORIGINAL_FOLLOW_TARGET45_SELECTED_STOPPED','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'boot_id':BOOT,'controller_root':str(NEW),'controller_manifest_sha256':manifest_sha,
    'entry_sha256':digest(CANDIDATE),'source_files_changed':1,'unchanged_source_files':24,'components_verified':380,
    'changed_component_keys':['config/pan_face.local.json'],'startup_before_sha256':digest(before[STARTUP]),
    'startup_after_sha256':digest(after[STARTUP]),'face_config_sha256':digest(after[FACE]),
    'stop_target_center_ratio':.45,'center_tolerance_ratio':.03,'stop_band':[.42,.48],
    'white_line_center_ratio':.5,'white_line_and_zone_unchanged':True,'zone_sha256':digest(zone_before),
    'old_controller_preserved':True,'old_stop_receipt_predecessor_preserved':True,
    'gui_restarted':False,'camera_restarted':False,'models_changed':False,'hardware_commands_sent':False,
    'before_stop':before_stop,'after_stop':last_stop}
create(TX/'transaction.json',enc(result));print(json.dumps(result))
