"""Verify the REAL selected 23-pin candidate in RAM; no production/config/database writes."""
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
STARTUP_SHA = '07c5aa3b1c8da060e5a7d8520021bce7f167a8cf303b48a0a24f8e2a8b63035d'
SELECTED_SHA = 'a7402eb0f3e8d5391a95136d65759569be86eceeb75d830146a4b1d14cc81667'
VERIFIER_SHA = 'b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e'

def raw(path):
    p = Path(path)
    assert not p.is_symlink() and p.suffix not in ('.sqlite', '.sqlite3', '.db')
    assert p.stat().st_size <= 64000000
    return p.read_bytes()

def digest(path):
    return hashlib.sha256(raw(path)).hexdigest()

def health():
    c = http.client.HTTPConnection('127.0.0.1', 8790, timeout=2)
    try:
        c.request('GET', '/health'); r = c.getresponse(); data = r.read(1048577)
        assert r.status == 200 and len(data) <= 1048576
        return json.loads(data)
    finally:
        c.close()

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
assert digest(BUSINESS/'startup/config.json') == STARTUP_SHA
startup = json.loads(raw(BUSINESS/'startup/config.json')); AURA = Path(startup['runtime'])/'aura'
assert len(startup['component_sha256']) == 380
assert all(digest(AURA/name) == sha for name, sha in startup['component_sha256'].items())
gui = subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,Job'],capture_output=True,text=True,timeout=5)
unit = dict(line.split('=',1) for line in gui.stdout.splitlines() if '=' in line)
assert gui.returncode == 0 and unit['MainPID'] == '0' and not unit['Job']
assert json.loads(raw('/home/root/.local/share/aura-board-business/listening_preference.json')) == {'version':1,'enabled':False}
ui = json.loads(raw(AURA/'config/board_avatar_gtk.json')); spec = ui['board_business']['face_readback']
assert spec['sha256'] == SELECTED_SHA and digest(spec['path']) == SELECTED_SHA
selected = json.loads(raw(spec['path'])); assert len(selected['source_sha256']) == 23
assert all(digest(name) == sha for name, sha in selected['source_sha256'].items())
first = health(); time.sleep(1.1); last = health()
for key in ('pid','board_boot_id','service_epoch','camera_epoch'):
    assert first.get(key) is not None and first[key] == last[key]
assert last['pid'] == 1333 and last['board_boot_id'] == BOOT
assert last['capture_frames'] > first['capture_frames'] and last['detected_frames'] > first['detected_frames']
for item in (first,last):
    assert not any(item.get(k) for k in ('camera_error','detector_error','preview_error'))
    assert item['identity']['ready'] is True and not item['identity'].get('error')
    assert item['motion_command_emitted'] is False
proc = Path('/proc/1333'); birth = (proc/'stat').read_text().rsplit(')',1)[1].split()[19]
cmd = hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()
assert birth == '2359' and cmd == selected['camera_cmdline_sha256']
run_config = json.loads(raw('/home/root/aura-native-live-20261024/ops/be72669aa53de735/native-run-'+BOOT+'-1333/config.json'))
assert run_config['identity'] == {'enabled':True,'config':selected['identity_config']}
native = run_config['native_execution']
assert digest(native['source_manifest']) == native['source_manifest_sha256'] == '5e08f7cf587d74334ef24104ea01f79701629b48f2004fb772ce3f8ea82afd0d'
native_root = Path(native['source_manifest']).parent/'aura'
native_pins = json.loads(raw(native['source_manifest']))['files']
native_actual = {str(p.relative_to(native_root)):digest(p) for p in native_root.rglob('*.py') if not p.is_symlink()}
assert native_actual == native_pins and len(native_actual) == 222
op = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1/runtime-manifest.json')
assert digest(op) == '74e011db30a9d943a9512f7648190ac0c01060af06df1280d1e8ea006dc882ad'
op_pins = json.loads(raw(op))['files']; assert len(op_pins) == 7
assert all(digest(path) == sha for path,sha in op_pins.items())
candidate = copy.deepcopy(selected)
candidate.update(board_boot_id=BOOT,camera_pid=last['pid'],camera_start_ticks=birth)
assert {k:v for k,v in candidate.items() if k not in ('board_boot_id','camera_pid','camera_start_ticks')} == {k:v for k,v in selected.items() if k not in ('board_boot_id','camera_pid','camera_start_ticks')}
path = AURA/'board/runtime/audio/face_gallery_readback.py'
assert digest(path) == VERIFIER_SHA
tree = ast.parse(raw(path).decode('utf-8'))
klass = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name == 'FaceGalleryReadback')
verify_node = copy.deepcopy(next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name == '_verify'))
verify_node.decorator_list = []
space = {'Path':Path,'hashlib':hashlib,'json':json}
exec(compile(ast.Module(body=[verify_node],type_ignores=[]),str(path)+'::<metadata-only-_verify>','exec'),space)
space['_verify'](candidate)
identity = json.loads(raw(candidate['identity_config']))
local = json.loads(raw(AURA/'config/face_gallery_readback.local.json'))
differences = sorted(key for key in set(local)|set(selected) if key != 'source_sha256' and local.get(key) != selected.get(key))
source_overlap = set(local['source_sha256']) & set(selected['source_sha256'])
assert all(local['source_sha256'][key] == selected['source_sha256'][key] for key in source_overlap)
assert digest(BUSINESS/'startup/config.json') == STARTUP_SHA
assert (proc/'stat').read_text().rsplit(')',1)[1].split()[19] == birth
raw_candidate = (json.dumps(candidate,sort_keys=True,indent=2)+'\n').encode()
def project(h):
    return {key:h.get(key) for key in ('pid','board_boot_id','service_epoch','camera_epoch','capture_frames','detected_frames','capture_age_ms','observation_age_ms','motion_command_emitted')}
print(json.dumps({'schema':'aura-selected-gui-binding-candidate-precheck-1',
    'status':'RAM_CANDIDATE_ORIGINAL_VERIFY_PASS_SELECTED_PRODUCTION_STILL_STALE',
    'boot_id':BOOT,'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'startup_sha256':STARTUP_SHA,'selected_before_path':spec['path'],'selected_before_sha256':SELECTED_SHA,
    'ui_config_before_sha256':digest(AURA/'config/board_avatar_gtk.json'),
    'selected_source_files_verified':23,'native_python_files_verified':222,'operator_files_verified':7,
    'all_380_components_verified':True,'candidate_original_verify_passed':True,
    'verifier_source_sha256':VERIFIER_SHA,'candidate_sha256_if_serialized':hashlib.sha256(raw_candidate).hexdigest(),
    'candidate_changed_owner_fields':['board_boot_id','camera_pid','camera_start_ticks'],
    'candidate_preserves_all_23_source_pins':True,'candidate_preserves_model_database_ttl_and_all_non_owner_values':True,
    'candidate_owner':{'pid':last['pid'],'birth_ticks':birth,'command_sha256':cmd},
    'selected_vs_local_non_source_differences':differences,
    'selected_vs_local_source_overlap_count':len(source_overlap),
    'selected_extra_source_paths':sorted(set(selected['source_sha256'])-set(local['source_sha256'])),
    'camera_samples':[project(first),project(last)],
    'backend':identity.get('feature_backend',{}).get('kind'),'result_ttl_ms':identity.get('result_ttl_ms'),
    'database_opened':False,'template_or_conversation_exported':False,'candidate_written':False,
    'services_started':False,'audio_or_motion_requested':False,'board_mutations':False},sort_keys=True))
