"""Issue one original normal stop, leaving its original shutdown/checkpoint path intact."""
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import time

BOOT='903cfade-b93c-48fa-804e-379be1967313'
STARTUP=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
SHA='0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f'
TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-axis-restore-v1')
CHECKPOINT=Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/state/native-protection-checkpoint.json')

def unit(name):
    p=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job,Result,Restart,SendSIGKILL,KillMode,TimeoutStopUSec'],capture_output=True,text=True,timeout=5)
    assert p.returncode==0
    return dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert hashlib.sha256(STARTUP.read_bytes()).hexdigest()==SHA
gui=unit('aura-avatar-ui.service');camera=unit('aura-camera-ui.service')
assert gui['MainPID']=='0' and gui['ActiveState']=='inactive' and not gui['Job']
assert camera['MainPID']=='1333' and camera['ActiveState']=='active' and not camera['Job']
assert camera['Restart']=='no' and camera['SendSIGKILL']=='no' and camera['KillMode']=='process' and camera['TimeoutStopUSec']=='infinity'
proc=Path('/proc/1333')
assert (proc/'stat').read_text().rsplit(')',1)[1].split()[19]=='2359'
assert hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()=='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
assert json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())=={'version':1,'enabled':False}
c=http.client.HTTPConnection('127.0.0.1',8790,timeout=3)
try:
    c.request('GET','/health');r=c.getresponse();data=r.read(1048577)
    assert r.status==200 and len(data)<=1048576
    health=json.loads(data)
finally:c.close()
schedule=health['dpu_schedule'];features=health['identity']['feature_inference']
assert health['pid']==1333 and health['board_boot_id']==BOOT and health['motion_command_emitted'] is False
assert health['identity']['ready'] is True and not health['identity'].get('error')
assert not health.get('camera_error') and not health.get('detector_error')
assert schedule['native_critical'] is True and schedule['native_abi']==2
assert schedule['owner_fenced'] is False and schedule['quiesced'] is False
assert schedule['primary_calls']>=209300 and schedule['primary_period_overruns']>=1
assert features['completed']>=3461
assert not TX.exists() and not TX.is_symlink() and TX.parent.resolve(strict=True)==TX.parent
TX.mkdir(mode=0o700)
intent={'schema':'aura-original-camera-stop-intent-1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'boot_id':BOOT,'source_pid':1333,'source_birth_ticks':2359,'startup_sha256':SHA,
    'stop_intent_mono_ns':time.monotonic_ns(),'primary_calls_lower_bound':schedule['primary_calls'],
    'primary_period_overruns_lower_bound':schedule['primary_period_overruns'],
    'sface_completed_lower_bound':features['completed'],'action':'systemctl stop --no-block aura-camera-ui.service'}
raw=(json.dumps(intent,sort_keys=True,indent=2)+'\n').encode()
fd=os.open(TX/'camera-stop-intent.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
fd=os.open(TX,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
p=subprocess.run(['systemctl','stop','--no-block','aura-camera-ui.service'],capture_output=True,text=True,timeout=8)
assert p.returncode==0
deadline=time.monotonic()+25
while True:
    state=unit('aura-camera-ui.service')
    stopped=state['MainPID']=='0' and state['ActiveState']=='inactive' and state['SubState']=='dead' and not state['Job']
    if stopped or time.monotonic()>=deadline:break
    time.sleep(.3)
result={'schema':'aura-original-camera-normal-stop-1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'CAMERA_STOPPED' if stopped else 'CAMERA_STOP_PENDING','intent':intent,
    'stop_sent_once':True,'unit':state,'firmware_changed':False,'motion_requested':False,'forced_action':False}
if stopped:
    assert not proc.exists()
    before=CHECKPOINT.read_bytes();assert len(before)<=262144
    document=json.loads(before);seed=document['seed']
    assert document['schema']=='aura-native-protection-checkpoint-2'
    assert seed['purpose']=='final_quiescent_business_checkpoint' and seed['checkpoint_kind']==1
    assert seed['boot_id']==BOOT and seed['source_pid']==1333 and seed['source_birth_ticks']==2359
    assert seed['captured_mono_ns']>=intent['stop_intent_mono_ns']
    assert seed['primary_calls']>=intent['primary_calls_lower_bound'] and seed['primary_period_overruns']>=intent['primary_period_overruns_lower_bound']
    result.update(status='CAMERA_STOPPED_NEW_FINAL_PRESENT',checkpoint_path=str(CHECKPOINT),
        checkpoint_sha256=hashlib.sha256(before).hexdigest(),checkpoint_bytes=len(before),
        checkpoint_captured_mono_ns=seed['captured_mono_ns'],checkpoint_primary_calls=seed['primary_calls'],
        checkpoint_primary_period_overruns=seed['primary_period_overruns'],
        full_original_validator_still_required=True,checkpoint_consumed=False)
print(json.dumps(result))
