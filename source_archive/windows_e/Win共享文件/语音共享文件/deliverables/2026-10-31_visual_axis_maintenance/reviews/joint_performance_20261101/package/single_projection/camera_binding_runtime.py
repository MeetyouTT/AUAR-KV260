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

"""Pure same-boot producer renewal; gallery, model and all old source pins are preserved."""
import copy

READBACK_FIELDS={'version','enabled','board_boot_id','camera_pid','camera_start_ticks',
    'camera_cmdline_sha256','camera_config','identity_config','source_sha256','database',
    'model_id','dimension','model_sha256','result_ttl_ms','backend'}

def binding_candidate(baseline,old_runtime,new_runtime,*,boot,old_pid,old_birth,new_pid,new_birth,
                      command_sha,new_runtime_path,new_runtime_sha,checkpoint_sha,model_id):
    def need(value,reason):
        if not value:raise ValueError(reason)
    need(set(baseline)==READBACK_FIELDS and baseline['version']==1 and baseline['enabled'] is True,
         'original complete enabled readback required')
    need(baseline['board_boot_id']==boot and baseline['camera_pid']==old_pid
         and str(baseline['camera_start_ticks'])==str(old_birth)
         and baseline['camera_cmdline_sha256']==command_sha,'original owner binding mismatch')
    need(type(new_pid) is int and new_pid>1 and new_pid!=old_pid,'distinct current producer required')
    need(baseline['dimension']==128 and baseline['backend']=='DPU_SFACE_INT8'
         and baseline['model_id']==model_id,'original model and backend required')
    need(old_runtime['identity']['config']==new_runtime['identity']['config']==baseline['identity_config'],
         'identity configuration changed')
    old=copy.deepcopy(old_runtime);new=copy.deepcopy(new_runtime)
    old['native_execution'].pop('seed');seed=new['native_execution'].pop('seed')
    need(old==new,'runtime change beyond the exact checkpoint pointer')
    need(seed['sha256']==checkpoint_sha and seed['path']==new_runtime['native_execution']['checkpoint_output'],
         'exact freshly consumed checkpoint pointer required')
    need(new_runtime_path not in baseline['source_sha256'],'new runtime source pin already present')
    result=copy.deepcopy(baseline)
    result.update(camera_pid=new_pid,camera_start_ticks=str(new_birth) if isinstance(baseline['camera_start_ticks'],str) else new_birth,
                  camera_cmdline_sha256=command_sha,camera_config=new_runtime_path)
    result['source_sha256'][new_runtime_path]=new_runtime_sha
    need(len(result['source_sha256'])==len(baseline['source_sha256'])+1,'exact one-pin extension required')
    return result

def verify_binding():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    wide_active();verify_wide_files()
    j=state()
    original=Path('/home/root/aura-board-owner-candidate-20261030/private-pin-bebd3e7d-229296-jpeg-aba-20261031/face_gallery_readback.local.json')
    assert digest(original)=='dc6071426041e3589f3c3eb42fe32ee9b82aca5d6d6d26bf0ac58832cdd5f446'
    baseline=document(original)
    for path,sha in baseline['source_sha256'].items():
        assert path!=baseline['database'] and not path.endswith(('.sqlite','.sqlite3','.db'))
        assert digest(path)==sha
    assert not (Path('/proc')/str(j['camera_pid'])).exists()
    proc=Path('/proc')/str(j['restored_camera_pid'])
    assert digest(proc/'cmdline')==j['restored_camera_command_sha256']
    birth=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]);assert birth==j['restored_camera_birth']
    assert dpu_users()==[j['restored_camera_pid']] and int(systemd()['MainPID'])==j['restored_camera_pid']
    closed=document(CHECKPOINT)
    assert digest(CHECKPOINT)==j['checkpoint_sha256'] and closed['seed']==j['checkpoint_seed']
    assert closed['auxiliary']==j['checkpoint_auxiliary'] and closed['source_unit_sha256']=='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
    marker=CHECKPOINT.with_name(CHECKPOINT.name+'.native-consumed-'+j['checkpoint_sha256'])
    assert read_regular(marker)==(j['checkpoint_sha256']+'\n').encode()
    audit=document(OPS/'pan-face-edge-v5/native-operator-v1'/('recovery-audit-'+str(j['restored_camera_pid'])+'.json'))
    assert audit['exact_seed_before_operator_request']==closed['seed'] and audit['checkpoint_sha256']==j['checkpoint_sha256']
    runpath=OPS/('native-run-'+BOOT+'-'+str(j['restored_camera_pid']))/'config.json'
    new_runtime=document(runpath);old_runtime=document(baseline['camera_config'])
    h=get_json(8790,'/health');handoff=h['dpu_schedule']['protection_handoff']
    assert h['pid']==j['restored_camera_pid'] and h['identity']['ready'] is True
    assert h['camera_error']==h['detector_error']==h['identity']['error']==''
    assert handoff['seed_sha256']==j['checkpoint_sha256'] and handoff['source_pid']==j['camera_pid']
    assert int(handoff['source_birth_ticks'])==j['camera_birth'] and h['dpu_schedule']['owner_fenced'] is False
    assert h['dpu_schedule']['primary_calls']>=closed['seed']['primary_calls']
    assert h['dpu_schedule']['primary_period_overruns']>=closed['seed']['primary_period_overruns']
    identity=document(baseline['identity_config'])
    assert identity['database']==baseline['database'] and identity['model_id']==baseline['model_id']
    candidate=binding_candidate(baseline,old_runtime,new_runtime,boot=BOOT,old_pid=j['camera_pid'],old_birth=j['camera_birth'],
        new_pid=j['restored_camera_pid'],new_birth=birth,command_sha=j['restored_camera_command_sha256'],
        new_runtime_path=str(runpath),new_runtime_sha=digest(runpath),checkpoint_sha=j['checkpoint_sha256'],model_id=h['identity']['model_id'])
    second=get_json(8790,'/health')
    assert all(second[k]==h[k] for k in ('pid','board_boot_id','service_epoch','camera_epoch'))
    assert digest(proc/'cmdline')==candidate['camera_cmdline_sha256']
    proof_path=ROOT/'camera-binding/proof.json'
    proof=document(proof_path)
    assert digest(proof_path)=='e486fc93588d5054c622ac2ea2737f5db952174b3193710c015aa5564107697d'
    assert proof['candidate']==j['camera_readback']
    assert digest(proof['candidate']['path'])==proof['candidate']['sha256']
    assert document(proof['candidate']['path'])==candidate
    assert proof['service_epoch']==h['service_epoch'] and proof['camera_epoch']==h['camera_epoch']
    return candidate,proof
