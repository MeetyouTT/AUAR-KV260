"""One original GUI start; EXPECTED is filled only from the returned live phase."""
import ast
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import time

EXPECTED = None  # ROOT_FRESH_EXPECTED

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def unit(name):
    r = subprocess.run(['systemctl', 'show', name,
        '--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus,Restart,KillMode,SendSIGKILL,TimeoutStopUSec'],
        capture_output=True, text=True, timeout=4)
    assert r.returncode == 0
    return dict(row.split('=', 1) for row in r.stdout.splitlines() if '=' in row)

def owner(pid):
    path = Path('/proc') / str(pid)
    return {'pid': int(pid), 'birth_ticks': path.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19],
            'command_sha256': digest(path / 'cmdline')}

def camera():
    u = unit('aura-camera-ui.service')
    assert u['MainPID'] == str(EXPECTED['camera_owner']['pid'])
    assert u['ActiveState'] == 'active' and u['SubState'] == 'running' and not u['Job']
    assert owner(int(u['MainPID'])) == EXPECTED['camera_owner']
    assert digest(EXPECTED['camera_config']['path']) == EXPECTED['camera_config']['sha256']

def stopped_gui():
    u = unit('aura-avatar-ui.service')
    assert u['MainPID'] == '0' and u['ActiveState'] == 'inactive' and u['SubState'] == 'dead' and not u['Job']
    assert u['Result'] == 'success' and u['ExecMainStatus'] == '0'
    assert {k: u[k] for k in ('Restart', 'KillMode', 'SendSIGKILL', 'TimeoutStopUSec')} == EXPECTED['original_GUI_properties']
    return u

def create(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    fd = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

assert type(EXPECTED) is dict, 'Unbound local template must never execute'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == EXPECTED['boot_id']
startup_path = Path(EXPECTED['startup_path'])
raw = startup_path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == EXPECTED['startup_sha256']
startup = json.loads(raw)
aura = Path(startup['runtime']) / 'aura'
assert startup['component_sha256'] == EXPECTED['component_sha256'] and len(startup['component_sha256']) == 380
assert all(digest(aura / k) == v for k, v in startup['component_sha256'].items())
assert all(startup['component_sha256'][k] == v for k, v in EXPECTED['identity_four_core'].items())
camera()
before = stopped_gui()
assert json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes()) == {
    'version': 1, 'enabled': False}
ui_path = aura / 'config/board_avatar_gtk.json'
assert digest(ui_path) == EXPECTED['GUI_config_sha256']
spec = json.loads(ui_path.read_bytes())['board_business']['face_readback']
assert spec['path'] == EXPECTED['selected_face_binding']['path']
assert spec['sha256'] == EXPECTED['selected_face_binding']['sha256']
binding_raw = Path(spec['path']).read_bytes()
assert hashlib.sha256(binding_raw).hexdigest() == spec['sha256']
binding = json.loads(binding_raw)
assert len(binding['source_sha256']) == EXPECTED['selected_face_binding']['source_pin_count']
assert binding['source_sha256'][EXPECTED['camera_config']['path']] == EXPECTED['camera_config']['sha256']
verifier = aura / 'board/runtime/audio/face_gallery_readback.py'
source = verifier.read_bytes()
assert hashlib.sha256(source).hexdigest() == 'b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e'
tree = ast.parse(source)
klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'FaceGalleryReadback')
method = copy.deepcopy(next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == '_verify'))
method.decorator_list = []
space = {'Path': Path, 'hashlib': hashlib, 'json': json}
exec(compile(ast.Module(body=[method], type_ignores=[]), str(verifier) + '::<pure-metadata-verify>', 'exec'), space)
space['_verify'](binding)
c = http.client.HTTPConnection('192.168.50.1', 8797, timeout=3)
try:
    sent = time.monotonic()
    c.request('GET', '/health')
    response = c.getresponse()
    elapsed = time.monotonic() - sent
    assert response.status == 200 and response.getheader('Date') and elapsed <= 1.
    body = response.read(1048577)
    assert len(body) <= 1048576
    health = json.loads(body)
    backend = health['backend']
    assert health['ok'] is True and health['role'] == 'model_inference_only'
    assert backend['model'] == 'aura-qwen3.8-27b-abliterated:iq4_xs'
    assert backend['tts'] == 'omnivoice' and backend['num_step'] == 16
    assert backend['tts_ready'] is True and backend['voice']['alive'] is True
finally:
    c.close()
tx = Path(EXPECTED['transaction_path'])
assert tx.parent == Path('/home/root/aura-5090-recovery-20261102-a6d4a069')
assert tx.parent.resolve() == tx.parent and not os.path.lexists(tx)
tx.mkdir(mode=0o700)
create(tx / 'intent.json', {'schema': 'aura-original-gui-recovery-start-intent-1',
    'boot_id': EXPECTED['boot_id'], 'board_monotonic': time.monotonic(),
    'startup_sha256': EXPECTED['startup_sha256'], 'camera_owner': EXPECTED['camera_owner'],
    'phase_sha256': EXPECTED['phase_sha256'], 'single_normal_start': True,
    'saved_listening_remains_false': True, 'original_gui_properties': before})
assert startup_path.read_bytes() == raw
camera()
stopped_gui()
create(tx / 'submission-intent.json', {'single_submission': True, 'board_monotonic': time.monotonic()})
r = subprocess.run(['systemctl', 'start', '--no-block', 'aura-avatar-ui.service'], capture_output=True, timeout=8)
receipt = {'schema': 'aura-original-gui-recovery-start-result-1', 'boot_id': EXPECTED['boot_id'],
    'board_monotonic': time.monotonic(), 'normal_start_submitted_once': True,
    'submission_returncode': r.returncode, 'startup_sha256': EXPECTED['startup_sha256'],
    'camera_owner': EXPECTED['camera_owner'], 'pure_selected_binding_verified': True,
    'source380_and_four_core_verified': True, 'listening_enabled': False,
    'GUI_unit': unit('aura-avatar-ui.service'), 'ready_claimed': False,
    'axis_or_config_or_identity_or_model_changes': False}
create(tx / 'submission-result.json', receipt)
print(json.dumps(receipt))
raise SystemExit(0 if r.returncode == 0 else 2)
