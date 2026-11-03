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
import time

BOOT='903cfade-b93c-48fa-804e-379be1967313'
BUSINESS=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP=BUSINESS/'startup/config.json'
STARTUP_SHA='3f5e81abc20ce5169ac91ae302611cba8958175a6a2bdb615fd9b858353120d5'
SELECTED_SHA='9ab2533d2c3000d61095f54de2e8199f53461ac085e2f58230ab36149be6af1f'

def raw(path):
    path=Path(path)
    assert path.is_file() and not path.is_symlink()
    assert path.suffix not in ('.db','.sqlite','.sqlite3') and path.stat().st_size <= 64000000
    return path.read_bytes()

def digest(path):return hashlib.sha256(raw(path)).hexdigest()

def platform():
    assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0') == b'aura-visual-servo-b4096-wide-v1.bit.bin'
    assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip() == 'operating'
    assert Path('/etc/vart.conf').read_bytes() == b'firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-wide-v1/aura-visual-servo-b4096-wide-v1.xclbin\n'
    assert digest('/sys/firmware/fdt') == 'd68bc147f22f5ab23bc60f0c2762af4bcd7b64340953e9c948e28ffa6b80f7ca'
    overlays = Path('/sys/kernel/config/device-tree/overlays')
    assert sorted(p.name for p in overlays.iterdir()) == ['aura-visual-servo-b4096-wide-v1_image_1']
    assert (overlays/'aura-visual-servo-b4096-wide-v1_image_1/status').read_text().strip() == 'applied'
    assert Path('/sys/bus/platform/drivers/zocl-drm/axi:zyxclmm_drm').resolve(strict=True) == Path('/sys/devices/platform/axi/axi:zyxclmm_drm')
    assert Path('/sys/class/drm/renderD128/device').resolve(strict=True) == Path('/sys/devices/platform/axi/axi:zyxclmm_drm')

def guard():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert digest(STARTUP)==STARTUP_SHA
    config=json.loads(raw(STARTUP));aura=Path(config['runtime'])/'aura'
    assert len(config['component_sha256'])==380
    assert all(digest(aura/key)==sha for key,sha in config['component_sha256'].items())
    assert digest(aura/'config/board_avatar_gtk.json')=='fc98455a5586cc4f1896f5472ec9b204bd7ff2b0c5be2798ba5cab1788b9b959'
    assert digest(aura/'config/face_gallery_readback.local.json')=='e203e6ffe973397464791eb07f12e0bd0c24658988c119e9d7d75685c4e41986'
    ui=json.loads(raw(aura/'config/board_avatar_gtk.json'))
    selected=ui['board_business']['face_readback']
    assert selected['sha256']==SELECTED_SHA and digest(selected['path'])==SELECTED_SHA
    binding=json.loads(raw(selected['path']));assert len(binding['source_sha256'])==25
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
    process=Path('/proc/79866')
    assert (process/'stat').read_text().rsplit(')',1)[1].split()[19]=='2265436'
    assert hashlib.sha256((process/'cmdline').read_bytes()).hexdigest()=='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
    platform()
    assert json.loads(raw('/home/root/.local/share/aura-board-business/listening_preference.json'))=={'version':1,'enabled':False}
    for name,pid,active,sub in (('aura-avatar-ui.service','0','inactive','dead'),('aura-camera-ui.service','79866','active','running')):
        result=subprocess.run(['systemctl','show',name,'--property=MainPID,Job,ActiveState,SubState'],capture_output=True,text=True,timeout=5)
        assert result.returncode==0
        assert dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)=={'MainPID':pid,'Job':'','ActiveState':active,'SubState':sub}


def camera_health():
    c=http.client.HTTPConnection('127.0.0.1',8790,timeout=3)
    try:
        c.request('GET','/health');r=c.getresponse();body=r.read(2097153)
        assert r.status==200 and len(body)<=2097152
        value=json.loads(body)
        assert value.get('pid')==79866 and value.get('board_boot_id')==BOOT
        assert not any(value.get(k) for k in ('camera_error','detector_error','preview_error'))
        identity=value.get('identity',{})
        assert isinstance(identity,dict) and identity.get('ready') is True and not identity.get('error')
        assert value.get('motion_command_emitted') is False
        fields={k:value[k] for k in ('capture_frames','detected_frames')}
        assert all(type(v) is int and v>=0 for v in fields.values())
        return fields
    finally:c.close()

# GET health is RAM-filtered. No camera stop, FPGA or Native calls.
guard()
camera_before=camera_health();time.sleep(1.2);camera_after=camera_health()
assert all(camera_after[k]>camera_before[k] for k in camera_before)
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
print(json.dumps({'schema':'aura-gui-restored-camera-normal-start-request-2', 'utc':started,'boot_id':BOOT,
    'startup_sha256':STARTUP_SHA,'selected_binding_sha256':SELECTED_SHA,
    'components_verified':380,'selected_sources_verified':25,'camera_pid':79866,
    'saved_listening_enabled':False,'model_health_reachable':True,'health_clock_difference_seconds':clock_delta,
    'command':'systemctl start --no-block aura-avatar-ui.service','exit_code':result.returncode,
    'stderr_present':bool(result.stderr.strip()),'start_requested':True,'software_ready':False,
    'configuration_changed':False,'motion_command_requested':False,
    'camera_health_advancing':True,'wide_platform_verified':True}))
assert result.returncode==0
