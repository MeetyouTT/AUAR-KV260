"""Current platform/axis metadata only. No client, device, control or project imports."""
import datetime
import hashlib
import http.client
import json
from pathlib import Path

BOOT='903cfade-b93c-48fa-804e-379be1967313'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
startup=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert hashlib.sha256(startup.read_bytes()).hexdigest()=='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
firmware=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode('ascii')
state=Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()
vart=Path('/etc/vart.conf').read_bytes();assert len(vart)<4096
candidate=Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c/candidate-manifest.json')
candidate_sha=hashlib.sha256(candidate.read_bytes()).hexdigest()
assert candidate_sha=='6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf'
connection=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
try:
    connection.request('GET','/api/state');response=connection.getresponse();data=response.read(2097153)
    assert response.status==200 and len(data)<=2097152
    value=json.loads(data);pan=value.get('manual_pan',{})
    manual={'state':pan.get('state') if pan.get('state') in ('FAULT','UNAVAILABLE','READY','MOVING','CONNECTING','CLOSED') else None,
        'following':pan.get('automatic_following') is True,
        'pulse_available':type(pan.get('pulse_us')) in (int,float),
        'readback_available':isinstance(pan.get('readback'),dict),
        'error_present':bool(pan.get('error'))}
    value=data=None
finally:connection.close()
vsrv=[];dpu=[];unreadable=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:
        text=(proc/'maps').read_text()
        if 'libvsrv.so' in text or '/dev/mem' in text:vsrv.append(int(proc.name))
        targets=[]
        for fd in (proc/'fd').iterdir():
            try:targets.append(str(fd.readlink()))
            except FileNotFoundError:continue
        if 'libvart-runner.so' in text or any('/dev/dri/renderD' in p or p=='/dev/dpu' for p in targets):
            dpu.append(int(proc.name))
    except (FileNotFoundError,ProcessLookupError):continue
    except PermissionError:
        if proc.exists():unreadable.append(int(proc.name))
print(json.dumps({'schema':'aura-joint-trial-platform-readonly-1',
    'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':BOOT,
    'firmware':firmware,'fpga_state':state,'fdt_sha256':hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest(),
    'vart_sha256':hashlib.sha256(vart).hexdigest(),
    'vart_is_benchmark':vart==b'firmware: /lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin\n',
    'wide_candidate_manifest_sha256':candidate_sha,'wide_currently_active':firmware=='aura-visual-servo-b4096-wide-v1.bit.bin',
    'manual_pan':manual,'native_register_map_owners':sorted(vsrv),'dpu_owner_pids':sorted(dpu),
    'unreadable_alive_processes':sorted(unreadable),
    'axis_ready_for_joint_trial':manual['state']=='READY' and manual['readback_available'] and firmware!='kv260-benchmark-b4096.bit.bin',
    'board_mutations':False,'device_opened':False,'motion_sent':False,'database_opened':False}))
