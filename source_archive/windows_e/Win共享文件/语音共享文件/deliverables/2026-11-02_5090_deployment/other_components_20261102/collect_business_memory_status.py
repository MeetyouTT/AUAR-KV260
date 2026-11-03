"""Observe non-UI business health and aggregate memory counts, without mutations."""
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import sqlite3
import subprocess
import time

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
startup_raw = (ROOT / 'startup/config.json').read_bytes()
startup = json.loads(startup_raw)
aura = Path(startup['runtime']) / 'aura'
pins = startup['component_sha256']
assert len(pins) == 380
source_names = ('common/board_memory.py', 'common/board_memory_backoff.py',
                'board/runtime/board_memory_policy.py', 'common/board_timeline_clock.py',
                'common/profile_access.py', 'common/memory_commands.py',
                'common/profile_memory.py', 'common/timeline_memory.py',
                'board/runtime/board_business.py', 'board/runtime/board_dialogue.py',
                'board/runtime/audio/board_dialogue_jobs.py')
verified = {}
for name in source_names:
    if name not in pins:
        continue
    path = aura / name
    assert path.is_file() and not path.is_symlink()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == pins[name], 'Non-UI business source differs from its current pin: ' + name
    verified[name] = digest
assert verified['common/board_memory.py'] == '8905770197f114cc063addb2dd40bc745d9af942f674140f43e597ff3a6b1905'

config_raw = (aura / 'config/board_avatar_gtk.json').read_bytes()
assert hashlib.sha256(config_raw).hexdigest() == pins['config/board_avatar_gtk.json']
config = json.loads(config_raw)['board_business']
private = Path(config['private_root'])
assert private == Path('/home/root/.local/share/aura-board-business')
assert config['data_origin'] == 'board'
path = private / 'timeline.sqlite3'
assert path.is_file() and not path.is_symlink() and path.resolve() == path

connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1, isolation_level=None)
deadline = time.monotonic() + 3
connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
try:
    connection.execute('PRAGMA query_only=ON')
    assert connection.execute('PRAGMA query_only').fetchone() == (1,)
    assert connection.execute('PRAGMA application_id').fetchone() == (0x41555242,)
    assert connection.execute("SELECT value FROM bm_meta WHERE key='schema_version'").fetchone() == ('1',)
    assert connection.execute("SELECT value FROM bm_meta WHERE key='data_origin'").fetchone() == ('board',)
    connection.execute('BEGIN')
    queries = {
        'turn_records': 'SELECT COUNT(*) FROM bm_turns',
        'valid_summaries': "SELECT COUNT(*) FROM bm_summaries WHERE state='valid'",
        'current_facts': "SELECT COUNT(*) FROM bm_facts WHERE state='current'",
        'personal_profiles': 'SELECT COUNT(*) FROM bm_profiles',
        'active_turns': "SELECT COUNT(*) FROM bm_turns WHERE status IN ('generating','awaiting_playback')",
        'pending_valid_bodies': "SELECT COUNT(*) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.compacted_summary_id IS NULL",
        'failed_tasks_linked_to_pending_bodies': "SELECT COUNT(*) FROM bm_tasks q WHERE q.status='failed' AND EXISTS (SELECT 1 FROM bm_task_sources ts JOIN bm_events e USING(event_id) JOIN bm_bodies b USING(event_id) WHERE ts.task_id=q.task_id AND e.state='valid' AND e.compacted_summary_id IS NULL AND e.revision=ts.revision AND e.body_hash=ts.body_hash)",
    }
    counts = {key: connection.execute(query).fetchone()[0] for key, query in queries.items()}
    pending = {source: connection.execute("SELECT COUNT(*) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.compacted_summary_id IS NULL AND e.source=?", (source,)).fetchone()[0]
               for source in ('user_said', 'assistant_reply', 'assistant_played', 'camera_observed', 'device_event', 'memory_command')}
    pending['other'] = counts['pending_valid_bodies'] - sum(pending.values())
    last_summary = connection.execute('SELECT MAX(created_utc) FROM bm_summaries').fetchone()[0]
    connection.execute('ROLLBACK')
finally:
    connection.close()

def read_api():
    client = http.client.HTTPConnection('127.0.0.1', 8783, timeout=3)
    try:
        client.request('GET', '/api/state')
        response = client.getresponse()
        data = response.read(2097153)
        assert response.status == 200 and len(data) <= 2097152
        value = json.loads(data)
        business = value.get('board_business') or {}
        memory = business.get('memory') or {}
        clock = business.get('clock') or {}
        dialogue = business.get('dialogue') or {}
        hands = value.get('handsfree_dialogue') or {}
        return {'available': True,
                'business_started': business.get('started') is True,
                'board_owns_business': business.get('production_cutover') is True,
                'single_writer_held': (business.get('writer') or {}).get('held') is True,
                'memory_running': memory.get('running') is True,
                'memory_completed': memory.get('completed'), 'memory_discarded': memory.get('discarded'),
                'memory_error_present': bool(memory.get('error')),
                'clock_anchored': clock.get('anchored') is True,
                'event_time_available': clock.get('event_time_available') is True,
                'dialogue_busy': dialogue.get('busy'),
                'listening_enabled': hands.get('enabled') is True,
                'microphone_open': hands.get('microphone_open') is True,
                'playback_active': value.get('playing') is True,
                'runtime_fault_count': (value.get('runtime_faults') or {}).get('count')}
    except (OSError, ValueError, AssertionError, http.client.HTTPException) as error:
        return {'available': False, 'error_type': type(error).__name__}
    finally:
        client.close()

api = read_api()
unit = subprocess.run(['systemctl', 'show', 'aura-avatar-ui.service',
                       '--property=MainPID,ActiveState,SubState,Job'],
                      capture_output=True, text=True, timeout=4)
assert unit.returncode == 0
print(json.dumps({'schema': 'aura-other-components-memory-status-readonly-1',
                  'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  'startup_sha256': hashlib.sha256(startup_raw).hexdigest(),
                  'runtime_aura': str(aura), 'component_sha256': pins,
                  'non_ui_sources_verified': verified,
                  'startup_changed_during_observation': (ROOT / 'startup/config.json').read_bytes() != startup_raw,
                  'counts': counts, 'pending_body_sources': pending,
                  'last_summary_created_utc': datetime.datetime.fromtimestamp(last_summary, datetime.timezone.utc).isoformat() if last_summary else None,
                  'retention_configured_enabled': config.get('retention_enabled'),
                  'business_api': api,
                  'gui_service': dict(row.split('=', 1) for row in unit.stdout.splitlines() if '=' in row),
                  'read_only': True, 'database_content_or_person_ids_exported': False,
                  'axis_or_main_page_inspected_or_changed': False,
                  'service_or_inference_or_audio_or_motion_requested': False}, sort_keys=True))
