"""Restore only our temporary stop guard and start the original GUI once."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
TX = Path('/home/root/aura-5090-recovery-20261102-a6d4a069/voice-self-match-alias-v1')
OVERRIDE = Path('/run/systemd/system/aura-avatar-ui.service.d/zzzzzz-voice-self-match-alias-graceful-20261102.conf')
GUARD = b'[Service]\nKillMode=process\nSendSIGKILL=no\nTimeoutStopSec=infinity\n'
TARGETS = {'board/runtime/board_speaker_business.py': '28d36d1f35ed173098df50e51b829a89b0f5d09c1f7281dc34381a3cedac6cfe', 'common/feature_intents.py': '901c74d8de825bf6f22ac7cca608db3840ea7d39cc104ac4b5392dca3f7d8f6c'}

def show(name, properties):
    r = subprocess.run(['systemctl', 'show', name, '--property=' + properties], capture_output=True, text=True, timeout=4)
    assert r.returncode == 0
    return dict(row.split('=', 1) for row in r.stdout.splitlines() if '=' in row)

def create(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())

def camera_owner():
    assert show('aura-camera-ui.service', 'MainPID,ActiveState,SubState,Job') == {'MainPID': '1332', 'ActiveState': 'active', 'SubState': 'running', 'Job': ''}
    assert Path('/proc/1332/stat').read_text().rsplit(')', 1)[1].split()[19] == '2236'
    assert hashlib.sha256(Path('/proc/1332/cmdline').read_bytes()).hexdigest() == 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == 'a6d4a069-e9b0-4065-8df7-dc23556b168e'
applied = json.loads((TX / 'applied.json').read_bytes())
assert applied['status'] == 'VOICE_SELF_MATCH_ALIAS_APPLIED_GUI_STOPPED' and applied['source_pins_after'] == TARGETS
raw = (ROOT / 'startup/config.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == applied['startup_after_sha256']
startup = json.loads(raw); aura = Path(startup['runtime']) / 'aura'
assert len(startup['component_sha256']) == 380
assert all(hashlib.sha256((aura / k).read_bytes()).hexdigest() == v for k, v in startup['component_sha256'].items())
assert all(startup['component_sha256'][k] == v for k, v in TARGETS.items())
assert show('aura-avatar-ui.service', 'MainPID,ActiveState,SubState,Job') == {'MainPID': '0', 'ActiveState': 'inactive', 'SubState': 'dead', 'Job': ''}
camera_owner()
assert json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes()) == {'version': 1, 'enabled': False}
c = http.client.HTTPConnection('192.168.50.1', 8797, timeout=3)
try:
    sent = time.monotonic(); c.request('GET', '/health'); response = c.getresponse(); received = time.monotonic()
    assert response.status == 200 and response.getheader('Date') and received - sent <= 1.
    data = response.read(1048577); assert len(data) <= 1048576
    h = json.loads(data); b = h['backend']
    assert h['ok'] is True and h['role'] == 'model_inference_only'
    assert b['model'] == 'aura-qwen3.8-27b-abliterated:iq4_xs'
    assert b['tts'] == 'omnivoice' and b['num_step'] == 16 and b['tts_ready'] is True and b['voice']['alive'] is True
finally: c.close()
assert OVERRIDE.is_file() and not OVERRIDE.is_symlink() and OVERRIDE.read_bytes() == GUARD
before = json.loads((TX / 'stop-intent.json').read_bytes())['gui_before']
create(TX / 'start-intent.json', {'board_monotonic': time.monotonic(), 'startup_sha256': applied['startup_after_sha256'],
       'single_normal_start': True, 'listening_remains_paused': True})
OVERRIDE.unlink()
r = subprocess.run(['systemctl', 'daemon-reload'], capture_output=True, timeout=6); assert r.returncode == 0
props = show('aura-avatar-ui.service', 'MainPID,ActiveState,SubState,Job,Restart,KillMode,SendSIGKILL,TimeoutStopUSec')
assert props['MainPID'] == '0' and props['ActiveState'] == 'inactive' and not props['Job']
assert all(props[k] == before[k] for k in ('Restart', 'KillMode', 'SendSIGKILL', 'TimeoutStopUSec'))
assert (ROOT / 'startup/config.json').read_bytes() == raw
camera_owner()
create(TX / 'start-submission-intent.json', {'single_submission': True})
r = subprocess.run(['systemctl', 'start', '--no-block', 'aura-avatar-ui.service'], capture_output=True, timeout=8)
assert r.returncode == 0
receipt = {'schema': 'aura-voice-self-match-alias-original-gui-start-1', 'board_monotonic': time.monotonic(),
           'normal_start_sent_once': True, 'startup_sha256': applied['startup_after_sha256'],
           'source_pins_after': TARGETS, 'original_service_properties_restored': True, 'runtime_stop_guard_removed': True,
           'camera_pid': 1332, 'camera_restarted': False, 'listening_enabled': False, 'ready_claimed': False,
           'unit': show('aura-avatar-ui.service', 'MainPID,ActiveState,SubState,Job,Result,ExecMainStatus')}
create(TX / 'start-request.json', receipt)
print(json.dumps(receipt))
