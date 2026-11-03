"""Read only the original metadata needed to rebase the original pan transaction."""
import ast,copy,hashlib,http.client,json,os,subprocess,time
from pathlib import Path
B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');A=B/'runtime/aura';S=B/'startup/config.json'
def raw(p):
    p=Path(p);assert p.is_file() and not p.is_symlink() and p.suffix not in ('.db','.sqlite','.sqlite3') and p.stat().st_size<64000000
    return p.read_bytes()
def sha(p):return hashlib.sha256(raw(p)).hexdigest()
def load(p):return json.loads(raw(p))
def unit(n):
    r=subprocess.run(['systemctl','show',n,'--property=MainPID,ActiveState,SubState,Job,Result'],capture_output=True,text=True,timeout=5);assert r.returncode==0
    return dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==G['boot_id']
assert sha(S)==G['startup_before_sha256'];startup=load(S);assert startup['component_sha256']==C['pins'] and len(C['pins'])==380
assert all(sha(A/n)==v for n,v in C['pins'].items())
assert all(C['pins'][n]==v for n,v in G['latest_identity_four_core'].items())
gui=unit('aura-avatar-ui.service');assert gui['MainPID']=='0' and gui['ActiveState']=='inactive' and gui['SubState']=='dead' and not gui['Job']
camera=unit('aura-camera-ui.service');assert camera['MainPID']==str(G['camera_owner']['pid']) and camera['ActiveState']=='active' and camera['SubState']=='running' and not camera['Job']
p=Path('/proc')/str(G['camera_owner']['pid']);assert (p/'stat').read_text().rsplit(')',1)[1].split()[19]==G['camera_owner']['birth_ticks']
assert hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==G['camera_owner']['command_sha256']
assert sha(G['camera_config']['path'])==G['camera_config']['sha256']
assert sha('/sys/firmware/fdt')==C['context']['fdt_sha256']
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==C['context']['firmware_name']=='aura-visual-servo-b4096-wide-v1.bit.bin'
assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
assert Path('/etc/vart.conf').read_bytes()==b'firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-wide-v1/aura-visual-servo-b4096-wide-v1.xclbin\n'
restore=Path(C['wide_root']);assert load(restore/'wide-context.json')==C['context']
assert sha(restore/'id-stop.json')==C['IDSTOP_sha256'];stop=load(restore/'id-stop.json');verified=load(restore/'idstop-verified.json')
assert verified['report_sha256']==C['IDSTOP_sha256'] and verified['report']==stop and stop['identity_stop_passed']
ui=load(A/'config/board_avatar_gtk.json');spec=ui['board_business']['face_readback'];selected=load(G['selected_face_binding']['path'])
assert spec['path']==G['selected_face_binding']['path'] and spec['sha256']==sha(spec['path'])==G['selected_face_binding']['sha256']
assert selected['source_sha256']==C['selected_sources'] and len(C['selected_sources'])==27
assert all(sha(n)==v for n,v in C['selected_sources'].items())
assert selected['board_boot_id']==G['boot_id'] and selected['camera_pid']==G['camera_owner']['pid'] and str(selected['camera_start_ticks'])==G['camera_owner']['birth_ticks'] and selected['camera_config']==G['camera_config']['path']
verifier=A/'board/runtime/audio/face_gallery_readback.py';tree=ast.parse(raw(verifier).decode());klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FaceGalleryReadback');node=copy.deepcopy(next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_verify'));node.decorator_list=[]
space={'Path':Path,'hashlib':hashlib,'json':json};exec(compile(ast.Module(body=[node],type_ignores=[]),str(verifier)+'::<metadata-only>', 'exec'),space);space['_verify'](selected)
face=load(A/'config/pan_face.local.json');manual=load(A/'config/pan_manual.local.json');direction=load(A/'config/pan_direction.current.json')
control=Path(face['release_root']);assert str(control)=='/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-stable150-35d5e154'
assert sha(control/'deployment-manifest.json')==face['manifest_sha256']=='9cd35b967bf9c859ed3f1f4de4dc5dad199e81ddfed845435fc8745a41be0ba9'
files=load(control/'deployment-manifest.json')['files'];assert len(files)==25
for f in files:assert sha(f['destination'])==f['sha256'] and Path(f['destination']).stat().st_size==f['bytes']
release_path=Path(manual['release_manifest']);assert sha(release_path)==manual['release_manifest_sha256'];release=load(release_path)
assert release['status']=='USER_RATED_RANGE_VSRV2';auth_path=release_path.parent/release['authorization']['file'];assert sha(auth_path)==release['authorization']['sha256']
zone_path=Path(face['arguments']['zone-settings']);zone=load(zone_path)
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:maps=(proc/'maps').read_text()
    except (FileNotFoundError,ProcessLookupError):continue
    assert 'libvsrv.so' not in maps and '/dev/mem' not in maps,'Existing original axis owner'
c=http.client.HTTPConnection('127.0.0.1',8790,timeout=3)
try:
    c.request('GET','/health');r=c.getresponse();body=r.read(2097153);assert r.status==200 and len(body)<=2097152;health=json.loads(body)
finally:c.close()
assert health['pid']==G['camera_owner']['pid'] and health['board_boot_id']==G['boot_id'] and health['identity']['ready'] is True
assert not any(health.get(k) for k in ('camera_error','detector_error','preview_error')) and health['motion_command_emitted'] is False
assert sha(S)==G["startup_before_sha256"]

PB=json.loads('{"zone": {"board_boot_id": "a6d4a069-e9b0-4065-8df7-dc23556b168e", "center_tolerance_ratio": 0.03, "frame_height": 480, "frame_width": 640, "geometry_reused_from": "/home/root/aura-pan-current-20261024/16a07283/face-zone-settings.json", "geometry_reused_sha256": "74dc2c216c115d0d0698086a205911482a1a666957fe915e640546e03ea4f8f2", "left_camera_ratio": 0.05, "left_ratio": 0.0, "left_reference": "face_box_left_edge", "mirror_horizontal": true, "recenter_on_edge": true, "reference": "face_center", "right_ratio": 0.7158253629442671, "right_reference": "face_center", "schema": "aura-face-zone-settings-1", "target_center_ratio": 0.5, "target_kind": "face", "updated_mono_ms": 22818709, "viewport": [8, 112, 568, 300]}, "host_prepared_utc": "2026-11-02T19:03:35.285319+00:00"}')
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

BOOT='a6d4a069-e9b0-4065-8df7-dc23556b168e'
BUSINESS=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
AURA=BUSINESS/'runtime/aura'
STARTUP=BUSINESS/'startup/config.json'
EXPECTED='9e260350eb6ba5775428cc9c1d056fab35b7753d52fd37ca53a7361f0c93835b'
BASE=Path('/home/root/aura-5090-recovery-20261102-a6d4a069')
TX=BASE/'original-follow-binding-185858-v1'
RESTORE=Path('/home/root/aura-5090-recovery-20261102-a6d4a069/axis-wide-idstop-184011-v1')
CONTROL=Path('/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-stable150-35d5e154')
APPLY=True
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
    assert sha('/sys/firmware/fdt')=='ed0e2ace1f5bda2b937a61f5f8a5ef05cf01065a24627b23ca2de6614948542f'
    assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0')==b'aura-visual-servo-b4096-wide-v1.bit.bin'
    assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
    assert Path('/etc/vart.conf').read_bytes()==b'firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-wide-v1/aura-visual-servo-b4096-wide-v1.xclbin\n'
    cam=show('aura-camera-ui.service')
    assert cam['MainPID']=='362659' and cam['ActiveState']=='active' and cam['SubState']=='running' and not cam['Job']
    p=Path('/proc/362659');assert (p/'stat').read_text().rsplit(')',1)[1].split()[19]=='2850120'
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
assert sha(manifest)=='9cd35b967bf9c859ed3f1f4de4dc5dad199e81ddfed845435fc8745a41be0ba9'
files=json.loads(raw(manifest))['files'];assert len(files)==25
assert all(sha(item['destination'])==item['sha256'] for item in files)
manual_path=AURA/'config/pan_manual.local.json';face_path=AURA/'config/pan_face.local.json';direction_path=AURA/'config/pan_direction.current.json'
manual=json.loads(raw(manual_path));face=json.loads(raw(face_path));old_direction=json.loads(raw(direction_path))
old_release_path=Path(manual['release_manifest']);old_release=json.loads(raw(old_release_path))
assert sha(old_release_path)==manual['release_manifest_sha256']=='fc637df7579902aa94ed1caa49091dc62d24fcb5863c78e800b7aaccb10a40c1'
assert old_release['status']=='USER_RATED_RANGE_VSRV2'
assert old_direction['axis_camera_mirrored_control_polarity']==1 and old_direction['status']=='HUMAN_DIRECTION_CONFIRMED'
zone_path=Path(face['arguments']['zone-settings']);old_zone=json.loads(raw(zone_path))
assert old_zone['frame_width']==640 and old_zone['frame_height']==480 and old_zone['viewport']==[8,112,568,300] and old_zone['mirror_horizontal'] is True
assert old_zone==PB['zone']
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
assert health['pid']==362659 and health['board_boot_id']==BOOT and health['identity']['ready'] is True
assert not any(health.get(k) for k in ('camera_error','detector_error','preview_error'))
assert health['motion_command_emitted'] is False

now=PB['host_prepared_utc']
authorization=copy.deepcopy(json.loads(raw(old_release_path.parent/old_release['authorization']['file'])))
authorization.update(boot_id=BOOT,user_instruction_quote='转轴解冻，我要进行整个流程的验收',
    current_user_mount_and_power_confirmation='转轴动力保持断开；沿用本轮已确认的安装未动、可观察、左右空间及线缆余量充足',
    motor_power_state='OFF',motor_power_off_is_human_confirmation=True,
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
    'current_camera_owner':{'pid':362659,'birth_ticks':'2850120'},'new_release_sha256':hashlib.sha256(enc(release)).hexdigest(),
    'ARM_sent':False,'COMMIT_sent':False,'services_started':False,'camera_stopped':False,'board_mutations':APPLY}
assert all(new_startup['component_sha256'][k]==v for k,v in pins.items() if k not in receipt['changed_component_keys'])
receipt.update(component_sha256=new_startup['component_sha256'],unchanged_component_count=377,
    new_manual_release_path=str(TX/'manual-release/release.json'),new_context_path=str(RESTORE/'wide-context.json'),
    original_direction_predecessor_sha256=sha(direction_path),original_authorization_predecessor_sha256=old_release['authorization']['sha256'],
    motor_power_state='OFF',selected27_and_four_core_preserved=True,
    BIND_sent=False,REFERENCE_sent=False,STOP_sent=False,MMIO_opened=False,
    phase_grant_sha256='7b1f3f1de563a8488f0692e4f7fb29d559a9e82aa79d7016fed45f9aaf5e62dc')
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
