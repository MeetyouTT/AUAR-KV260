"""Refresh a verified camera owner binding while business remains stopped."""
import ast
import copy
import datetime
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

BOOT='903cfade-b93c-48fa-804e-379be1967313'
ROOT=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP=ROOT/'startup/config.json'
if os.geteuid()!=0 or Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT:
    raise RuntimeError('Expected the authorized current board boot')
lock_fd=os.open('/run/lock/aura-5090-recovery-903cfade.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
fcntl.flock(lock_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
unit=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState,Job'],capture_output=True,text=True,timeout=5)
fields=dict(line.split('=',1) for line in unit.stdout.splitlines() if '=' in line)
if unit.returncode or fields.get('MainPID')!='0' or fields.get('Job') or fields.get('ActiveState') not in ('inactive','failed'):
    raise RuntimeError('Business GUI must remain stopped')
if json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes()).get('enabled') is not False:
    raise RuntimeError('Saved listening must remain paused')
startup_before=STARTUP.read_bytes()
if hashlib.sha256(startup_before).hexdigest()!='ec12fccfdd3e8446e9c761e161167e00187e6fcf90372aa7e52c9865cc23c56f':
    raise RuntimeError('Startup configuration changed since the reviewed baseline')
startup=json.loads(startup_before);aura=Path(startup['runtime'])/'aura'
relative='config/face_gallery_readback.local.json';path=aura/relative
before=path.read_bytes();config=json.loads(before)
components=startup['component_sha256']
if len(components)!=380 or any(hashlib.sha256((aura/name).read_bytes()).hexdigest()!=expected for name,expected in components.items()):
    raise RuntimeError('Installed source closure changed')
if components.get(relative)!=hashlib.sha256(before).hexdigest():
    raise RuntimeError('Readback configuration is not in the original source closure')

def health():
    connection=http.client.HTTPConnection('127.0.0.1',8790,timeout=2)
    try:
        connection.request('GET','/health');response=connection.getresponse();raw=response.read(1048577)
        if response.status!=200 or len(raw)>1048576:raise RuntimeError('Camera health is not available')
        return json.loads(raw)
    finally:connection.close()

first=health();time.sleep(1);last=health()
for key in ('pid','board_boot_id','service_epoch','camera_epoch'):
    if first.get(key) is None or first[key]!=last.get(key):raise RuntimeError('Camera source changed during verification')
if (last['board_boot_id']!=BOOT or last['capture_frames']<=first['capture_frames']
        or last['detected_frames']<=first['detected_frames']
        or last.get('capture_age_ms',99999)>2000 or last.get('observation_age_ms',99999)>2000
        or last.get('identity',{}).get('ready') is not True
        or any(last.get(name) for name in ('camera_error','detector_error','preview_error'))
        or last.get('motion_command_emitted') is not False):
    raise RuntimeError('Fresh camera/identity progress is not verified')
process=Path('/proc')/str(last['pid'])
birth=process.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]
command_sha=hashlib.sha256(process.joinpath('cmdline').read_bytes()).hexdigest()
if command_sha!=config['camera_cmdline_sha256']:raise RuntimeError('Camera command differs from the original pinned command')
candidate=dict(config,board_boot_id=BOOT,camera_pid=last['pid'],camera_start_ticks=birth)

# Run only the installed, closure-verified read-only verifier. Importing the
# project or reading the private gallery is unnecessary for this owner refresh.
source=ast.parse((aura/'board/runtime/audio/face_gallery_readback.py').read_text())
klass=next(node for node in source.body if isinstance(node,ast.ClassDef) and node.name=='FaceGalleryReadback')
function=copy.deepcopy(next(node for node in klass.body if isinstance(node,ast.FunctionDef) and node.name=='_verify'))
function.decorator_list=[]
namespace=dict(Path=Path,hashlib=hashlib,json=json)
exec(compile(ast.Module(body=[function],type_ignores=[]),'<installed-read-only-verifier>','exec'),namespace)
verify=namespace['_verify'];verify(candidate)
backup=Path('/home/root/aura-5090-recovery-20261102-903cfade')/('readback-before-'+str(time.time_ns()))
backup.mkdir(parents=True,mode=0o700)
(backup/'face_gallery_readback.local.json').write_bytes(before)
(backup/'startup_config.json').write_bytes(startup_before)

def atomic(target,raw):
    info=target.stat();temporary=target.with_name(target.name+'.5090-'+uuid.uuid4().hex)
    fd=os.open(str(temporary),os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,info.st_mode&0o777)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.chown(str(temporary),info.st_uid,info.st_gid);os.replace(str(temporary),str(target))

candidate_raw=(json.dumps(candidate,sort_keys=True,indent=2)+'\n').encode()
updated=copy.deepcopy(startup);updated['component_sha256'][relative]=hashlib.sha256(candidate_raw).hexdigest()
updated_raw=(json.dumps(updated,sort_keys=True,indent=2)+'\n').encode()
try:
    verify(candidate)
    atomic(path,candidate_raw);atomic(STARTUP,updated_raw)
    verify(json.loads(path.read_bytes()))
    if any(hashlib.sha256((aura/name).read_bytes()).hexdigest()!=expected for name,expected in updated['component_sha256'].items()):
        raise RuntimeError('Updated source closure did not verify')
except BaseException:
    atomic(path,before);atomic(STARTUP,startup_before)
    raise
result=dict(status='CURRENT_CAMERA_OWNER_REBOUND_AND_VERIFIED',boot_id=BOOT,
    camera_pid=last['pid'],camera_birth_ticks=birth,camera_command_sha256=command_sha,
    original_pinned_source_files_verified=len(config['source_sha256']),components_verified=380,
    unchanged_components=379,changed_component=relative,backup=str(backup),
    startup_before_sha256=hashlib.sha256(startup_before).hexdigest(),startup_after_sha256=hashlib.sha256(updated_raw).hexdigest(),
    readback_before_sha256=hashlib.sha256(before).hexdigest(),readback_after_sha256=hashlib.sha256(candidate_raw).hexdigest(),
    changed_owner_fields=['board_boot_id','camera_pid','camera_start_ticks'],
    services_started=False,listening_enabled=False,database_opened=False,audio_or_motion_requested=False,
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(backup/'applied_receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
