"""One original normal GUI start after the applied current-boot binding receipt."""
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import time

BOOT = 'a6d4a069-e9b0-4065-8df7-dc23556b168e'
ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
TX = Path('/home/root/aura-5090-recovery-20261102-a6d4a069/gui-selected-1332-26pins-v1')

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def unit(name):
    r = subprocess.run(['systemctl', 'show', name, '--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus'], capture_output=True, text=True, timeout=4)
    assert r.returncode == 0
    return dict(row.split('=', 1) for row in r.stdout.splitlines() if '=' in row)

def create(p, v):
    raw = (json.dumps(v, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
applied = json.loads((TX / 'applied.json').read_bytes())
assert applied['status'] == 'BINDING26_APPLIED_GUI_STOPPED'
assert digest(ROOT / 'startup/config.json') == applied['startup_after_sha256'] == '9a9a709a7b2e898879bac595758f9b7ece6f2ff2e75a4c9f42ed9c38e043072a'
startup = json.loads((ROOT / 'startup/config.json').read_bytes()); aura = Path(startup['runtime']) / 'aura'
assert len(startup['component_sha256']) == 380
assert all(digest(aura / k) == v for k, v in startup['component_sha256'].items())
assert digest(aura / 'board/identity/voice_enrollment.py') == 'a9113ba40efc49828ee158554b2dae70485858396680918458f6f96bba16bacb'
gui = unit('aura-avatar-ui.service'); camera = unit('aura-camera-ui.service')
assert gui['MainPID'] == '0' and gui['ActiveState'] in {'failed', 'inactive'} and not gui['Job']
assert camera['MainPID'] == '1332' and camera['ActiveState'] == 'active' and camera['SubState'] == 'running' and not camera['Job']
assert Path('/proc/1332/stat').read_text().rsplit(')', 1)[1].split()[19] == '2236'
assert digest('/proc/1332/cmdline') == 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
assert json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes()) == {'version': 1, 'enabled': False}
c = http.client.HTTPConnection('192.168.50.1', 8797, timeout=3)
try:
    sent = time.monotonic(); c.request('GET', '/health'); response = c.getresponse(); received = time.monotonic()
    assert response.status == 200 and received - sent <= 1. and response.getheader('Date')
    body = response.read(1048577); assert len(body) <= 1048576
    h = json.loads(body); b = h['backend']
    assert h['ok'] is True and h['role'] == 'model_inference_only'
    assert b['model'] == 'aura-qwen3.8-27b-abliterated:iq4_xs'
    assert b['tts'] == 'omnivoice' and b['num_step'] == 16 and b['tts_ready'] is True and b['voice']['alive'] is True
finally: c.close()
create(TX / 'normal-start-intent.json', {'boot_id': BOOT, 'board_monotonic': time.monotonic(),
       'startup_sha256': applied['startup_after_sha256'], 'single_submission': True, 'listening_remains_paused': True})
assert digest(ROOT / 'startup/config.json') == applied['startup_after_sha256']
r = subprocess.run(['systemctl', 'start', '--no-block', 'aura-avatar-ui.service'], capture_output=True, timeout=8)
assert r.returncode == 0
receipt = {'schema': 'aura-current-boot-original-gui-start-1', 'boot_id': BOOT, 'board_monotonic': time.monotonic(),
           'normal_start_submitted_once': True, 'startup_sha256': applied['startup_after_sha256'],
           'source_or_time_policy_or_identity_threshold_changed': False, 'camera_restarted': False,
           'axis_command_sent': False, 'gui_unit': unit('aura-avatar-ui.service'), 'ready_claimed': False}
create(TX / 'normal-start-request.json', receipt)
print(json.dumps(receipt))
