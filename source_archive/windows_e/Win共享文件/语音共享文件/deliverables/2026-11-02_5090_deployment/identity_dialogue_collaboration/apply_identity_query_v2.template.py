"""Root-reviewed single-component transaction. Default dry-run; never starts services."""
import argparse
import ast
import base64
import copy
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import stat
import subprocess
import time
import uuid

BOOT='903cfade-b93c-48fa-804e-379be1967313'
BUSINESS=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP=BUSINESS/'startup/config.json'
STARTUP_BEFORE='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
STARTUP_AFTER='0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f'
RELATIVE='tools/unified_identity_binding.py'
SOURCE_BEFORE='f083fe8b618f4b09dce1587b3c32bf47f92510948e728615ce989ef31a1757cf'
SOURCE_AFTER='85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809'
UI_SHA='fc21e6f2ef831442b08966957fa7aeb744a9b74124ee8778edc40397285626cd'
DEFAULT_SHA='e203e6ffe973397464791eb07f12e0bd0c24658988c119e9d7d75685c4e41986'
SELECTED=Path('/home/root/aura-5090-recovery-20261102-903cfade/gui-selected-1333-24pins-v1/face_gallery_readback.local.json')
SELECTED_SHA='4d8f0c2bccea1c7a56761fbcb204f40ba3b3c2fc9efad76af778aff535d378ac'
CAM_CMD='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
VERIFIER_SHA='b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e'
TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/identity-query-sampling-v2')
PAYLOAD_B64='__CANDIDATE_BASE64__'

def raw(path):
    path=Path(path)
    assert path.is_file() and not path.is_symlink() and path.suffix not in ('.db','.sqlite','.sqlite3')
    assert path.stat().st_size<=64000000
    return path.read_bytes()

def digest(path):return hashlib.sha256(raw(path)).hexdigest()

def owners():
    assert os.geteuid()==0
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    for name,expected in (
        ('aura-avatar-ui.service',{'MainPID':'0','ActiveState':'inactive','SubState':'dead','Job':''}),
        ('aura-camera-ui.service',{'MainPID':'1333','ActiveState':'active','SubState':'running','Job':''})):
        value=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job'],capture_output=True,text=True,timeout=5)
        assert value.returncode==0
        assert dict(line.split('=',1) for line in value.stdout.splitlines() if '=' in line)==expected
    proc=Path('/proc/1333')
    assert (proc/'stat').read_text().rsplit(')',1)[1].split()[19]=='2359'
    assert hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()==CAM_CMD
    assert json.loads(raw('/home/root/.local/share/aura-board-business/listening_preference.json'))=={'version':1,'enabled':False}

def health():
    connection=http.client.HTTPConnection('127.0.0.1',8790,timeout=3)
    try:
        connection.request('GET','/health');response=connection.getresponse();data=response.read(1048577)
        assert response.status==200 and len(data)<=1048576
        value=json.loads(data)
        assert value['board_boot_id']==BOOT and value['pid']==1333
        assert value['identity']['ready'] is True and not value['identity'].get('error')
        assert not any(value.get(k) for k in ('camera_error','detector_error','preview_error'))
        assert value['motion_command_emitted'] is False
        return {k:value[k] for k in ('pid','capture_frames','detected_frames','service_epoch','camera_epoch')}
    finally:connection.close()

def sync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def create(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    sync_dir(path.parent)

def replace(path,expected,data):
    info=path.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==0
    assert raw(path)==expected,'Concurrent production bytes changed'
    temporary=path.with_name('.'+path.name+'.identity-v2-'+uuid.uuid4().hex+'.tmp')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,stat.S_IMODE(info.st_mode))
    try:
        with os.fdopen(fd,'wb') as stream:
            os.fchmod(stream.fileno(),stat.S_IMODE(info.st_mode))
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        assert raw(path)==expected,'Concurrent production bytes changed'
        os.replace(temporary,path);sync_dir(path.parent)
        assert raw(path)==data
    finally:
        if temporary.exists():temporary.unlink()

parser=argparse.ArgumentParser()
parser.add_argument('--apply-identity-query-v2',action='store_true')
args=parser.parse_args()
owners();assert digest(STARTUP)==STARTUP_BEFORE
startup=json.loads(raw(STARTUP));AURA=Path(startup['runtime'])/'aura';SOURCE=AURA/RELATIVE
assert len(startup['component_sha256'])==380
assert startup['component_sha256'][RELATIVE]==SOURCE_BEFORE and digest(SOURCE)==SOURCE_BEFORE
assert all(digest(AURA/name)==sha for name,sha in startup['component_sha256'].items())
assert digest(AURA/'config/board_avatar_gtk.json')==UI_SHA
assert digest(AURA/'config/face_gallery_readback.local.json')==DEFAULT_SHA
assert digest(SELECTED)==SELECTED_SHA
assert json.loads(raw(AURA/'config/board_avatar_gtk.json'))['board_business']['face_readback']=={'path':str(SELECTED),'sha256':SELECTED_SHA}
binding=json.loads(raw(SELECTED));assert len(binding['source_sha256'])==24
assert all(digest(name)==sha for name,sha in binding['source_sha256'].items())
verifier=AURA/'board/runtime/audio/face_gallery_readback.py';assert digest(verifier)==VERIFIER_SHA
tree=ast.parse(raw(verifier).decode('utf-8'))
klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FaceGalleryReadback')
node=copy.deepcopy(next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_verify'));node.decorator_list=[]
space={'Path':Path,'hashlib':hashlib,'json':json}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(verifier)+'::<metadata-only-_verify>','exec'),space)
space['_verify'](binding)
first=health();time.sleep(.4);last=health()
assert last['capture_frames']>first['capture_frames'] and last['detected_frames']>first['detected_frames']
assert first['service_epoch']==last['service_epoch'] and first['camera_epoch']==last['camera_epoch']
payload=base64.b64decode(PAYLOAD_B64,validate=True);assert hashlib.sha256(payload).hexdigest()==SOURCE_AFTER
ast.parse(payload.decode('utf-8'))
new=copy.deepcopy(startup);new['component_sha256'][RELATIVE]=SOURCE_AFTER
assert [k for k,v in startup['component_sha256'].items() if new['component_sha256'][k]!=v]==[RELATIVE]
startup_after=(json.dumps(new,sort_keys=True,indent=2)+'\n').encode('utf-8')
assert hashlib.sha256(startup_after).hexdigest()==STARTUP_AFTER
before={SOURCE:raw(SOURCE),STARTUP:raw(STARTUP)};after={SOURCE:payload,STARTUP:startup_after}
assert not TX.exists() and not TX.is_symlink()
assert TX.parent.resolve(strict=True)==TX.parent and TX.parent.is_dir() and TX.parent.stat().st_uid==0
receipt={'schema':'aura-identity-query-single-component-transaction-2','status':'DRY_RUN_READY','boot_id':BOOT,
    'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'transaction_directory':str(TX),
    'source_before_sha256':SOURCE_BEFORE,'source_after_sha256':SOURCE_AFTER,
    'startup_before_sha256':STARTUP_BEFORE,'startup_after_sha256':STARTUP_AFTER,
    'changed_components':[RELATIVE],'component_count':380,'selected_binding_source_count':24,
    'gui_configuration_sha256':UI_SHA,'selected_binding_sha256':SELECTED_SHA,'camera_pid':1333,
    'services_started_or_stopped':False,'identity_config_or_database_changed':False,
    'model_or_recording_or_playback_or_motion_requested':False,'board_mutations':False}

def save_receipt():
    value=(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode('utf-8');path=TX/'transaction.json'
    if path.exists():replace(path,raw(path),value)
    else:create(path,value)

if not args.apply_identity_query_v2:
    print(json.dumps(receipt,sort_keys=True));raise SystemExit(0)
owners();assert raw(STARTUP)==before[STARTUP] and raw(SOURCE)==before[SOURCE]
TX.mkdir(mode=0o700);sync_dir(TX.parent)
receipt.update(status='PREPARED_BACKUPS_PENDING',board_mutations=True);save_receipt()
changed=[]
try:
    create(TX/'startup.before.json',before[STARTUP])
    create(TX/'unified_identity_binding.before.py',before[SOURCE])
    create(TX/'unified_identity_binding.after.py',payload)
    receipt['status']='BACKUPS_VERIFIED';save_receipt()
    for path in (SOURCE,STARTUP):
        owners();changed.append(path);replace(path,before[path],after[path])
        receipt['status']='SOURCE_WRITTEN_STARTUP_PENDING' if path==SOURCE else 'BOTH_WRITTEN';save_receipt()
    owners();assert digest(STARTUP)==STARTUP_AFTER
    assert all(digest(AURA/name)==sha for name,sha in new['component_sha256'].items())
    assert digest(AURA/'config/board_avatar_gtk.json')==UI_SHA
    assert digest(AURA/'config/face_gallery_readback.local.json')==DEFAULT_SHA
    assert digest(SELECTED)==SELECTED_SHA and all(digest(name)==sha for name,sha in binding['source_sha256'].items())
    space['_verify'](binding);post=health()
    assert post['capture_frames']>last['capture_frames'] and post['detected_frames']>last['detected_frames']
    assert post['service_epoch']==last['service_epoch'] and post['camera_epoch']==last['camera_epoch']
    receipt.update(status='IDENTITY_QUERY_V2_UPDATED_GUI_STILL_STOPPED',component_count_verified=380,
        selected_binding_verified=True,original_verifier_passed=True,camera_owner_unchanged=True,
        completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());save_receipt()
except BaseException as error:
    receipt.update(status='FAILED_ROLLBACK_PENDING',error_type=type(error).__name__);rollback=[]
    for path in reversed(changed):
        try:
            owners();actual=raw(path)
            if actual==after[path]:replace(path,after[path],before[path]);state='ORIGINAL_BYTES_RESTORED'
            elif actual==before[path]:state='ALREADY_ORIGINAL'
            else:raise RuntimeError('Concurrent bytes changed; rollback refused')
            rollback.append({'path':str(path),'status':state})
        except BaseException as failure:rollback.append({'path':str(path),'status':'ROLLBACK_REFUSED_OR_FAILED','error_type':type(failure).__name__})
    receipt['rollback']=rollback
    receipt['status']='FAILED_ORIGINAL_BYTES_RESTORED' if all(row['status'] in ('ORIGINAL_BYTES_RESTORED','ALREADY_ORIGINAL') for row in rollback) else 'FAILED_REQUIRES_RECONCILIATION'
    save_receipt();print(json.dumps(receipt,sort_keys=True),flush=True);raise
print(json.dumps(receipt,sort_keys=True))
