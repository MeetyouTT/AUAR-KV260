"""One forward clock correction, only while the pinned board business is stopped."""
import datetime
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

BOOT = '903cfade-b93c-48fa-804e-379be1967313'
target = float(sys.argv[1])
if not math.isfinite(target) or not 1767225600 <= target < 1798761600:
    raise RuntimeError('Unexpected host clock target')
if os.geteuid() != 0 or os.uname().machine != 'aarch64':
    raise RuntimeError('Expected the authorized KV260 root account')
if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != BOOT:
    raise RuntimeError('Board boot changed; inspect before correcting time')
unit = subprocess.run(['systemctl', 'show', 'aura-avatar-ui.service', '--no-pager',
                       '--property=MainPID,ActiveState,Job'],
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
fields = dict(line.split('=', 1) for line in unit.stdout.splitlines() if '=' in line)
if unit.returncode or fields.get('MainPID') != '0' or fields.get('Job') or fields.get('ActiveState') not in ('failed', 'inactive'):
    raise RuntimeError('GUI business is not confirmed stopped')
preference = json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())
if preference.get('enabled') is not False:
    raise RuntimeError('Saved listening preference must remain paused')
with socket.socket() as probe:
    probe.settimeout(1)
    if probe.connect_ex(('127.0.0.1', 8783)) == 0:
        raise RuntimeError('A GUI/business API is still listening')
for entry in Path('/proc').iterdir():
    if not entry.name.isdigit():
        continue
    try:
        command = (entry / 'cmdline').read_bytes()
    except OSError:
        continue
    if any(term in command for term in (b'aura-board-business-', b'board_avatar_gtk.py',
                                        b'production_memory', b'voice_memory')):
        raise RuntimeError('A possible business or memory writer is still running')
before = time.time()
if target < before - 5:
    raise RuntimeError('Backward clock correction requires separate review')
changed = abs(target - before) > 5
if changed:
    time.clock_settime(time.CLOCK_REALTIME, target)
after = time.time()
if abs(after - target) > 5:
    raise RuntimeError('Corrected board clock differs from the provided UTC target')
print(json.dumps(dict(status='FORWARD_CLOCK_ALIGNED' if changed else 'ALREADY_ALIGNED',
    boot_id=BOOT, before_epoch=before, after_epoch=after, target_host_epoch=target,
    before_utc=datetime.datetime.fromtimestamp(before, datetime.timezone.utc).isoformat(),
    after_utc=datetime.datetime.fromtimestamp(after, datetime.timezone.utc).isoformat(),
    corrected=changed, saved_listening_enabled=False, business_writers_running=False,
    ntp_configuration_changed=False, database_opened=False, audio_or_motion_requested=False)))
