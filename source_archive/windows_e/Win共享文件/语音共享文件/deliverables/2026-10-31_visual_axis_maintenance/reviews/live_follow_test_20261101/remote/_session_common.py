"""Pinned session helpers: stdlib only; none starts a device, service or inference by itself."""
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

BOOT='bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
ROOT=Path('/home/root/aura-face-follow-test-20261101-bebd3e7d-r2')
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
AURA=Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura')
CHECKPOINT=AURA.parent/'state/native-protection-checkpoint.json'
BUSINESS=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP_SHA='888faff24fef9d85ad75bbe19bc34d63956820ccd3e6dd3f674cfe4525ed0863'
APP='aura-visual-servo-b4096-wide-v1'
FW=Path('/lib/firmware/xilinx')/APP
RELEASE=Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
MANIFEST_SHA='6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf'

def read_regular(path,limit=64000000):
    path=Path(path)
    fd=os.open(str(path),os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        assert stat.S_ISREG(info.st_mode) and info.st_size<=limit
        with os.fdopen(fd,'rb',closefd=False) as handle:raw=handle.read(limit+1)
        assert len(raw)<=limit
        return raw
    finally:os.close(fd)

def digest(path):return hashlib.sha256(read_regular(path)).hexdigest()

def document(path):return json.loads(read_regular(path,1048576))

def atomic(path,value):
    path=Path(path);tmp=path.with_name(path.name+'.partial-'+str(os.getpid()))
    raw=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    fd=os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as handle:handle.write(raw);handle.flush();os.fsync(handle.fileno())
    os.replace(str(tmp),str(path))

def state():return document(ROOT/'session.json')

def save(value):
    value['updated_mono_ns']=time.monotonic_ns()
    atomic(ROOT/'session.json',value)

def systemd():
    result=subprocess.run(['systemctl','show','aura-camera-ui.service','--no-pager',
        '--property=MainPID,ActiveState,SubState,Restart,SendSIGKILL,TimeoutStopUSec,KillMode,Job'],
        capture_output=True,text=True,timeout=5)
    assert result.returncode==0
    return dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)

def get_json(port,path):
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=2)
    try:
        conn.request('GET',path);reply=conn.getresponse();raw=reply.read(1048577)
        assert reply.status==200 and len(raw)<=1048576
        return json.loads(raw)
    finally:conn.close()

def current_guard():
    assert os.geteuid()==0 and os.uname().machine=='aarch64'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert digest(BUSINESS/'startup/config.json')==STARTUP_SHA
    value=get_json(8783,'/api/state');handsfree=value.get('handsfree_dialogue',{})
    assert handsfree.get('state')=='PAUSED' and handsfree.get('enabled') is False
    assert handsfree.get('microphone_open') is False and value.get('playing') is False
    assert value.get('manual_pan',{}).get('face_follow',{}).get('running',False) is False

def dpu_users():
    values=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            maps=(path/'maps').read_text()
            if 'libvart' in maps or 'libaura_native_operator' in maps:
                values.append(int(path.name))
        except OSError:pass
    return sorted(values)

def checkpoint_ready(expected_pid,expected_birth):
    sys.path.insert(0,str(AURA))
    from board.vision.native_protection import load_business_checkpoint
    pin=dict(path=str(CHECKPOINT),sha256=digest(CHECKPOINT))
    loaded=load_business_checkpoint(pin,boot_id=BOOT)
    assert loaded['seed']['source_pid']==expected_pid
    assert loaded['seed']['source_birth_ticks']==expected_birth
    assert loaded['document']['source_unit_sha256']=='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
    return loaded

def verify_wide_files():
    assert digest(RELEASE/'candidate-manifest.json')==MANIFEST_SHA
    manifest=document(RELEASE/'candidate-manifest.json')
    assert manifest['app']==APP and manifest['build_id']==0x10282601
    assert all(digest(path)==sha for path,sha in manifest['runtime_files'].items())
    assert all(digest(RELEASE/'driver'/name)==sha for name,sha in manifest['payload_files'].items())
    return manifest

def firmware():return Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()

def wide_active():
    assert firmware()==APP+'.bit.bin'
    assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
    assert Path('/etc/vart.conf').read_text()=='firmware: '+str(FW/(APP+'.xclbin'))+'\n'

lock=os.open('/run/lock/aura-axis-takeover-bebd3e7d.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
