"""Remove only our temporary stop protection and start the original GUI once."""
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
TX = Path('/home/root/aura-5090-recovery-20261102-903cfade/voice-start-sync-v2')
OVERRIDE = Path('/run/systemd/system/aura-avatar-ui.service.d/zzzzzz-voice-start-sync-graceful-20261102.conf')
GUARD = b'[Service]\nKillMode=process\nSendSIGKILL=no\nTimeoutStopSec=infinity\n'

def show(name, properties):
    result = subprocess.run(['systemctl', 'show', name, '--property=' + properties], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    return dict(row.split('=', 1) for row in result.stdout.splitlines() if '=' in row)

def create(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == '903cfade-b93c-48fa-804e-379be1967313'
applied = json.loads((TX / 'applied.json').read_bytes())
assert applied['status'] == 'SYNC_FIX_V2_APPLIED_GUI_STOPPED'
raw = (ROOT / 'startup/config.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == applied['startup_after_sha256']
startup = json.loads(raw); aura = Path(startup['runtime']) / 'aura'
assert all(hashlib.sha256((aura / key).read_bytes()).hexdigest() == value for key, value in startup['component_sha256'].items())
assert startup['component_sha256']['board/identity/voice_enrollment.py'] == 'a9113ba40efc49828ee158554b2dae70485858396680918458f6f96bba16bacb'
assert show('aura-avatar-ui.service', 'MainPID,ActiveState,SubState,Job') == {'MainPID': '0', 'ActiveState': 'inactive', 'SubState': 'dead', 'Job': ''}
assert show('aura-camera-ui.service', 'MainPID,ActiveState,SubState,Job') == {'MainPID': '79866', 'ActiveState': 'active', 'SubState': 'running', 'Job': ''}
assert Path('/proc/79866/stat').read_text().rsplit(')', 1)[1].split()[19] == '2265436'
assert json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes()) == {'version': 1, 'enabled': False}
client = http.client.HTTPConnection('192.168.50.1', 8797, timeout=4)
try:
    client.request('GET', '/health'); response = client.getresponse(); data = response.read(1048577)
    assert response.status == 200 and len(data) <= 1048576
    health = json.loads(data); backend = health['backend']
    assert health['ok'] is True and health['role'] == 'model_inference_only'
    assert backend['model'] == 'aura-qwen3.8-27b-abliterated:iq4_xs'
    assert backend['tts'] == 'omnivoice' and backend['num_step'] == 16 and backend['tts_ready'] is True
    assert backend['voice']['alive'] is True and not backend['voice']['error']
finally: client.close()
assert OVERRIDE.is_file() and not OVERRIDE.is_symlink() and OVERRIDE.read_bytes() == GUARD
before = json.loads((TX / 'stop-intent.json').read_bytes())['gui_before']
create(TX / 'start-intent.json', {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'startup_sha256': applied['startup_after_sha256'], 'source_after_sha256': applied['source_after_sha256'],
       'action': 'systemctl start --no-block aura-avatar-ui.service', 'listening_to_remain_paused': True})
# The original process has stopped; remove our exact, temporary runtime override.
OVERRIDE.unlink()
result = subprocess.run(['systemctl', 'daemon-reload'], capture_output=True, timeout=6); assert result.returncode == 0
props = show('aura-avatar-ui.service', 'MainPID,ActiveState,SubState,Job,Restart,KillMode,SendSIGKILL,TimeoutStopUSec')
assert props['MainPID'] == '0' and props['ActiveState'] == 'inactive' and not props['Job']
assert all(props[key] == before[key] for key in ('Restart', 'KillMode', 'SendSIGKILL', 'TimeoutStopUSec'))
assert (ROOT / 'startup/config.json').read_bytes() == raw
create(TX / 'start-submission-intent.json', {'single_submission': True})
result = subprocess.run(['systemctl', 'start', '--no-block', 'aura-avatar-ui.service'], capture_output=True, timeout=8)
assert result.returncode == 0
receipt = {'schema': 'aura-voice-start-sync-original-gui-start-1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'status': 'ORIGINAL_GUI_START_REQUESTED_SYNC_FIX_V2', 'normal_start_sent_once': True,
           'runtime_stop_guard_removed': True, 'original_service_properties_restored': True,
           'startup_sha256': applied['startup_after_sha256'], 'source_after_sha256': applied['source_after_sha256'],
           'camera_pid': 79866, 'listening_enabled': False, 'software_ready_claimed': False,
           'unit': show('aura-avatar-ui.service', 'MainPID,ActiveState,SubState,Job,Result,ExecMainStatus')}
create(TX / 'start-request.json', receipt)
print(json.dumps(receipt))
