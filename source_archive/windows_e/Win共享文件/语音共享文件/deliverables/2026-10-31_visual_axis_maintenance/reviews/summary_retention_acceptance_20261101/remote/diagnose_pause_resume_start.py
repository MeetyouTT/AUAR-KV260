"""Read-only startup failure metadata; never exports arbitrary journal messages."""
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
CONTROL = Path('/home/root/aura-board-business-20261030/control-production-v1')
assert os.geteuid() == 0
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
lock = open('/run/lock/aura-axis-takeover-bebd3e7d.lock', 'a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
sha = lambda raw: hashlib.sha256(raw).hexdigest()
assert sha((ROOT / 'startup/config.json').read_bytes()) == 'ec12fccfdd3e8446e9c761e161167e00187e6fcf90372aa7e52c9865cc23c56f'
assert sha((ROOT / 'production_source_manifest.json').read_bytes()) == 'b144536398bcaa6fdda2f36f9c14decced7e2f766f03e55714853674d8cfdd0d'
startup = json.loads((ROOT / 'startup/config.json').read_bytes())
assert len(startup['component_sha256']) == 380
assert all(sha((ROOT / 'runtime/aura' / name).read_bytes()) == pin for name, pin in startup['component_sha256'].items())
props = ('ActiveState', 'SubState', 'MainPID', 'Result', 'ExecMainCode', 'ExecMainStatus',
         'Job', 'Restart', 'SendSIGKILL', 'TimeoutStopUSec', 'NRestarts')
show = subprocess.run(['systemctl', 'show', 'aura-avatar-ui.service', '--no-pager']
                      + ['--property=' + key for key in props], capture_output=True, text=True, timeout=5)
assert show.returncode == 0
unit = dict(line.split('=', 1) for line in show.stdout.splitlines() if '=' in line)
journal = json.loads((CONTROL / 'state.json').read_bytes())
guard = Path(journal['guard'])
assert sha(guard.read_bytes()) == journal['guard_sha256']
assert unit['Restart'] == 'no' and unit['SendSIGKILL'] == 'no' and unit['TimeoutStopUSec'] == 'infinity'
pid = int(unit['MainPID'])
proc = None
if pid and Path('/proc', str(pid)).exists():
    base = Path('/proc', str(pid))
    argv = (base / 'cmdline').read_bytes()
    expected = ['/usr/bin/python3', '-B', str(ROOT / 'startup/launcher.py'), '--config', str(ROOT / 'startup/config.json')]
    proc = dict(pid=pid, birth_ticks=int((base / 'stat').read_text().rsplit(')', 1)[1].split()[19]),
                command_sha256=sha(argv), exact_supervisor_argv=argv.rstrip(b'\0').decode().split('\0') == expected)
log = subprocess.run(['journalctl', '-u', 'aura-avatar-ui.service', '-n', '160', '--no-pager', '-o', 'json'],
                     capture_output=True, text=True, timeout=5)
assert log.returncode == 0
frames = []
errors = []
fixed = {key: False for key in ('Traceback', 'ModuleNotFoundError', 'ImportError', 'SyntaxError', 'IndentationError',
                              'ValueError', 'TypeError', 'AttributeError', 'RuntimeError', 'TimeoutError',
                              'PermissionError', 'FileNotFoundError', 'AssertionError', 'OSError',
                              'display', 'bootstrap', 'selection', 'source', 'manifest', 'lock')}
for line in log.stdout.splitlines():
    item = json.loads(line)
    message = item.get('MESSAGE', '')
    if not isinstance(message, str):
        continue
    for key in fixed:
        if key.lower() in message.lower():
            fixed[key] = True
    match = re.search(r'File "([^"\n]+)", line ([0-9]+), in ([A-Za-z0-9_<>.]+)', message)
    if match:
        name = Path(match[1]).name
        if re.fullmatch(r'[A-Za-z0-9_.<>-]{1,100}', name):
            frames.append(dict(file=name, line=int(match[2]), function=match[3]))
    match = re.match(r'^([A-Za-z][A-Za-z0-9_.]*(?:Error|Exception))(?::|$)', message)
    if match:
        errors.append(dict(error_class=match[1], message_characters=len(message), message_sha256=sha(message.encode())))
api = dict(available=False)
try:
    c = http.client.HTTPConnection('127.0.0.1', 8783, timeout=2)
    c.request('GET', '/api/state')
    r = c.getresponse()
    raw = r.read(1048577)
    assert r.status == 200 and len(raw) <= 1048576
    value = json.loads(raw)
    h = value.get('handsfree_dialogue', {})
    p = value.get('manual_pan', {})
    rb = p.get('readback') or {}
    api = dict(available=True, phase=value.get('phase') if value.get('phase') in ('IDLE', 'THINKING', 'SPEAKING') else 'other',
               listening_enabled=h.get('enabled') if type(h.get('enabled')) is bool else None,
               microphone_open=h.get('microphone_open') if type(h.get('microphone_open')) is bool else None,
               playing=value.get('playing') if type(value.get('playing')) is bool else None,
               following=p.get('automatic_following') if type(p.get('automatic_following')) is bool else None,
               output_closed=rb.get('flags') == 0 and rb.get('lease_left_ms') == 0 and rb.get('active') is False and rb.get('armed') is False)
except Exception as exc:
    api = dict(available=False, error_class=type(exc).__name__)
finally:
    try:c.close()
    except Exception:pass
print(json.dumps(dict(schema='aura-pause-resume-start-readonly-diagnostic-1', observed_mono=time.monotonic(),
    startup_source_380_match=True, unit=unit, supervisor=proc, guard_retained=True,
    publication_phase=journal.get('phase') if journal.get('phase') in ('STARTING','START_INTENT','POSTCHECK_FAILED_GUARDED') else 'other',
    traceback_frames=frames[-25:], errors=errors[-12:], fixed_journal_categories=fixed,
    public_api=api, journal_bodies_exported=False, device_commands_sent=False, private_database_opened=False), allow_nan=False))
