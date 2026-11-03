"""Verify original ID/STOP result, then start the unchanged camera service once."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

BOOT='903cfade-b93c-48fa-804e-379be1967313'
TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-axis-restore-v1')
CP=Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/state/native-protection-checkpoint.json')
SHA='c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471'

def show(name,props):
    p=subprocess.run(['systemctl','show',name,'--property='+props],capture_output=True,text=True,timeout=5)
    assert p.returncode==0
    return dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)

def create(path,value):
    data=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
state=show('aura-original-idstop-903c-v1.service','InvocationID,MainPID,ExecMainPID,ExecMainCode,ExecMainStatus,Result,ActiveState,SubState,Job,ExecMainExitTimestampMonotonic')
assert state['InvocationID']=='06d7005d93534d09ba36356a5322f91d' and state['ExecMainPID']=='79696'
assert state['MainPID']=='0' and state['ActiveState']=='active' and state['SubState']=='exited' and not state['Job']
assert state['ExecMainCode']=='1' and state['ExecMainStatus']=='0' and state['Result']=='success' and int(state['ExecMainExitTimestampMonotonic'])>0
report_bytes=(TX/'id-stop.json').read_bytes();report=json.loads(report_bytes)
assert report['boot_id']==BOOT and report['manifest_sha256']=='6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf'
assert report['identity_stop_passed'] is True and report['after_stop']['flags']==0 and report['after_stop']['lease_left_ms']==0
assert all(report[k] is False for k in ('ARM_sent','COMMIT_sent','BIND_sent','REFERENCE_sent'))
assert not (TX/'idstop.stderr.raw').read_bytes()
output=json.loads((TX/'idstop.stdout.raw').read_bytes())
assert output=={'identity_stop_passed':True,'motion_tested':False,'report':str(TX/'id-stop.json')}
for name in ('aura-avatar-ui.service','aura-camera-ui.service'):
    assert show(name,'MainPID,ActiveState,SubState,Job')=={'MainPID':'0','ActiveState':'inactive','SubState':'dead','Job':''}
assert not Path('/proc/1333').exists()
assert hashlib.sha256(CP.read_bytes()).hexdigest()==SHA and (TX/('native-final-'+SHA+'.json')).read_bytes()==CP.read_bytes()
assert not os.path.lexists(str(CP)+'.native-consumed-'+SHA)
context=json.loads((TX/'wide-context.json').read_bytes())
assert context['boot_id']==BOOT and hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest()==context['fdt_sha256']
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==context['firmware_name']=='aura-visual-servo-b4096-wide-v1.bit.bin'
assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
assert json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())=={'version':1,'enabled':False}
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:
        maps=(proc/'maps').read_text();targets=[]
        for fd in (proc/'fd').iterdir():
            try:targets.append(str(fd.readlink()))
            except FileNotFoundError:continue
        assert not any(x in maps for x in ('libvart','libaura_native_operator','libvsrv.so'))
        assert not any(t.startswith(('/dev/dri/renderD','/dev/dpu')) or t=='/dev/mem' for t in targets)
    except (FileNotFoundError,ProcessLookupError):continue
create(TX/'idstop-verified.json',{'unit':state,'report_sha256':hashlib.sha256(report_bytes).hexdigest(),
    'report':report,'confirmed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
intent={'schema':'aura-original-camera-start-intent-1','boot_id':BOOT,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'monotonic_ns':time.monotonic_ns(),'checkpoint_sha256':SHA,'action':'systemctl start --no-block aura-camera-ui.service',
    'id_stop_only_verified':True,'old_owner_pid':1333,'old_owner_birth_ticks':2359}
create(TX/'camera-start-intent.json',intent)
started=subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],capture_output=True,text=True,timeout=8)
receipt={'schema':'aura-original-idstop-pass-camera-start-request-1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'ORIGINAL_ID_STOP_PASS_CAMERA_START_REQUESTED','start_returncode':started.returncode,
    'id_stop_report':report,'id_stop_unit':state,'checkpoint_sha256':SHA,'context':context,
    'camera_unit':show('aura-camera-ui.service','MainPID,ActiveState,SubState,Job,Result,ExecMainStatus'),
    'source_service_or_shutdown_protection_modified':False,'ARM_sent':False,'COMMIT_sent':False,'BIND_sent':False,'REFERENCE_sent':False}
create(TX/'camera-start-request.json',receipt)
print(json.dumps(receipt));assert started.returncode==0
