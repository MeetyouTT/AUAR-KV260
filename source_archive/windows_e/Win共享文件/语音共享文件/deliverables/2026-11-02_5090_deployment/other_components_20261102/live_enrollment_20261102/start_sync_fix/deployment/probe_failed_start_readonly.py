"""Read-only startup failure metadata. No transcript, enrollment identity or raw log export."""
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import re
import subprocess

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
TARGET = 'board/identity/voice_enrollment.py'

def show(unit):
    result = subprocess.run(['systemctl', 'show', unit, '--property=MainPID,ActiveState,SubState,Result,ExecMainCode,ExecMainStatus,ExecCondition,Job,ActiveEnterTimestampMonotonic,InactiveEnterTimestampMonotonic'], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    fields = dict(row.split('=', 1) for row in result.stdout.splitlines() if '=' in row)
    condition = fields.pop('ExecCondition', '')
    fields['condition_statuses'] = re.findall(r'(?:code|status)=([^ ;}]+)', condition)
    return fields

def owner(pid):
    p = Path('/proc') / str(pid)
    if not pid or not p.exists(): return None
    return {'pid': int(pid), 'birth': p.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19], 'cmd_sha256': hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest()}

def get(port, path):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
    try:
        c.request('GET', path); response = c.getresponse(); data = response.read(2097153)
        assert response.status == 200 and len(data) <= 2097152
        return json.loads(data)
    except (OSError, ValueError, http.client.HTTPException, AssertionError):
        return None
    finally: c.close()

raw = (ROOT / 'startup/config.json').read_bytes()
startup = json.loads(raw); runtime = Path(startup['runtime']) / 'aura'
pins = startup['component_sha256']
gui = show('aura-avatar-ui.service'); camera = show('aura-camera-ui.service')
result = {'schema': 'aura-identity-coordination-handoff-1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          'startup_sha256': hashlib.sha256(raw).hexdigest(), 'component_count': len(pins),
          'all_component_pins_match': all(hashlib.sha256((runtime / key).read_bytes()).hexdigest() == value for key, value in pins.items()),
          'voice_enrollment_sha256': hashlib.sha256((runtime / TARGET).read_bytes()).hexdigest(), 'voice_enrollment_pin': pins.get(TARGET),
          'gui_unit': gui, 'camera_unit': camera, 'gui_owner': owner(int(gui['MainPID'])), 'camera_owner': owner(int(camera['MainPID'])),
          'saved_listening_enabled': json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes()).get('enabled'),
          'this_chat_gui_camera_listening_writes_frozen': True,
          'board_mutations': False, 'raw_state_or_log_exported': False}
v = get(8783, '/api/state')
if v is not None:
    hands = v.get('handsfree_dialogue') or {}; business = v.get('board_business') or {}; enrollment = (business.get('dialogue') or {}).get('voice_enrollment') or {}; speaker = business.get('speaker') or {}
    result['gui_api'] = {'reachable': True, 'pair_ready': (v.get('character_pair') or {}).get('state') == 'READY', 'main_page': v.get('ui_page') == 'main',
          'listening_enabled': hands.get('enabled'), 'microphone_open': hands.get('microphone_open'), 'paused': hands.get('state') == 'PAUSED',
          'playing': v.get('playing'), 'pending_job': bool(v.get('pending_job')), 'business_started': business.get('started'),
          'enrollment_active': enrollment.get('active'), 'enrollment_stage': enrollment.get('stage') if enrollment.get('stage') in {'idle','await_confirmation','sampling','ready','done'} else None,
          'speaker_active': speaker.get('active'), 'speaker_queued_or_active': speaker.get('queued_or_active')}
else: result['gui_api'] = {'reachable': False, 'new_enrollment_started_by_this_chat_after_failed_session': False}
v = get(8790, '/v1/ui/status')
if v is not None:
    identity = (v.get('modules') or {}).get('identity') or {}; sampling = identity.get('enrollment_sampling') or {}
    stage = sampling.get('stage')
    result['camera_identity'] = {'sampling_stage': stage if stage in {'idle','collect','validate','ready','failed','done','cancelled'} else None,
             'sampling_active': stage in {'collect','validate','ready'}, 'people_count': len(identity.get('people') or []),
             'db_version': identity.get('db_version'), 'last_operation_action': (identity.get('last_operation') or {}).get('action') if (identity.get('last_operation') or {}).get('action') in {'identity_delete','enroll','identity_enroll','enrollment_start','enrollment_save'} else None}
# Process only the current technical failure window, and emit a small fixed vocabulary.
logs = subprocess.run(['journalctl', '-u', 'aura-avatar-ui.service', '--since', '2026-11-02 09:52:05 UTC', '--no-pager', '-o', 'cat', '-n', '90'], capture_output=True, text=True, timeout=6)
assert logs.returncode == 0
log = logs.stdout
markers = ['Traceback (most recent call last)', 'SyntaxError', 'ImportError', 'ModuleNotFoundError', 'AssertionError', 'PermissionError', 'FileNotFoundError', 'TypeError', 'ValueError', 'RuntimeError', 'ExecCondition', 'Failed with result', 'condition', 'hash', 'sha256', 'manifest', 'MCP01', 'timed out', 'Address already in use', 'status=1', 'status=203', 'start-limit-hit']
result['failure_fixed_markers'] = [m for m in markers if m.lower() in log.lower()]
result['failure_python_frames'] = [{'source_basename': Path(name).name, 'line': int(line), 'function': func} for name,line,func in re.findall(r'File "([^"\n]+\.py)", line (\d+), in ([a-zA-Z0-9_<>]+)', log)][-8:]
result['failure_journal_line_count'] = len(log.splitlines())
result['failure_exit_codes'] = re.findall(r'(?:status|code|result)=(\d+|exited|exit-code|timeout|start-limit-hit)', log)
print(json.dumps(result))
