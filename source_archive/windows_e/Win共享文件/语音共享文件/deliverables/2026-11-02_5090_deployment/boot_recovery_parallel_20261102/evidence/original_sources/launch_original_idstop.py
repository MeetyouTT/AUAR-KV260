"""Create fresh measured context, then run the unchanged original ID/STOP-only entry."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

BOOT='903cfade-b93c-48fa-804e-379be1967313'
TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-axis-restore-v1')
UNIT='aura-original-idstop-903c-v1.service'
RELEASE=Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
BENCH=RELEASE/'bench_identity_stop.py'
MANIFEST='6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf'

def show(name,properties):
    p=subprocess.run(['systemctl','show',name,'--property='+properties],capture_output=True,text=True,timeout=5)
    return dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)

def create(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert hashlib.sha256(BENCH.read_bytes()).hexdigest()=='c9e91f74336c1e73d7c60408739abc8537b80066eb666a1a79e32b81d7d267aa'
assert hashlib.sha256((RELEASE/'candidate-manifest.json').read_bytes()).hexdigest()==MANIFEST
assert show('aura-original-load-903c-v1.service','InvocationID,ExecMainPID,ExecMainCode,ExecMainStatus,SubState,Job')=={'InvocationID':'990d648e43ee4a9fb5cf9f6066ba2156','ExecMainPID':'79397','ExecMainCode':'1','ExecMainStatus':'0','SubState':'exited','Job':''}
assert (TX/'load.stdout.raw').read_bytes()==b'aura-visual-servo-b4096-wide-v1: loaded to slot 0\n' and not (TX/'load.stderr.raw').read_bytes()
for name in ('aura-camera-ui.service','aura-avatar-ui.service'):
    assert show(name,'MainPID,ActiveState,SubState,Job')=={'MainPID':'0','ActiveState':'inactive','SubState':'dead','Job':''}
assert show(UNIT,'LoadState').get('LoadState')=='not-found'
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
fdt=Path('/sys/firmware/fdt').read_bytes()
firmware=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
assert firmware=='aura-visual-servo-b4096-wide-v1.bit.bin'
assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
context={'boot_id':BOOT,'fdt_sha256':hashlib.sha256(fdt).hexdigest(),'firmware_name':firmware}
create(TX/'wide-fdt.raw.dtb',fdt)
create(TX/'wide-context.json',(json.dumps(context,sort_keys=True,indent=2)+'\n').encode())
stdout=TX/'idstop.stdout.raw';stderr=TX/'idstop.stderr.raw';create(stdout,b'');create(stderr,b'')
argv=['/usr/bin/python3','-B',str(BENCH),'--execute','--confirmation','ID_STOP_ONLY',
    '--manifest',str(RELEASE/'candidate-manifest.json'),'--manifest-sha256',MANIFEST,
    '--context',str(TX/'wide-context.json'),'--output',str(TX/'id-stop.json')]
intent={'schema':'aura-original-id-stop-intent-1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'boot_id':BOOT,'context':context,'unit':UNIT,'original_argv':argv,
    'entry_sha256':'c9e91f74336c1e73d7c60408739abc8537b80066eb666a1a79e32b81d7d267aa',
    'interpreter_sha256':hashlib.sha256(Path('/usr/bin/python3').read_bytes()).hexdigest(),
    'ARM_requested':False,'COMMIT_requested':False,'BIND_requested':False,'REFERENCE_requested':False}
create(TX/'idstop-intent.json',(json.dumps(intent,sort_keys=True,indent=2)+'\n').encode())
fd=os.open(TX,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
launch=subprocess.run(['systemd-run','--unit='+UNIT,'--no-block','--service-type=exec','--remain-after-exit',
    '--property=Restart=no','--property=TimeoutStartSec=infinity','--property=RuntimeMaxSec=infinity',
    '--property=TimeoutStopSec=infinity','--property=KillMode=process','--property=SendSIGKILL=no',
    '--property=StandardInput=null','--property=StandardOutput=append:'+str(stdout),
    '--property=StandardError=append:'+str(stderr),'--property=UMask=0077']+argv,capture_output=True,text=True,timeout=10)
state=show(UNIT,'InvocationID,MainPID,ExecMainPID,ExecMainStartTimestampMonotonic,ExecMainExitTimestampMonotonic,ExecMainCode,ExecMainStatus,Result,ActiveState,SubState,Job,ExecStart')
process=None;pid=int(state.get('MainPID','0'))
if pid:
    try:
        proc=Path('/proc')/str(pid)
        process={'pid':pid,'birth_ticks':(proc/'stat').read_text().rsplit(')',1)[1].split()[19],
            'command_sha256':hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),
            'interpreter_sha256':hashlib.sha256((proc/'exe').read_bytes()).hexdigest()}
    except (FileNotFoundError,ProcessLookupError):process=None
receipt={'schema':'aura-original-idstop-submitted-1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'unit':UNIT,'submit_returncode':launch.returncode,'submit_stdout':launch.stdout,'submit_stderr':launch.stderr,
    'context':context,'context_path':str(TX/'wide-context.json'),'context_sha256':hashlib.sha256((TX/'wide-context.json').read_bytes()).hexdigest(),
    'unit_snapshot':state,'live_process_metadata_if_observed':process,'completion_claimed':False,'motion_requested':False}
create(TX/'idstop-submission.json',(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode())
print(json.dumps(receipt))
