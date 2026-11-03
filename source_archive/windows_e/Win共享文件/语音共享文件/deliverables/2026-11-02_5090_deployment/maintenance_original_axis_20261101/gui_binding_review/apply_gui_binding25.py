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

# The precheck above is the restored-camera 25-pin RAM-only collector through serialization.
# The host composes it with this transaction; no project code other than isolated _verify.
import argparse
import os
import stat
import sys
import uuid

parser=argparse.ArgumentParser(description='Guarded selected GUI binding replacement; never starts services')
parser.add_argument('--apply-selected-restored-camera-binding',action='store_true')
args=parser.parse_args()
TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/gui-selected-79866-25pins-v1')
DEST=TX/'face_gallery_readback.local.json'
EXPECTED_CANDIDATE_SHA='9ab2533d2c3000d61095f54de2e8199f53461ac085e2f58230ab36149be6af1f'
assert hashlib.sha256(raw_candidate).hexdigest() == EXPECTED_CANDIDATE_SHA
assert digest(RUN) == 'c8df0795664d21d52eab3a4f1cf55e0d1a721577d547c512e83ee1931d80871d'
assert not TX.exists() and not TX.is_symlink()
assert TX.parent.is_dir() and TX.parent.resolve(strict=True) == TX.parent
assert os.geteuid() == 0 and TX.parent.stat().st_uid == 0
STARTUP=BUSINESS/'startup/config.json'
UI=AURA/'config/board_avatar_gtk.json'
before={STARTUP:raw(STARTUP),UI:raw(UI)}
assert hashlib.sha256(before[STARTUP]).hexdigest() == STARTUP_SHA
assert hashlib.sha256(before[UI]).hexdigest() == UI_SHA
new_ui=copy.deepcopy(ui)
assert set(spec) == {'path','sha256'}
new_ui['board_business']['face_readback']={'path':str(DEST),'sha256':EXPECTED_CANDIDATE_SHA}
ui_after=(json.dumps(new_ui,sort_keys=True,indent=2)+'\n').encode()
new_startup=copy.deepcopy(startup)
new_startup['component_sha256']['config/board_avatar_gtk.json']=hashlib.sha256(ui_after).hexdigest()
startup_after=(json.dumps(new_startup,sort_keys=True,indent=2)+'\n').encode()
assert {k:v for k,v in new_startup.items() if k!='component_sha256'} == {k:v for k,v in startup.items() if k!='component_sha256'}
assert [k for k,v in startup['component_sha256'].items() if new_startup['component_sha256'][k]!=v] == ['config/board_avatar_gtk.json']
assert new_startup['component_sha256']['config/face_gallery_readback.local.json'] == DEFAULT_SHA
after={UI:ui_after,STARTUP:startup_after}
receipt={'schema':'aura-gui-restored-camera-binding-transaction-2','boot_id':BOOT,
    'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'transaction_directory':str(TX),'status':'DRY_RUN_READY',
    'selected_before_path':spec['path'],'selected_before_sha256':SELECTED_SHA,
    'new_selected_path':str(DEST),'new_selected_sha256':EXPECTED_CANDIDATE_SHA,
    'default_14_pin_binding_sha256':DEFAULT_SHA,
    'startup_before_sha256':STARTUP_SHA,'startup_after_sha256':hashlib.sha256(startup_after).hexdigest(),
    'ui_before_sha256':UI_SHA,'ui_after_sha256':hashlib.sha256(ui_after).hexdigest(),
    'candidate_source_files_verified':25,'original_source_pins_preserved':24,
    'native_python_files_verified':222,'operator_files_verified':7,'components_verified':380,
    'changed_component_keys':['config/board_avatar_gtk.json'],
    'camera_owner':{'pid':79866,'birth_ticks':'2265436','command_sha256':CMD_SHA},
    'original_verifier_passed':True,'camera_samples':[project(first),project(last)],
    'services_started':False,'models_started_or_stopped':False,'fpga_reconfigured':False,
    'mmio_or_motion_requested':False,'database_opened_or_copied':False,
    'template_or_conversation_exported':False,'board_mutations':False}

def sync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def create(path,data,mode=0o600):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    sync_dir(path.parent)

def replace(path,expected,data):
    info=path.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == 0
    assert raw(path) == expected, 'Concurrent configuration change; replacement refused'
    temporary=path.with_name('.'+path.name+'.gui-selected-'+uuid.uuid4().hex+'.tmp')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,stat.S_IMODE(info.st_mode))
    try:
        with os.fdopen(fd,'wb') as stream:
            os.fchmod(stream.fileno(),stat.S_IMODE(info.st_mode))
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        assert raw(path) == expected, 'Concurrent configuration change; replacement refused'
        os.replace(temporary,path);sync_dir(path.parent)
        assert raw(path) == data
    finally:
        if temporary.exists():temporary.unlink()

def save_receipt():
    encoded=(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode()
    path=TX/'transaction.json'
    if path.exists():replace(path,raw(path),encoded)
    else:create(path,encoded)

if not args.apply_selected_restored_camera_binding:
    print(json.dumps(receipt,sort_keys=True));sys.exit(0)

# The normally stopped GUI and restored camera are checked again immediately before all writes.
units();owner();platform()
assert raw(STARTUP) == before[STARTUP] and raw(UI) == before[UI]
assert digest(spec['path']) == SELECTED_SHA and digest(AURA/'config/face_gallery_readback.local.json') == DEFAULT_SHA
assert json.loads(raw('/home/root/.local/share/aura-board-business/listening_preference.json')) == {'version':1,'enabled':False}
TX.mkdir(mode=0o700);sync_dir(TX.parent)
receipt.update(status='PREPARED_BACKUPS_PENDING',board_mutations=True)
save_receipt()
changed=[]
try:
    create(TX/'startup.before.json',before[STARTUP])
    create(TX/'board_avatar_gtk.before.json',before[UI])
    create(TX/'selected_binding.before.json',raw(spec['path']))
    create(TX/'face_gallery_readback.local.json',raw_candidate)
    assert digest(DEST) == EXPECTED_CANDIDATE_SHA
    space['_verify'](json.loads(raw(DEST)))
    receipt['status']='BACKUPS_AND_CANDIDATE_VERIFIED';save_receipt()
    for path in (UI,STARTUP):
        units();owner();platform()
        changed.append(path)  # Include replace-after-rename failure in rollback set.
        replace(path,before[path],after[path])
        receipt['status']='UI_WRITTEN_STARTUP_PENDING' if path==UI else 'CONFIGURATION_WRITTEN'
        save_receipt()
    assert digest(STARTUP) == receipt['startup_after_sha256']
    assert all(digest(AURA/name) == sha for name,sha in new_startup['component_sha256'].items())
    assert digest(spec['path']) == SELECTED_SHA
    assert digest(AURA/'config/face_gallery_readback.local.json') == DEFAULT_SHA
    assert all(digest(name)==sha for name,sha in candidate['source_sha256'].items())
    assert digest(RUN) == run_sha
    assert json.loads(raw(RUN))['identity'] == {'enabled':True,'config':candidate['identity_config']}
    assert {str(p.relative_to(native_root)):digest(p) for p in native_root.rglob('*.py') if not p.is_symlink()} == native_pins
    assert all(digest(path)==sha for path,sha in op_pins.items())
    space['_verify'](json.loads(raw(DEST)))
    assert json.loads(raw(UI))['board_business']['face_readback'] == {'path':str(DEST),'sha256':EXPECTED_CANDIDATE_SHA}
    post=health()
    assert post['capture_frames'] > last['capture_frames'] and post['detected_frames'] > last['detected_frames']
    for key in ('pid','board_boot_id','service_epoch','camera_epoch'):
        assert post[key] == last[key]
    assert post['identity']['ready'] is True and not post['identity'].get('error')
    assert not any(post.get(k) for k in ('camera_error','detector_error','preview_error'))
    assert post['motion_command_emitted'] is False
    assert json.loads(raw('/home/root/.local/share/aura-board-business/listening_preference.json')) == {'version':1,'enabled':False}
    units();owner();platform()
    receipt.update(status='SELECTED_BINDING_UPDATED_GUI_STILL_STOPPED',
        completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        post_camera_sample=project(post),post_component_sha256_verified=True,
        post_original_verifier_passed=True,old_selected_binding_unchanged=True,
        default_14_pin_binding_unchanged=True,services_started=False)
    save_receipt()
except BaseException as exc:
    receipt.update(status='FAILED_ROLLBACK_PENDING',error_type=type(exc).__name__)
    rollbacks=[]
    for path in reversed(changed):
        try:
            units();owner();platform()
            current=raw(path)
            if current == after[path]:
                replace(path,after[path],before[path]);status='ORIGINAL_BYTES_RESTORED'
            elif current == before[path]:status='ALREADY_ORIGINAL'
            else:raise RuntimeError('Concurrent change; rollback refused')
            rollbacks.append({'path':str(path),'status':status})
        except BaseException as rollback_exc:
            rollbacks.append({'path':str(path),'status':'ROLLBACK_REFUSED_OR_FAILED',
                              'error_type':type(rollback_exc).__name__})
    receipt['rollback_results']=rollbacks
    receipt['status']='FAILED_ORIGINAL_CONFIG_RESTORED' if all(x['status'] in ('ORIGINAL_BYTES_RESTORED','ALREADY_ORIGINAL') for x in rollbacks) else 'FAILED_REQUIRES_RECONCILIATION'
    save_receipt()
    print(json.dumps(receipt,sort_keys=True),flush=True)
    raise
print(json.dumps(receipt,sort_keys=True))
