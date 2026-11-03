"""Verify selected production candidate with all existing 24 pins plus the restored camera run config."""
import ast
import copy
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import time

BOOT = '903cfade-b93c-48fa-804e-379be1967313'
BUSINESS = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP_SHA = '0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f'
SELECTED_SHA = '4d8f0c2bccea1c7a56761fbcb204f40ba3b3c2fc9efad76af778aff535d378ac'
VERIFIER_SHA = 'b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e'
UI_SHA = 'fc21e6f2ef831442b08966957fa7aeb744a9b74124ee8778edc40397285626cd'
CMD_SHA = 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
DEFAULT_SHA = 'e203e6ffe973397464791eb07f12e0bd0c24658988c119e9d7d75685c4e41986'
RUN = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/native-run-'+BOOT+'-79866/config.json')

def raw(path):
    p=Path(path)
    assert not p.is_symlink() and p.is_file() and p.suffix not in ('.sqlite','.sqlite3','.db')
    assert p.stat().st_size <= 64000000
    return p.read_bytes()

def digest(path):
    return hashlib.sha256(raw(path)).hexdigest()

def health():
    c=http.client.HTTPConnection('127.0.0.1',8790,timeout=2)
    try:
        c.request('GET','/health'); r=c.getresponse(); data=r.read(1048577)
        assert r.status == 200 and len(data) <= 1048576
        return json.loads(data)
    finally:
        c.close()

def units():
    p=subprocess.run(['systemctl','show','aura-avatar-ui.service',
        '--property=MainPID,Job,ActiveState,SubState'],capture_output=True,text=True,timeout=5)
    assert p.returncode == 0
    v=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
    assert v == {'MainPID':'0','Job':'','ActiveState':'inactive','SubState':'dead'}
    p=subprocess.run(['systemctl','show','aura-camera-ui.service',
        '--property=MainPID,Job,ActiveState,SubState'],capture_output=True,text=True,timeout=5)
    assert p.returncode == 0
    v=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
    assert v == {'MainPID':'79866','Job':'','ActiveState':'active','SubState':'running'}

def owner():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
    proc=Path('/proc/79866')
    assert (proc/'stat').read_text().rsplit(')',1)[1].split()[19] == '2265436'
    assert hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest() == CMD_SHA

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

platform()
units(); owner()
assert digest(BUSINESS/'startup/config.json') == STARTUP_SHA
startup=json.loads(raw(BUSINESS/'startup/config.json')); AURA=Path(startup['runtime'])/'aura'
assert len(startup['component_sha256']) == 380
assert all(digest(AURA/name) == sha for name,sha in startup['component_sha256'].items())
assert digest(AURA/'config/board_avatar_gtk.json') == UI_SHA
assert digest(AURA/'config/face_gallery_readback.local.json') == DEFAULT_SHA
assert json.loads(raw('/home/root/.local/share/aura-board-business/listening_preference.json')) == {'version':1,'enabled':False}
ui=json.loads(raw(AURA/'config/board_avatar_gtk.json')); spec=ui['board_business']['face_readback']
assert spec['sha256'] == SELECTED_SHA and digest(spec['path']) == SELECTED_SHA
selected=json.loads(raw(spec['path']))
assert len(selected['source_sha256']) == 24 and str(RUN) not in selected['source_sha256']
assert all(digest(name) == sha for name,sha in selected['source_sha256'].items())
first=health(); time.sleep(1.1); last=health()
for key in ('pid','board_boot_id','service_epoch','camera_epoch'):
    assert first.get(key) is not None and first[key] == last[key]
assert last['pid'] == 79866 and last['board_boot_id'] == BOOT
assert last['capture_frames'] > first['capture_frames'] and last['detected_frames'] > first['detected_frames']
for item in (first,last):
    assert not any(item.get(k) for k in ('camera_error','detector_error','preview_error'))
    assert item['identity']['ready'] is True and not item['identity'].get('error')
    assert item['motion_command_emitted'] is False
run_config=json.loads(raw(RUN)); run_sha=digest(RUN)
assert run_sha == 'c8df0795664d21d52eab3a4f1cf55e0d1a721577d547c512e83ee1931d80871d'
assert run_config['identity'] == {'enabled':True,'config':selected['identity_config']}
native=run_config['native_execution']
assert digest(native['source_manifest']) == native['source_manifest_sha256'] == '5e08f7cf587d74334ef24104ea01f79701629b48f2004fb772ce3f8ea82afd0d'
native_root=Path(native['source_manifest']).parent/'aura'
native_pins=json.loads(raw(native['source_manifest']))['files']
native_actual={str(p.relative_to(native_root)):digest(p) for p in native_root.rglob('*.py') if not p.is_symlink()}
assert native_actual == native_pins and len(native_actual) == 222
op=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1/runtime-manifest.json')
assert digest(op) == '74e011db30a9d943a9512f7648190ac0c01060af06df1280d1e8ea006dc882ad'
op_pins=json.loads(raw(op))['files']; assert len(op_pins) == 7
assert all(digest(path) == sha for path,sha in op_pins.items())
candidate=copy.deepcopy(selected)
candidate.update(board_boot_id=BOOT,camera_pid=79866,camera_start_ticks='2265436',camera_config=str(RUN))
candidate['source_sha256'][str(RUN)]=run_sha
excluded={'board_boot_id','camera_pid','camera_start_ticks','camera_config','source_sha256'}
assert {k:v for k,v in candidate.items() if k not in excluded} == {k:v for k,v in selected.items() if k not in excluded}
assert len(candidate['source_sha256']) == 25
assert all(candidate['source_sha256'][k] == v for k,v in selected['source_sha256'].items())
path=AURA/'board/runtime/audio/face_gallery_readback.py'
assert digest(path) == VERIFIER_SHA
tree=ast.parse(raw(path).decode())
klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FaceGalleryReadback')
node=copy.deepcopy(next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_verify'))
node.decorator_list=[]
space={'Path':Path,'hashlib':hashlib,'json':json}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(path)+'::<metadata-only-_verify>','exec'),space)
space['_verify'](candidate)
assert all(digest(name) == sha for name,sha in candidate['source_sha256'].items())
identity=json.loads(raw(candidate['identity_config']))
assert digest(BUSINESS/'startup/config.json') == STARTUP_SHA
units(); owner(); platform()
raw_candidate=(json.dumps(candidate,sort_keys=True,indent=2)+'\n').encode()
def project(h):
    return {k:h.get(k) for k in ('pid','board_boot_id','service_epoch','camera_epoch','capture_frames','detected_frames','capture_age_ms','observation_age_ms','motion_command_emitted')}
print(json.dumps({'schema':'aura-selected-restored-gui-binding-candidate-precheck-25-1',
    'status':'RAM_25_PIN_CANDIDATE_ORIGINAL_VERIFY_PASS_PRODUCTION_STILL_STALE',
    'boot_id':BOOT,'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'startup_sha256':STARTUP_SHA,'ui_config_before_sha256':UI_SHA,
    'selected_before_path':spec['path'],'selected_before_sha256':SELECTED_SHA,
    'default_14_pin_binding_sha256':DEFAULT_SHA,'candidate_source_files_verified':25,
    'candidate_preserves_all_24_source_pins':True,'actual_camera_config_path':str(RUN),
    'actual_camera_config_sha256':run_sha,'native_python_files_verified':222,'operator_files_verified':7,
    'all_380_components_verified':True,'candidate_original_verify_passed':True,
    'verifier_source_sha256':VERIFIER_SHA,'candidate_sha256_if_serialized':hashlib.sha256(raw_candidate).hexdigest(),
    'candidate_changed_keys':sorted(excluded),'candidate_preserves_model_database_ttl_and_other_parameters':True,
    'candidate_owner':{'pid':79866,'birth_ticks':'2265436','command_sha256':CMD_SHA},
    'camera_samples':[project(first),project(last)],'backend':identity.get('feature_backend',{}).get('kind'),
    'result_ttl_ms':identity.get('result_ttl_ms'),'database_opened':False,'template_or_conversation_exported':False,
    'candidate_written':False,'services_started':False,'audio_or_motion_requested':False,'board_mutations':False},sort_keys=True))
