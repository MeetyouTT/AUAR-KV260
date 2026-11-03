"""One finite invocation of the unchanged board face follower under systemd."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

BOOT='903cfade-b93c-48fa-804e-379be1967313'
BUSINESS=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
AURA=BUSINESS/'runtime/aura'
TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-follow-current-v1')
UNIT='aura-original-face-903c-once-v1.service'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def show(name,props):
    p=subprocess.run(['systemctl','show',name,'--property='+props],capture_output=True,text=True,timeout=4)
    return dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
def create(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert sha(BUSINESS/'startup/config.json')=='092c2ccf0872cae2f6e13c81e2d8b8a2ffe3b0800ab701566128b5c7947159af'
startup=json.loads((BUSINESS/'startup/config.json').read_text())
assert len(startup['component_sha256'])==380 and all(sha(AURA/key)==value for key,value in startup['component_sha256'].items())
gui=show('aura-avatar-ui.service','MainPID,ActiveState,SubState,Job')
assert gui=={'MainPID':'0','ActiveState':'failed','SubState':'failed','Job':''}
assert show('aura-camera-ui.service','MainPID,ActiveState,SubState,Job')=={'MainPID':'79866','ActiveState':'active','SubState':'running','Job':''}
assert (Path('/proc/79866/stat')).read_text().rsplit(')',1)[1].split()[19]=='2265436'
assert show(UNIT,'LoadState').get('LoadState')=='not-found'
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:maps=(proc/'maps').read_text()
    except (FileNotFoundError,ProcessLookupError):continue
    assert 'libvsrv.so' not in maps and '/dev/mem' not in maps,'Another axis owner exists'
face=json.loads((AURA/'config/pan_face.local.json').read_text());root=Path(face['release_root'])
assert sha(root/'deployment-manifest.json')==face['manifest_sha256']=='5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562'
items=json.loads((root/'deployment-manifest.json').read_text())['files'];assert len(items)==25
assert all(sha(item['destination'])==item['sha256'] for item in items)
assert sha(root/'run_face_motion.py')=='9ebf21a1bcbc37992398e8d59f459141d7cc49163dcf400e768ea129f4e8be94'
manual=json.loads((AURA/'config/pan_manual.local.json').read_text());assert manual['boot_id']==BOOT
assert sha(manual['release_manifest'])==manual['release_manifest_sha256']
direction=json.loads(Path(face['arguments']['direction-evidence']).read_text())
assert direction['boot_id']==BOOT and direction['axis_camera_mirrored_control_polarity']==1
assert direction['current_boot_motion_measured'] is False
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0')==b'aura-visual-servo-b4096-wide-v1.bit.bin'
assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
output=TX/'single-follow-40s.json';stdout=TX/'single-follow-40s.stdout.raw';stderr=TX/'single-follow-40s.stderr.raw'
assert not output.exists()
create(stdout,b'');create(stderr,b'')
argv=['/usr/bin/python3','-B',str(root/'run_face_motion.py')]
for key,value in face['arguments'].items():argv+=['--'+key,value]
argv+=['--output',str(output),'--confirmation','FACE_ZONE_CONTINUOUS','--duration','40']
intent={'schema':'aura-original-finite-face-follow-intent-1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'boot_id':BOOT,'unit':UNIT,'original_argv':argv,'duration_s':40,'original_source_unchanged':True,
    'range_us':[500,2500],'polarity':1,'reused_original_mapping':True,'new_direction_measurement_claimed':False,
    'normal_stop_is_original_program_finally':'shutdown_face_session','no_auto_restart':True,
    'gui_absent_reason':'original clock RTT guard rejected startup; no GUI mechanical owner',
    'explicit_cancel_argv':['systemctl','kill','--kill-who=main','--signal=SIGTERM',UNIT]}
create(TX/'single-follow-40s-intent.json',(json.dumps(intent,sort_keys=True,indent=2)+'\n').encode())
p=subprocess.run(['systemd-run','--unit='+UNIT,'--no-block','--service-type=exec','--remain-after-exit',
    '--property=Restart=no','--property=TimeoutStartSec=infinity','--property=RuntimeMaxSec=infinity',
    '--property=TimeoutStopSec=infinity','--property=KillMode=process','--property=SendSIGKILL=no',
    '--property=StandardInput=null','--property=StandardOutput=append:'+str(stdout),
    '--property=StandardError=append:'+str(stderr),'--property=UMask=0077']+argv,
    capture_output=True,text=True,timeout=8)
unit=show(UNIT,'InvocationID,MainPID,ExecMainPID,ExecMainStatus,Result,ActiveState,SubState,Job')
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'unit':UNIT,'submit_exit_code':p.returncode,
    'submission_stderr':p.stderr,'unit_snapshot':unit,'output':str(output),'finite_seconds':40,
    'completion_claimed':False,'gui_controls_connected':False,'original_program_only':True}
create(TX/'single-follow-40s-submission.json',(json.dumps(result,sort_keys=True,indent=2)+'\n').encode())
print(json.dumps(result));assert p.returncode==0
