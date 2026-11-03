"""Version and select the three reviewed changes in the original Ubuntu follower."""
import base64
import copy
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import stat
import time
import uuid

CHANGES=json.loads(base64.b64decode('PAYLOAD_BASE64'))
EXPECTED=json.loads(base64.b64decode('EXPECTED_BASE64'))
BOOT='903cfade-b93c-48fa-804e-379be1967313'
BUSINESS=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
AURA=BUSINESS/'runtime/aura';STARTUP=BUSINESS/'startup/config.json';FACE=AURA/'config/pan_face.local.json'
OLD=Path('/home/root/aura-pan-wide-20261028/control-10282601-target45-9adb90c3')
NEW=OLD.with_name('control-10282601-left40-right45-aaaa15bf')
TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-follow-left40-right45-v1')
OWNERS=((97308,'2694906','48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),
        (97312,'2695022','bb612bf74a9fefd8528337b6d907298563a3c7abe1703b53e54db32971fef121'),
        (79866,'2265436','acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'))
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
def replace_file(path,expected,data):
    st=path.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_uid==0
    assert raw(path)==expected
    tmp=path.with_name('.'+path.name+'.left40-'+uuid.uuid4().hex+'.tmp')
    create(tmp,data,stat.S_IMODE(st.st_mode));assert raw(path)==expected
    os.replace(tmp,path);sync(path.parent)
def owners():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert sha('/sys/firmware/fdt')=='d68bc147f22f5ab23bc60f0c2762af4bcd7b64340953e9c948e28ffa6b80f7ca'
    for pid,birth,cmd in OWNERS:
        p=Path('/proc')/str(pid)
        assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==birth and sha(p/'cmdline')==cmd
def request(kind=None):
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
    try:
        if kind:c.request('POST','/api/command',json.dumps({'type':kind}).encode(),
            {'Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783','Content-Type':'application/json'})
        else:c.request('GET','/api/state')
        r=c.getresponse();body=r.read(2097153);assert r.status==200 and len(body)<=2097152
        return json.loads(body)
    finally:c.close()
def stopped():
    pan=request()['manual_pan'];rb=pan.get('readback') or {}
    assert pan.get('automatic_following') is False and pan.get('state')=='READY' and not pan.get('error')
    assert rb.get('flags')==0 and rb.get('lease_left_ms')==0 and rb.get('reason')==0
    return dict(state=pan['state'],following=pan['automatic_following'],readback=rb,
                face_follow=pan.get('face_follow'),backend_pid=pan.get('backend_pid'))

owners()
assert sha(STARTUP)=='bcb773cd5bf306ac536df0373d1c1b27d01b6564a35839f2623b274442c13a59'
assert sha(FACE)=='775fa3c5d5f694ff8d9eadffb03fe7180935812cc4ab8b55eaa70105a0be66ed'
startup=json.loads(raw(STARTUP));pins=startup['component_sha256']
assert len(pins)==380 and all(sha(AURA/key)==value for key,value in pins.items())
before={FACE:raw(FACE),STARTUP:raw(STARTUP)}
face=json.loads(before[FACE]);assert face['release_root']==str(OLD)
assert sha(OLD/'deployment-manifest.json')==face['manifest_sha256']=='cfe36df907fc195b083cbf6b44c7e120cbf613324e821c626bac169ad77a5d8b'
zone=Path(face['arguments']['zone-settings']);zone_before=raw(zone)
assert digest(zone_before)=='815fb333ad60137c93d2147ab14574903556b551d15cad5621320ba94cdfd4e3'
zone_value=json.loads(zone_before)
assert zone_value['left_camera_ratio']==.05 and zone_value['right_ratio']==.7158253629442671
assert zone_value['target_center_ratio']==.5 and zone_value['center_tolerance_ratio']==.03
manifest=json.loads(raw(OLD/'deployment-manifest.json'));assert len(manifest['files'])==25
payload={};candidate_manifest=copy.deepcopy(manifest)
for old,item in zip(manifest['files'],candidate_manifest['files']):
    source=Path(old['destination']);relative=source.relative_to(OLD);name=relative.as_posix()
    assert not relative.is_absolute() and '..' not in relative.parts and name not in payload
    data=raw(source);assert digest(data)==old['sha256']==EXPECTED[name]['before'] and len(data)==old['bytes']
    if name in CHANGES:data=base64.b64decode(CHANGES[name])
    assert digest(data)==EXPECTED[name]['after']
    payload[name]=data;item.update(destination=str(NEW/relative),sha256=digest(data),bytes=len(data))
assert sorted(name for name,data in payload.items() if digest(data)!=sha(OLD/name))==sorted(CHANGES)
assert len(CHANGES)==3 and set(CHANGES)=={'run_face_motion.py','continuous_face_control.py','continuous_session.py'}
candidate_manifest['scope']=manifest['scope']+'; optional left stop target latched by original trigger side; left 0.40 / right 0.45'
manifest_bytes=enc(candidate_manifest);manifest_sha=digest(manifest_bytes)
new_face=copy.deepcopy(face);new_face.update(release_root=str(NEW),manifest_sha256=manifest_sha)
new_face['arguments']['target-center-ratio']='0.45';new_face['arguments']['left-target-center-ratio']='0.40'
predecessor={'root':str(OLD),'sha256':face['manifest_sha256']}
assert predecessor not in new_face.get('stopped_readback_predecessors',[])
new_face.setdefault('stopped_readback_predecessors',[]).insert(0,predecessor)
new_startup=copy.deepcopy(startup);new_startup['component_sha256']['config/pan_face.local.json']=digest(enc(new_face))
after={FACE:enc(new_face),STARTUP:enc(new_startup)}
assert {k:v for k,v in new_startup.items() if k!='component_sha256'}=={k:v for k,v in startup.items() if k!='component_sha256'}
assert [k for k,v in pins.items() if new_startup['component_sha256'][k]!=v]==['config/pan_face.local.json']
assert not TX.exists() and not NEW.exists()
request('pan_stop')
end=time.monotonic()+12
while True:
    try:before_stop=stopped();break
    except AssertionError:
        assert time.monotonic()<end
        time.sleep(.25)
owners()
assert raw(FACE)==before[FACE] and raw(STARTUP)==before[STARTUP] and raw(zone)==zone_before
TX.mkdir(mode=0o700);NEW.mkdir(mode=0o700);sync(TX.parent);sync(NEW.parent)
create(TX/'startup.before.json',before[STARTUP]);create(TX/'pan_face.before.json',before[FACE])
create(TX/'original-deployment-manifest.json',raw(OLD/'deployment-manifest.json'))
create(TX/'stop-before.json',enc(before_stop))
create(TX/'publication-intent.json',enc(dict(new_root=str(NEW),source_changes=sorted(CHANGES),left_target=.4,right_target=.45)))
for name,data in payload.items():
    destination=NEW/name;destination.parent.mkdir(parents=True,exist_ok=True)
    assert destination.parent.resolve().is_relative_to(NEW.resolve())
    create(destination,data,stat.S_IMODE((OLD/name).stat().st_mode))
create(NEW/'deployment-manifest.json',manifest_bytes)
for name in CHANGES:compile(payload[name],str(NEW/name),'exec')
assert all(sha(item['destination'])==item['sha256'] for item in candidate_manifest['files'])
changed=[]
try:
    owners();stopped()
    assert raw(zone)==zone_before and all(sha(AURA/key)==value for key,value in pins.items())
    for path,data in after.items():changed.append(path);replace_file(path,before[path],data)
    assert all(sha(AURA/key)==value for key,value in new_startup['component_sha256'].items())
    assert all(sha(item['destination'])==item['sha256'] for item in candidate_manifest['files'])
    assert all(sha(item['destination'])==item['sha256'] for item in manifest['files'])
    assert sha(OLD/'deployment-manifest.json')==face['manifest_sha256'] and raw(zone)==zone_before
    owners();last_stop=stopped()
    result=dict(status='ORIGINAL_FOLLOW_LEFT40_RIGHT45_SELECTED_STOPPED',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        boot_id=BOOT,controller_root=str(NEW),controller_manifest_sha256=manifest_sha,
        changed_sources={name:digest(payload[name]) for name in CHANGES},source_files_changed=3,unchanged_source_files=22,
        components_verified=380,selected_files_verified=25,changed_component_keys=['config/pan_face.local.json'],
        startup_before_sha256=digest(before[STARTUP]),startup_after_sha256=digest(after[STARTUP]),face_config_sha256=digest(after[FACE]),
        left_stop_target_center_ratio=.4,right_stop_target_center_ratio=.45,center_tolerance_ratio=.03,
        left_stop_band=[.37,.43],right_stop_band=[.42,.48],white_line_center_ratio=.5,zone_sha256=digest(zone_before),
        trigger_settings_changed=False,old_controller_preserved=True,old_stop_receipt_predecessor_preserved=True,
        gui_restarted=False,camera_restarted=False,models_changed=False,explicit_stop_once=True,motion_start_sent=False,
        before_stop=before_stop,after_stop=last_stop,transaction_root=str(TX))
    create(TX/'transaction.json',enc(result))
except BaseException:
    for path in reversed(changed):
        if raw(path)==after[path]:replace_file(path,after[path],before[path])
    raise
print(json.dumps(result))
