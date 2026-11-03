"""One normal GUI start after current configuration, camera and model-health checks."""
import ast
import copy
import datetime
import email.utils
import hashlib
import http.client
import json
from pathlib import Path
import subprocess

BOOT='903cfade-b93c-48fa-804e-379be1967313'
BUSINESS=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP=BUSINESS/'startup/config.json'
STARTUP_SHA='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
SELECTED_SHA='4d8f0c2bccea1c7a56761fbcb204f40ba3b3c2fc9efad76af778aff535d378ac'

def raw(path):
    path=Path(path)
    assert path.is_file() and not path.is_symlink()
    assert path.suffix not in ('.db','.sqlite','.sqlite3') and path.stat().st_size <= 64000000
    return path.read_bytes()

def digest(path):return hashlib.sha256(raw(path)).hexdigest()

def guard():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert digest(STARTUP)==STARTUP_SHA
    config=json.loads(raw(STARTUP));aura=Path(config['runtime'])/'aura'
    assert len(config['component_sha256'])==380
    assert all(digest(aura/key)==sha for key,sha in config['component_sha256'].items())
    ui=json.loads(raw(aura/'config/board_avatar_gtk.json'))
    selected=ui['board_business']['face_readback']
    assert selected['sha256']==SELECTED_SHA and digest(selected['path'])==SELECTED_SHA
    binding=json.loads(raw(selected['path']));assert len(binding['source_sha256'])==24
    assert all(digest(path)==sha for path,sha in binding['source_sha256'].items())
    verifier=aura/'board/runtime/audio/face_gallery_readback.py'
    assert digest(verifier)=='b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e'
    tree=ast.parse(raw(verifier).decode('utf-8'))
    klass=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='FaceGalleryReadback')
    node=copy.deepcopy(next(node for node in klass.body if isinstance(node,ast.FunctionDef) and node.name=='_verify'))
    node.decorator_list=[]
    space={'Path':Path,'hashlib':hashlib,'json':json}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(verifier)+'::<metadata-only-_verify>','exec'),space)
    space['_verify'](binding)
    process=Path('/proc/1333')
    assert (process/'stat').read_text().rsplit(')',1)[1].split()[19]=='2359'
    assert hashlib.sha256((process/'cmdline').read_bytes()).hexdigest()=='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
    assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0')==b'kv260-benchmark-b4096.bit.bin'
    assert json.loads(raw('/home/root/.local/share/aura-board-business/listening_preference.json'))=={'version':1,'enabled':False}
    for name,pid,active,sub in (('aura-avatar-ui.service','0','failed','failed'),('aura-camera-ui.service','1333','active','running')):
        result=subprocess.run(['systemctl','show',name,'--property=MainPID,Job,ActiveState,SubState'],capture_output=True,text=True,timeout=5)
        assert result.returncode==0
        assert dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)=={'MainPID':pid,'Job':'','ActiveState':active,'SubState':sub}

guard()
connection=http.client.HTTPConnection('192.168.50.1',8797,timeout=3)
try:
    connection.request('GET','/health');response=connection.getresponse();body=response.read(1048577)
    assert response.status==200 and len(body)<=1048576
    health=json.loads(body)
    assert health['ok'] is True and health['role']=='model_inference_only'
    backend=health['backend']
    assert backend['model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and backend['tts']=='omnivoice' and backend['num_step']==16 and backend['tts_ready'] is True
    assert backend['voice']['alive'] is True and not backend['voice']['error']
    date=email.utils.parsedate_to_datetime(response.getheader('Date'))
    clock_delta=abs((datetime.datetime.now(datetime.timezone.utc)-date).total_seconds())
    assert clock_delta<10
finally:connection.close()
guard()
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],capture_output=True,text=True,timeout=8)
print(json.dumps({'schema':'aura-gui-normal-start-request-1', 'utc':started,'boot_id':BOOT,
    'startup_sha256':STARTUP_SHA,'selected_binding_sha256':SELECTED_SHA,
    'components_verified':380,'selected_sources_verified':24,'camera_pid':1333,
    'saved_listening_enabled':False,'model_health_reachable':True,'health_clock_difference_seconds':clock_delta,
    'command':'systemctl start --no-block aura-avatar-ui.service','exit_code':result.returncode,
    'stderr_present':bool(result.stderr.strip()),'start_requested':True,'software_ready':False,
    'configuration_changed':False,'motion_command_requested':False}))
assert result.returncode==0
