"""Use existing systemd to supervise the unchanged original DFX client, once."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

BOOT='903cfade-b93c-48fa-804e-379be1967313'
TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-axis-restore-v1')
UNIT='aura-original-load-903c-v1.service'
CLIENT='/usr/bin/dfx-mgr-client'
CLIENT_SHA='a37d8449c3362a509d459f9e57aa3711314602369354f7d98ca60c3e51607ad7'
CP=Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/state/native-protection-checkpoint.json')
CP_SHA='c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471'

def show(name,properties):
    result=subprocess.run(['systemctl','show',name,'--property='+properties],capture_output=True,text=True,timeout=5)
    return dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)

def create(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert TX.resolve()==TX and not TX.is_symlink()
assert hashlib.sha256(CP.read_bytes()).hexdigest()==CP_SHA
assert (TX/('native-final-'+CP_SHA+'.json')).read_bytes()==CP.read_bytes()
assert not os.path.lexists(str(CP)+'.native-consumed-'+CP_SHA)
startup=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert hashlib.sha256(startup.read_bytes()).hexdigest()=='0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f'
for name in ('aura-camera-ui.service','aura-avatar-ui.service'):
    assert show(name,'MainPID,ActiveState,SubState,Job,Result')=={'MainPID':'0','ActiveState':'inactive','SubState':'dead','Job':'','Result':'success'}
assert hashlib.sha256(Path(CLIENT).read_bytes()).hexdigest()==CLIENT_SHA
assert (Path('/proc/1121')/'stat').read_text().rsplit(')',1)[1].split()[19]=='1516'
assert hashlib.sha256(Path('/proc/1121/cmdline').read_bytes()).hexdigest()=='eba390fe164718811ee931534079ab55a51a95b5e8092c7600dcf730346d7088'
assert not Path('/proc/device-tree/fpga-full/firmware-name').exists()
assert not list(Path('/sys/kernel/config/device-tree/overlays').iterdir())
assert not list(Path('/sys/class/drm').glob('renderD*'))
removed=show('aura-original-remove-903c-v1.service','InvocationID,ExecMainPID,ExecMainCode,ExecMainStatus,SubState,Job')
assert removed=={'InvocationID':'2f576a41a8f44a34b173cbca8305a82a','ExecMainPID':'79180','ExecMainCode':'1','ExecMainStatus':'0','SubState':'exited','Job':''}
assert (TX/'remove.stdout.raw').read_bytes()==b'remove from slot 0 returns: 0 (Ok)\n' and not (TX/'remove.stderr.raw').read_bytes()
release=Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
manifest_bytes=(release/'candidate-manifest.json').read_bytes()
assert hashlib.sha256(manifest_bytes).hexdigest()=='6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf'
manifest=json.loads(manifest_bytes)
assert manifest['app']=='aura-visual-servo-b4096-wide-v1' and manifest['build_id']==0x10282601
assert len(manifest['runtime_files'])==4 and len(manifest['payload_files'])==3
assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected for path,expected in manifest['runtime_files'].items())
assert all(hashlib.sha256((release/'driver'/name).read_bytes()).hexdigest()==expected for name,expected in manifest['payload_files'].items())
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
assert show(UNIT,'LoadState').get('LoadState')=='not-found','Existing original-client job; observe without retry'
stdout=TX/'load.stdout.raw';stderr=TX/'load.stderr.raw'
create(stdout,b'');create(stderr,b'')
arguments=['systemd-run','--unit='+UNIT,'--no-block','--service-type=exec','--remain-after-exit',
    '--property=Restart=no','--property=TimeoutStartSec=infinity','--property=RuntimeMaxSec=infinity',
    '--property=TimeoutStopSec=infinity','--property=KillMode=process','--property=SendSIGKILL=no',
    '--property=StandardInput=null','--property=StandardOutput=append:'+str(stdout),
    '--property=StandardError=append:'+str(stderr),'--property=UMask=0077',CLIENT,'-load','aura-visual-servo-b4096-wide-v1']
intent={'schema':'aura-original-client-os-job-intent-1','action':'original_load_original_wide','unit':UNIT,
    'boot_id':BOOT,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'monotonic_ns':time.monotonic_ns(),'client_argv':[CLIENT,'-load','aura-visual-servo-b4096-wide-v1'],'client_sha256':CLIENT_SHA,
    'checkpoint_sha256':CP_SHA,'daemon_pid':1121,'daemon_birth_ticks':1516,
    'systemd_run_argv':arguments,'stdout_path':str(stdout),'stderr_path':str(stderr)}
create(TX/'load-intent.json',(json.dumps(intent,sort_keys=True,indent=2)+'\n').encode())
fd=os.open(TX,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
# A timeout here could only stop this D-Bus submitter, never the system-manager-owned client.
launch=subprocess.run(arguments,capture_output=True,text=True,timeout=10)
properties='LoadState,Job,ActiveState,SubState,InvocationID,MainPID,ExecMainPID,ExecMainStartTimestampMonotonic,ExecMainExitTimestampMonotonic,ExecMainCode,ExecMainStatus,Result,Type,Restart,RemainAfterExit,KillMode,SendSIGKILL,RuntimeMaxUSec,TimeoutStartUSec,TimeoutStopUSec,ExecStart,StandardOutput,StandardError'
snapshot=show(UNIT,properties);process=None
pid=int(snapshot.get('MainPID','0'))
if pid:
    try:
        proc=Path('/proc')/str(pid)
        process={'pid':pid,'birth_ticks':(proc/'stat').read_text().rsplit(')',1)[1].split()[19],
            'cmdline_sha256':hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),
            'executable_sha256':hashlib.sha256((proc/'exe').read_bytes()).hexdigest()}
    except (FileNotFoundError,ProcessLookupError):process=None
receipt={'schema':'aura-original-client-os-job-submission-1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'unit':UNIT,'submit_returncode':launch.returncode,'submit_stdout':launch.stdout,'submit_stderr':launch.stderr,
    'unit_snapshot':snapshot,'live_process_metadata_if_observed':process,'intent_path':str(TX/'load-intent.json'),
    'execution_complete_claimed':False,'camera_or_motion_started':False}
create(TX/'load-submission.json',(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode())
print(json.dumps(receipt))
