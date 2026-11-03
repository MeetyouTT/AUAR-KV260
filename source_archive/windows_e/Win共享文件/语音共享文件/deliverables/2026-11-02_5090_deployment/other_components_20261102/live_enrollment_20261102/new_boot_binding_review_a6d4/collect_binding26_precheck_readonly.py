"""Verify selected production candidate with all existing 25 pins plus this new-boot camera run config."""
import ast
import copy
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import time

BOOT = 'a6d4a069-e9b0-4065-8df7-dc23556b168e'
BUSINESS = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP_SHA = '680fd752c74e75bfbbcd73a296f21f4f39134ce4863a6bc30643c7e77feae1c0'
SELECTED_SHA = '9ab2533d2c3000d61095f54de2e8199f53461ac085e2f58230ab36149be6af1f'
VERIFIER_SHA = 'b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e'
UI_SHA = 'fc98455a5586cc4f1896f5472ec9b204bd7ff2b0c5be2798ba5cab1788b9b959'
CMD_SHA = 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
DEFAULT_SHA = 'e203e6ffe973397464791eb07f12e0bd0c24658988c119e9d7d75685c4e41986'
RUN = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/native-run-'+BOOT+'-1332/config.json')

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
    assert v in ({'MainPID':'0','Job':'','ActiveState':'inactive','SubState':'dead'}, {'MainPID':'0','Job':'','ActiveState':'failed','SubState':'failed'})
    p=subprocess.run(['systemctl','show','aura-camera-ui.service',
        '--property=MainPID,Job,ActiveState,SubState'],capture_output=True,text=True,timeout=5)
    assert p.returncode == 0
    v=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
    assert v == {'MainPID':'1332','Job':'','ActiveState':'active','SubState':'running'}

def owner():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
    proc=Path('/proc/1332')
    assert (proc/'stat').read_text().rsplit(')',1)[1].split()[19] == '2236'
    assert hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest() == CMD_SHA

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
assert len(selected['source_sha256']) == 25 and str(RUN) not in selected['source_sha256']
assert all(digest(name) == sha for name,sha in selected['source_sha256'].items())
first=health(); time.sleep(1.1); last=health()
for key in ('pid','board_boot_id','service_epoch','camera_epoch'):
    assert first.get(key) is not None and first[key] == last[key]
assert last['pid'] == 1332 and last['board_boot_id'] == BOOT
assert last['capture_frames'] > first['capture_frames'] and last['detected_frames'] > first['detected_frames']
for item in (first,last):
    assert not any(item.get(k) for k in ('camera_error','detector_error','preview_error'))
    assert item['identity']['ready'] is True and not item['identity'].get('error')
    assert item['motion_command_emitted'] is False
run_config=json.loads(raw(RUN)); run_sha=digest(RUN)
assert run_sha == 'b9656e728f828dd6e450cae901b978d58b42fc7d4eddfd1ae322f3046a6f8f70'
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
candidate.update(board_boot_id=BOOT,camera_pid=1332,camera_start_ticks='2236',camera_config=str(RUN))
candidate['source_sha256'][str(RUN)]=run_sha
excluded={'board_boot_id','camera_pid','camera_start_ticks','camera_config','source_sha256'}
assert {k:v for k,v in candidate.items() if k not in excluded} == {k:v for k,v in selected.items() if k not in excluded}
assert len(candidate['source_sha256']) == 26
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
units(); owner()
raw_candidate=(json.dumps(candidate,sort_keys=True,indent=2)+'\n').encode()
def project(h):
    return {k:h.get(k) for k in ('pid','board_boot_id','service_epoch','camera_epoch','capture_frames','detected_frames','capture_age_ms','observation_age_ms','motion_command_emitted')}

# Build only RAM bytes/differences. This collector has no board write or service command.
DEST=Path('/home/root/aura-5090-recovery-20261102-a6d4a069/gui-selected-1332-26pins-v1/face_gallery_readback.local.json')
assert not DEST.exists() and not DEST.is_symlink()
new_ui=copy.deepcopy(ui)
new_ui['board_business']['face_readback']={'path':str(DEST),'sha256':hashlib.sha256(raw_candidate).hexdigest()}
ui_after=(json.dumps(new_ui,sort_keys=True,indent=2)+'\n').encode()
new_startup=copy.deepcopy(startup)
new_startup['component_sha256']['config/board_avatar_gtk.json']=hashlib.sha256(ui_after).hexdigest()
startup_after=(json.dumps(new_startup,sort_keys=True,indent=2)+'\n').encode()
assert {k:v for k,v in new_startup.items() if k!='component_sha256'}=={k:v for k,v in startup.items() if k!='component_sha256'}
assert [k for k,v in startup['component_sha256'].items() if new_startup['component_sha256'][k]!=v]==['config/board_avatar_gtk.json']
assert json.loads(raw(AURA/'config/board_avatar_gtk.json'))==ui
print(json.dumps({'schema':'aura-new-boot-selected-gui-binding-precheck-26-1',
    'status':'RAM_26_PIN_CANDIDATE_ORIGINAL_VERIFY_PASS',
    'boot_id':BOOT,'host_clock_required_before_gui_start':True,
    'startup_before_sha256':STARTUP_SHA,'startup_after_sha256_if_serialized':hashlib.sha256(startup_after).hexdigest(),
    'ui_before_sha256':UI_SHA,'ui_after_sha256_if_serialized':hashlib.sha256(ui_after).hexdigest(),
    'selected_before_path':spec['path'],'selected_before_sha256':SELECTED_SHA,
    'new_selected_path':str(DEST),'candidate_sha256_if_serialized':hashlib.sha256(raw_candidate).hexdigest(),
    'candidate_document':candidate,'changed_component_keys':['config/board_avatar_gtk.json'],
    'native_python_files_verified':222,'operator_files_verified':7,'all_380_components_verified':True,
    'old_selected_25_pins_preserved':True,'candidate_source_files_verified':26,
    'original_verifier_passed':True,'verifier_source_sha256':VERIFIER_SHA,
    'camera_owner':{'pid':1332,'birth_ticks':'2236','command_sha256':CMD_SHA},
    'camera_run_config_path':str(RUN),'camera_run_config_sha256':run_sha,
    'camera_samples':[project(first),project(last)],'database_opened':False,
    'board_mutations':False,'services_controlled':False,'old_seed_or_checkpoint_replayed':False,
    'default_14_pin_binding_unchanged':True,'ui_other_fields_changed':False,
    'raw_identity_records_or_templates_or_images_read':False},sort_keys=True))
