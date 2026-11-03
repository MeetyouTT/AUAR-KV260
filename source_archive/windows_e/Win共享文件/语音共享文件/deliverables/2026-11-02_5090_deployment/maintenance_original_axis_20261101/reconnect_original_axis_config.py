"""Refresh original rated-range release/configuration; no new controller or motion."""
import ast
import copy
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import uuid

BOOT='903cfade-b93c-48fa-804e-379be1967313'
BUSINESS=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
AURA=BUSINESS/'runtime/aura'
STARTUP=BUSINESS/'startup/config.json'
EXPECTED='3f5e81abc20ce5169ac91ae302611cba8958175a6a2bdb615fd9b858353120d5'
BASE=Path('/home/root/aura-5090-recovery-20261102-903cfade')
TX=BASE/'original-follow-current-v1'
RESTORE=BASE/'original-axis-restore-v1'
CONTROL=Path('/home/root/aura-pan-wide-20261028/control-10282601')
APPLY=sys.argv[1:]==['--apply-original-axis-config']
assert not sys.argv[1:] or APPLY

def raw(path):
    p=Path(path);assert p.is_file() and not p.is_symlink() and p.suffix not in ('.db','.sqlite','.sqlite3')
    assert p.stat().st_size<64000000
    return p.read_bytes()

def sha(path):return hashlib.sha256(raw(path)).hexdigest()
def enc(v):return (json.dumps(v,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()
def show(name):
    p=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job,Result'],capture_output=True,text=True,timeout=4)
    assert p.returncode==0
    return dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)

def guard(stopped=False):
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert sha(STARTUP)==EXPECTED
    assert sha('/sys/firmware/fdt')=='d68bc147f22f5ab23bc60f0c2762af4bcd7b64340953e9c948e28ffa6b80f7ca'
    assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0')==b'aura-visual-servo-b4096-wide-v1.bit.bin'
    assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
    assert Path('/etc/vart.conf').read_bytes()==b'firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-wide-v1/aura-visual-servo-b4096-wide-v1.xclbin\n'
    cam=show('aura-camera-ui.service')
    assert cam['MainPID']=='79866' and cam['ActiveState']=='active' and cam['SubState']=='running' and not cam['Job']
    p=Path('/proc/79866');assert (p/'stat').read_text().rsplit(')',1)[1].split()[19]=='2265436'
    assert hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()=='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
    if stopped:
        gui=show('aura-avatar-ui.service')
        assert gui['MainPID']=='0' and gui['ActiveState']=='inactive' and gui['SubState']=='dead' and not gui['Job']
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:maps=(proc/'maps').read_text()
        except (FileNotFoundError,ProcessLookupError):continue
        assert 'libvsrv.so' not in maps and '/dev/mem' not in maps,'Existing axis owner'

guard(APPLY)
startup=json.loads(raw(STARTUP));pins=startup['component_sha256']
assert len(pins)==380 and all(sha(AURA/k)==v for k,v in pins.items())
assert pins['tools/unified_identity_binding.py']=='85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809'
manifest=CONTROL/'deployment-manifest.json'
assert sha(manifest)=='5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562'
files=json.loads(raw(manifest))['files'];assert len(files)==25
assert all(sha(item['destination'])==item['sha256'] for item in files)
manual_path=AURA/'config/pan_manual.local.json';face_path=AURA/'config/pan_face.local.json';direction_path=AURA/'config/pan_direction.current.json'
manual=json.loads(raw(manual_path));face=json.loads(raw(face_path));old_direction=json.loads(raw(direction_path))
old_release_path=Path(manual['release_manifest']);old_release=json.loads(raw(old_release_path))
assert sha(old_release_path)==manual['release_manifest_sha256']=='a329dcb4ef7d701a659d949a8739b0d7bad3789d0ecbad74c2ec8b77e9c70152'
assert old_release['status']=='USER_RATED_RANGE_VSRV2'
assert old_direction['axis_camera_mirrored_control_polarity']==1 and old_direction['status']=='HUMAN_DIRECTION_CONFIRMED'
zone_path=Path(face['arguments']['zone-settings']);old_zone=json.loads(raw(zone_path))
assert old_zone['frame_width']==640 and old_zone['frame_height']==480 and old_zone['viewport']==[8,112,568,300] and old_zone['mirror_horizontal'] is True
assert old_zone['left_camera_ratio']==.1 and old_zone['right_ratio']==.7158253629442671
context=json.loads(raw(RESTORE/'wide-context.json'))
assert context['boot_id']==BOOT and context['fdt_sha256']==sha('/sys/firmware/fdt')
id_report=json.loads(raw(RESTORE/'id-stop.json'));verified=json.loads(raw(RESTORE/'idstop-verified.json'))
assert verified['report_sha256']==sha(RESTORE/'id-stop.json') and verified['report']==id_report
assert id_report['boot_id']==BOOT and id_report['identity_stop_passed'] is True
assert all(id_report[k] is False for k in ('ARM_sent','COMMIT_sent','BIND_sent','REFERENCE_sent'))
assert id_report['after_stop']['flags']==0 and id_report['after_stop']['lease_left_ms']==0
assert all(sha(path)==value for path,value in old_release['runtime_files'].items())
payload={name:raw(old_release_path.parent/name) for name in old_release['payload_files']}
assert all(hashlib.sha256(payload[name]).hexdigest()==value for name,value in old_release['payload_files'].items())
connection=http.client.HTTPConnection('127.0.0.1',8790,timeout=3)
try:
    connection.request('GET','/health');response=connection.getresponse();body=response.read(2097153)
    assert response.status==200 and len(body)<=2097152
    health=json.loads(body)
finally:connection.close()
assert health['pid']==79866 and health['board_boot_id']==BOOT and health['identity']['ready'] is True
assert not any(health.get(k) for k in ('camera_error','detector_error','preview_error'))
assert health['motion_command_emitted'] is False

now=datetime.datetime.now(datetime.timezone.utc).isoformat()
authorization=copy.deepcopy(json.loads(raw(old_release_path.parent/old_release['authorization']['file'])))
authorization.update(boot_id=BOOT,user_instruction_quote='转轴我已经接好了，按照原来Ubuntu上写的；按照原来已优化的直接进行人脸跟随，我一次性调试',
    current_user_mount_and_power_confirmation='安装未动，可观察且空间充足；大致在中间且相机朝前；转轴动力已接好',
    predecessor_authorization={'path':str(old_release_path.parent/old_release['authorization']['file']),'sha256':old_release['authorization']['sha256']},
    current_boot_motion_measured=False,recorded_utc=now)
proof=dict(id_report,fdt_sha256=context['fdt_sha256'],build_id=0x10282601,
    original_id_stop_report={'path':str(RESTORE/'id-stop.json'),'sha256':sha(RESTORE/'id-stop.json')})
release=copy.deepcopy(old_release);release.update(boot_id=BOOT,
    authorization={'file':'authorization.json','sha256':hashlib.sha256(enc(authorization)).hexdigest()},
    platform_proof={'file':'platform-proof.json','sha256':hashlib.sha256(enc(proof)).hexdigest()})
direction=copy.deepcopy(old_direction)
direction.update(boot_id=BOOT,qualification_basis='User-directed reuse of previously human-confirmed polarity on unchanged camera/axis installation',
    source='Current user restoration instruction and original human-confirmed mapping',current_boot_motion_measured=False,
    user_instruction_quote=authorization['user_instruction_quote'],
    predecessor_direction={'path':str(TX/'direction.predecessor.json'),'original_path':str(direction_path),'sha256':sha(direction_path),'boot_id':old_direction['boot_id']})
for key in ('trial_sha256','pulse_sequence_us','physical_return_stop_observed','command_return_stop_verified','user_quote'):
    direction.pop(key,None)
direction['corrected_mapping_live_acceptance']='PENDING_CURRENT_USER_OBSERVATION'
zone=copy.deepcopy(old_zone);zone.update(board_boot_id=BOOT,updated_mono_ms=int(time.monotonic()*1000),
    geometry_reused_from=str(zone_path),geometry_reused_sha256=sha(zone_path),
    reuse_basis='Unchanged installation, same pinned original GUI viewport and restored original camera')
human=copy.deepcopy(authorization);human['actual_direction_evidence_sha256']=hashlib.sha256(enc(direction)).hexdigest()
new_manual=copy.deepcopy(manual);new_manual.update(boot_id=BOOT,fdt_sha256=context['fdt_sha256'],
    release_manifest=str(TX/'manual-release/release.json'),release_manifest_sha256=hashlib.sha256(enc(release)).hexdigest())
new_face=copy.deepcopy(face)
new_face['arguments']['context']=str(RESTORE/'wide-context.json')
new_face['arguments']['human-evidence']=str(TX/'human-evidence.json')
new_face['arguments']['zone-settings']=str(TX/'face-zone-settings.json')
assert new_face['duration_s']==0 and new_face['follow_semantics']=='latched_visual_center_hardware_slew'
new={manual_path:enc(new_manual),face_path:enc(new_face),direction_path:enc(direction)}
new_startup=copy.deepcopy(startup)
for path,value in new.items():new_startup['component_sha256'][str(path.relative_to(AURA))]=hashlib.sha256(value).hexdigest()
new[STARTUP]=enc(new_startup)
before={path:raw(path) for path in new}
assert {k:v for k,v in new_manual.items() if k not in ('boot_id','fdt_sha256','release_manifest','release_manifest_sha256')}=={k:v for k,v in manual.items() if k not in ('boot_id','fdt_sha256','release_manifest','release_manifest_sha256')}
assert {k for k,v in pins.items() if new_startup['component_sha256'][k]!=v}=={'config/pan_manual.local.json','config/pan_face.local.json','config/pan_direction.current.json'}
receipt={'schema':'aura-original-axis-current-config-1','utc':now,'status':'DRY_RUN_READY','transaction':str(TX),
    'startup_before_sha256':EXPECTED,'startup_after_sha256':hashlib.sha256(new[STARTUP]).hexdigest(),
    'changed_component_keys':[str(p.relative_to(AURA)) for p in new if p!=STARTUP],
    'original_control_files_verified':25,'original_control_source_changed':False,'software_bounds_us':[500,2500],
    'original_polarity':1,'new_direction_measurement_claimed':False,'nominal_reference_is_not_measured_angle':True,
    'current_camera_owner':{'pid':79866,'birth_ticks':'2265436'},'new_release_sha256':hashlib.sha256(enc(release)).hexdigest(),
    'ARM_sent':False,'COMMIT_sent':False,'services_started':False,'camera_stopped':False,'board_mutations':APPLY}
if not APPLY:
    print(json.dumps(receipt));raise SystemExit(0)
assert not TX.exists() and not TX.is_symlink()
def fsync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def create(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
    fsync_dir(path.parent)
def replace(path,old,data):
    st=path.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_uid==0 and raw(path)==old
    temp=path.with_name('.'+path.name+'.original-axis-'+uuid.uuid4().hex+'.tmp')
    fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,stat.S_IMODE(st.st_mode))
    with os.fdopen(fd,'wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
    assert raw(path)==old
    os.replace(temp,path);fsync_dir(path.parent)
guard(True)
TX.mkdir(mode=0o700);(TX/'manual-release').mkdir(mode=0o700);(TX/'before').mkdir(mode=0o700)
create(TX/'authorization-record.json',enc(authorization))
create(TX/'manual-release/authorization.json',enc(authorization));create(TX/'manual-release/platform-proof.json',enc(proof))
for name,value in payload.items():create(TX/'manual-release'/name,value)
create(TX/'manual-release/release.json',enc(release));create(TX/'human-evidence.json',enc(human));create(TX/'face-zone-settings.json',enc(zone))
create(TX/'direction.inherited.json',enc(direction));create(TX/'direction.predecessor.json',raw(direction_path))
validator=AURA/'board/motion/rated_range_release.py';assert sha(validator)==pins['board/motion/rated_range_release.py']
space={'__name__':'original_rated_range_metadata_only'}
exec(compile(raw(validator),str(validator),'exec'),space)
assert space['rated_range_bounds'](release,new_manual,TX/'manual-release')==(500,2500)
changed=[]
try:
    for i,(path,value) in enumerate(before.items()):create(TX/'before'/(str(i)+'-'+path.name),value)
    for path,value in new.items():
        assert raw(path)==before[path]
        changed.append(path);replace(path,before[path],value)
    assert all(sha(AURA/key)==value for key,value in new_startup['component_sha256'].items())
    assert sha(STARTUP)==receipt['startup_after_sha256']
    assert space['rated_range_bounds'](release,new_manual,TX/'manual-release')==(500,2500)
    receipt.update(status='ORIGINAL_AXIS_CONFIG_RECONNECTED_GUI_STOPPED',original_rated_range_validator_passed=True,components_verified=380)
    create(TX/'transaction.json',enc(receipt))
except BaseException:
    for path in reversed(changed):
        if raw(path)==new[path]:replace(path,new[path],before[path])
    raise
print(json.dumps(receipt))
