import json
GRANT={'startup_sha256': '71431dc7d7ffcf8fa824f03ae984488afec22b96f546bd3cd66e002fca8f7883', 'gui_owner': {'pid': 1128353, 'birth_ticks': '7742281', 'command_sha256': '48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'}, 'gtk_owner': {'pid': 1128405, 'birth_ticks': '7747322', 'command_sha256': 'ddd3dcd7202153c7ed7eb108c8c287b03216af1e147c930611440bfb30b2c1fc'}, 'camera_owner': {'pid': 362659, 'birth_ticks': '2850120', 'command_sha256': 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'}}
SESSION='/home/root/aura-5090-recovery-20261102-a6d4a069/five-turn-20261103T094534Z-512ef3fc-stop'
"""Single normal GUI stop, with temporary runtime protection against forced shutdown."""
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP = ROOT / 'startup/config.json'
EXPECTED_STARTUP = GRANT['startup_sha256']
BOOT = 'a6d4a069-e9b0-4065-8df7-dc23556b168e'
TX = Path(SESSION)
OVERRIDE = Path('/run/systemd/system/aura-avatar-ui.service.d/zzzzzz-root-five-turn-20261103T094534Z-512ef3fc.conf')
GUARD = b'[Service]\nKillMode=process\nSendSIGKILL=no\nTimeoutStopSec=infinity\n'

def show(unit, properties):
    result = subprocess.run(['systemctl', 'show', unit, '--property=' + properties], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)

def create(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(data); handle.flush(); os.fsync(handle.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def get(port, path):
    client = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        client.request('GET', path); response = client.getresponse(); data = response.read(2097153)
        assert response.status == 200 and len(data) <= 2097152
        return json.loads(data)
    finally: client.close()

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
assert os.geteuid() == 0 and not TX.exists() and not os.path.lexists(OVERRIDE)
raw = STARTUP.read_bytes(); assert hashlib.sha256(raw).hexdigest() == EXPECTED_STARTUP
startup = json.loads(raw); aura = Path(startup['runtime']) / 'aura'
assert len(startup['component_sha256']) == 380
assert all(hashlib.sha256((aura / key).read_bytes()).hexdigest() == digest for key, digest in startup['component_sha256'].items())
assert startup['component_sha256']['board/identity/voice_enrollment.py'] == 'a9113ba40efc49828ee158554b2dae70485858396680918458f6f96bba16bacb'
props = 'MainPID,ActiveState,SubState,Job,Restart,KillMode,SendSIGKILL,TimeoutStopUSec,Result,ExecMainStatus'
before = show('aura-avatar-ui.service', props)
assert before['MainPID'] == str(GRANT['gui_owner']['pid']) and before['ActiveState'] == 'active' and before['SubState'] == 'running' and not before['Job']
assert Path('/proc/'+str(GRANT['gui_owner']['pid'])+'/stat').read_text().rsplit(')', 1)[1].split()[19] == GRANT['gui_owner']['birth_ticks']
camera_before = show('aura-camera-ui.service', props)
assert camera_before['MainPID'] == str(GRANT['camera_owner']['pid']) and camera_before['ActiveState'] == 'active' and not camera_before['Job']
ui = get(8783, '/api/state'); hands = ui.get('handsfree_dialogue') or {}; business = ui.get('board_business') or {}
dialogue = business.get('dialogue') or {}; enrollment = dialogue.get('voice_enrollment') or {}; speaker = business.get('speaker') or {}
assert hands.get('enabled') is False and hands.get('microphone_open') is False and ui.get('playing') is False
assert not ui.get('pending_job') and enrollment.get('active') is False and speaker.get('active') is False and speaker.get('queued_or_active') == 0
assert (ui.get('manual_pan') or {}).get('automatic_following') is False
rb=(ui.get('manual_pan') or {}).get('readback') or {}
assert rb.get('flags')==0 and rb.get('lease_left_ms')==0 and rb.get('active') is False and rb.get('armed') is False
snapshot = get(8790, '/v1/ui/status')
phase = (((snapshot.get('modules') or {}).get('identity') or {}).get('enrollment_sampling') or {}).get('stage')
assert phase in ('idle', 'failed')
assert json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes()) == {'version': 1, 'enabled': False}
assert STARTUP.read_bytes() == raw
assert Path('/proc/'+str(GRANT['gtk_owner']['pid'])+'/stat').read_text().rsplit(')', 1)[1].split()[19] == GRANT['gtk_owner']['birth_ticks']
assert Path('/proc/'+str(GRANT['camera_owner']['pid'])+'/stat').read_text().rsplit(')', 1)[1].split()[19] == GRANT['camera_owner']['birth_ticks']
assert hashlib.sha256(Path('/proc/'+str(GRANT['camera_owner']['pid'])+'/cmdline').read_bytes()).hexdigest() == GRANT['camera_owner']['command_sha256']
for role in ('gui_owner','gtk_owner','camera_owner'):
    value=GRANT[role];root=Path('/proc')/str(value['pid'])
    assert root.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==value['birth_ticks']
    assert hashlib.sha256(root.joinpath('cmdline').read_bytes()).hexdigest()==value['command_sha256']
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
TX.mkdir(mode=0o700)
intent = {'schema': 'aura-no-speech-enrollment-normal-stop-intent-1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'boot_id': BOOT, 'startup_sha256': EXPECTED_STARTUP, 'gui_before': before, 'camera_before': camera_before,
          'runtime_guard_path': str(OVERRIDE), 'runtime_guard_sha256': hashlib.sha256(GUARD).hexdigest(),
          'action': 'systemctl stop --no-block aura-avatar-ui.service', 'force_kill_authorized': False}
create(TX / 'stop-intent.json', (json.dumps(intent, sort_keys=True, indent=2) + '\n').encode())
OVERRIDE.parent.mkdir(parents=True, exist_ok=True)
assert OVERRIDE.parent.resolve() == OVERRIDE.parent
create(OVERRIDE, GUARD)
reload = subprocess.run(['systemctl', 'daemon-reload'], capture_output=True, timeout=6); assert reload.returncode == 0
protected = show('aura-avatar-ui.service', props)
assert protected['MainPID'] == before['MainPID'] and not protected['Job']
assert protected['KillMode'] == 'process' and protected['SendSIGKILL'] == 'no' and protected['TimeoutStopUSec'] == 'infinity'
assert show('aura-camera-ui.service', props) == camera_before
create(TX / 'stop-submission-intent.json', b'{"single_submission":true}\n')
result = subprocess.run(['systemctl', 'stop', '--no-block', 'aura-avatar-ui.service'], capture_output=True, timeout=6)
assert result.returncode == 0
deadline = time.monotonic() + 15
while time.monotonic() < deadline:
    after = show('aura-avatar-ui.service', props)
    if after['MainPID'] == '0' and after['ActiveState'] == 'inactive' and not after['Job']: break
    time.sleep(.4)
stopped = after['MainPID'] == '0' and after['ActiveState'] == 'inactive' and after['SubState'] == 'dead' and not after['Job']
receipt = {'schema': 'aura-no-speech-enrollment-normal-stop-result-1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'status': 'GUI_NORMAL_STOPPED' if stopped else 'GUI_STOP_PENDING_NO_FORCE', 'unit': after,
           'camera_unit': show('aura-camera-ui.service', props), 'runtime_guard_path': str(OVERRIDE),
           'normal_stop_sent_once': True, 'forced_shutdown_requested': False, 'camera_stop_requested': False}
if stopped: assert after['Result'] == 'success' and after['ExecMainStatus'] == '0'
assert receipt['camera_unit'] == camera_before
if stopped:
    for role in ('gui_owner','gtk_owner'):
        value=GRANT[role];root=Path('/proc')/str(value['pid'])
        assert not root.exists() or root.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]!=value['birth_ticks']
    assert OVERRIDE.read_bytes()==GUARD
    OVERRIDE.unlink()
    parent_fd=os.open(OVERRIDE.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(parent_fd)
    finally:os.close(parent_fd)
    reload=subprocess.run(['systemctl','daemon-reload'],capture_output=True,timeout=6)
    assert reload.returncode==0
    restored=show('aura-avatar-ui.service',props)
    assert all(restored[key]==before[key] for key in ('Restart','KillMode','SendSIGKILL','TimeoutStopUSec'))
    receipt['original_GUI_stop_properties_restored']=True
    receipt['old_GUI_and_GTK_lifetimes_dead']=True
else:
    receipt['original_GUI_stop_properties_restored']=False
create(TX / 'stop-result.json', (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode())
print(json.dumps(receipt))
