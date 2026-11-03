"""Reversible current-boot test-off only. No microphone, model or GUI control."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import stat
import time
import uuid

EXPECTED = {'boot_id': 'a6d4a069-e9b0-4065-8df7-dc23556b168e', 'startup_path': '/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json', 'startup_sha256': '71431dc7d7ffcf8fa824f03ae984488afec22b96f546bd3cd66e002fca8f7883', 'gui_owner': {'pid': 1128353, 'birth_ticks': '7742281', 'command_sha256': '48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'}, 'gtk_owner': {'pid': 1128405, 'birth_ticks': '7747322', 'command_sha256': 'ddd3dcd7202153c7ed7eb108c8c287b03216af1e147c930611440bfb30b2c1fc'}, 'camera_owner': {'pid': 362659, 'birth_ticks': '2850120', 'command_sha256': 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'}}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def owner(value):
    path = Path('/proc') / str(value['pid'])
    assert path.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19] == value['birth_ticks']
    assert sha(path / 'cmdline') == value['command_sha256']


def create(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def current():
    connection = http.client.HTTPConnection('127.0.0.1', 8783, timeout=3)
    try:
        connection.request('GET', '/api/state')
        response = connection.getresponse()
        raw = response.read(2097153)
        assert response.status == 200 and len(raw) <= 2097152
        value = json.loads(raw)
    finally:
        connection.close()
    hands = value.get('handsfree_dialogue') or {}
    dialogue = (value.get('board_business') or {}).get('dialogue') or {}
    ack = dialogue.get('last_playback_ack') or {}
    token = ack.get('request_id')
    return dict(ui_page=value.get('ui_page'), phase=value.get('phase'),
        listening_enabled=hands.get('enabled'), microphone_open=hands.get('microphone_open'),
        handsfree_state=hands.get('state'), playing=bool(value.get('playing')),
        pending_job=bool(value.get('pending_job')), fault_count=(value.get('runtime_faults') or {}).get('count'),
        ack_committed=ack.get('committed'),
        ack_hash=hashlib.sha256(token.encode()).hexdigest()[:16] if isinstance(token, str) else None)


assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == EXPECTED['boot_id']
startup = Path(EXPECTED['startup_path'])
assert sha(startup) == EXPECTED['startup_sha256']
cfg = json.loads(startup.read_bytes())
aura = Path(cfg['runtime']) / 'aura'
assert len(cfg['component_sha256']) == 380
assert all(sha(aura / path) == digest for path, digest in cfg['component_sha256'].items())
for key in ('gui_owner', 'gtk_owner', 'camera_owner'):
    owner(EXPECTED[key])
flag = Path('/run/aura-dialogue-thinking-test.json')
assert not flag.is_symlink()
info = flag.stat()
assert stat.S_ISREG(info.st_mode)
raw = flag.read_bytes()
assert len(raw) <= 1024
assert json.loads(raw) == dict(version=1, enabled=True, board_boot_id=EXPECTED['boot_id'], num_predict=192)
before = current()
transaction = Path('/run') / ('aura-no-output-recovery-' + uuid.uuid4().hex)
transaction.mkdir(mode=0o700)
create(transaction / 'thinking-flag.before.json', raw)
intent = dict(schema='aura-no-output-test-off-intent-1', reason='Restore ordinary replies after reproduced temporary-thinking failure',
    boot_id=EXPECTED['boot_id'], startup_sha256=EXPECTED['startup_sha256'], flag_before_sha256=hashlib.sha256(raw).hexdigest(),
    board_monotonic=time.monotonic(), state_before=before, microphone_enable_calls=0, GUI_restarts=0)
create(transaction / 'intent.json', (json.dumps(intent, indent=2) + '\n').encode())
assert flag.read_bytes() == raw
latest = flag.stat()
assert (latest.st_dev, latest.st_ino) == (info.st_dev, info.st_ino)
flag.unlink()
fd = os.open('/run', os.O_RDONLY | os.O_DIRECTORY)
try:
    os.fsync(fd)
finally:
    os.close(fd)
assert not flag.exists()
import sys
sys.path.insert(0, str(aura))
from board.runtime.board_dialogue import dialogue_thinking_test_options
assert dialogue_thinking_test_options(EXPECTED['boot_id']) == {}
assert sha(startup) == EXPECTED['startup_sha256']
for key in ('gui_owner', 'gtk_owner', 'camera_owner'):
    owner(EXPECTED[key])
after = current()
result = dict(schema='aura-no-output-test-off-result-1', status='TEMPORARY_THINKING_DISABLED_ORDINARY_MODE_RESTORED',
    startup_sha256=EXPECTED['startup_sha256'], boot_id=EXPECTED['boot_id'], all380_actual_bytes_match=True,
    transaction=str(transaction), flag_backup=str(transaction / 'thinking-flag.before.json'),
    flag_absent=True, next_turn_thinking_options={}, source_or_model_configuration_changes=0,
    GUI_restarts=0, listening_controls=0, microphone_enable_calls=0, current_job_cancelled=False,
    state_before=before, current_state=after, GUI_and_camera_owners_unchanged=True,
    in_flight_control_transactions=0, unknown_operations_remaining=0)
create(transaction / 'result.json', (json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result))
