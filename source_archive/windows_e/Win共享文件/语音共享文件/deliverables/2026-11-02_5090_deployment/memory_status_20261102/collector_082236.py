"""Read production memory aggregates only; never construct a store or worker."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import time

BOOT = '903cfade-b93c-48fa-804e-379be1967313'
BUSINESS = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
PRIVATE = Path('/home/root/.local/share/aura-board-business')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
startup_raw = (BUSINESS / 'startup/config.json').read_bytes()
assert hashlib.sha256(startup_raw).hexdigest() == 'bcb773cd5bf306ac536df0373d1c1b27d01b6564a35839f2623b274442c13a59'
startup = json.loads(startup_raw)
aura = Path(startup['runtime']) / 'aura'
assert len(startup['component_sha256']) == 380
assert all(hashlib.sha256((aura / name).read_bytes()).hexdigest() == sha for name,sha in startup['component_sha256'].items())
source = aura / 'common/board_memory.py'
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_sha == '8905770197f114cc063addb2dd40bc745d9af942f674140f43e597ff3a6b1905'
assert startup['component_sha256']['common/board_memory.py'] == source_sha
ui_raw = (aura / 'config/board_avatar_gtk.json').read_bytes()
assert hashlib.sha256(ui_raw).hexdigest() == startup['component_sha256']['config/board_avatar_gtk.json']
config = json.loads(ui_raw)['board_business']
assert Path(config['private_root']) == PRIVATE
assert config['data_origin'] == 'board'
path = PRIVATE / 'timeline.sqlite3'
assert not path.is_symlink() and path.resolve() == path
before = path.stat()
assert stat.S_ISREG(before.st_mode) and before.st_size <= 128 * 1024 * 1024
services = {}
for name in ('aura-avatar-ui.service', 'aura-camera-ui.service'):
    p = subprocess.run(['systemctl', 'show', name, '--property=MainPID,ActiveState,SubState,Job'],
                       capture_output=True, text=True, timeout=4)
    assert p.returncode == 0
    services[name] = dict(line.split('=', 1) for line in p.stdout.splitlines() if '=' in line)
assert services['aura-avatar-ui.service'] == {'MainPID': '97308', 'ActiveState': 'active', 'SubState': 'running', 'Job': ''}
gui_stat = Path('/proc/97308/stat').read_text()
gui_birth = gui_stat[gui_stat.rfind(')')+2:].split()[19]
assert gui_birth == '2694906'
gui_cmd = Path('/proc/97308/cmdline').read_bytes()
assert hashlib.sha256(gui_cmd).hexdigest() == '48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'
assert services['aura-camera-ui.service']['MainPID'] == '79866'
assert services['aura-camera-ui.service']['ActiveState'] == 'active'
assert services['aura-camera-ui.service']['SubState'] == 'running'

db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2, isolation_level=None)
deadline = time.monotonic() + 8
db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
queries = {}

def count(label, query, parameters=()):
    assert query.lstrip().upper().startswith('SELECT ')
    row = db.execute(query, parameters).fetchone()
    assert len(row) == 1 and type(row[0]) is int and row[0] >= 0
    queries[label] = row[0]

try:
    db.execute('PRAGMA query_only=ON')
    assert db.execute('PRAGMA query_only').fetchone() == (1,)
    assert db.execute('PRAGMA application_id').fetchone() == (0x41555242,)
    assert db.execute("SELECT value FROM bm_meta WHERE key='schema_version'").fetchone() == ('1',)
    assert db.execute("SELECT value FROM bm_meta WHERE key='data_origin'").fetchone() == ('board',)
    db.execute('BEGIN')
    tables = ('bm_turns', 'bm_events', 'bm_bodies', 'bm_summaries', 'bm_tasks', 'bm_facts', 'bm_profiles')
    for table in tables:
        count(table + '_rows', 'SELECT COUNT(*) FROM ' + table)
    count('valid_summaries', "SELECT COUNT(*) FROM bm_summaries WHERE state='valid'")
    count('current_facts', "SELECT COUNT(*) FROM bm_facts WHERE state='current'")
    count('active_turns', "SELECT COUNT(*) FROM bm_turns WHERE status IN ('generating','awaiting_playback')")
    count('uncompacted_valid_bodies', "SELECT COUNT(*) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.compacted_summary_id IS NULL")
    count('uncompacted_valid_user_bodies', "SELECT COUNT(*) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.compacted_summary_id IS NULL AND e.source='user_said'")
    count('uncompacted_valid_played_bodies', "SELECT COUNT(*) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.compacted_summary_id IS NULL AND e.source='assistant_played'")
    count('reserved_valid_bodies', "SELECT COUNT(*) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.compacted_summary_id IS NULL AND e.reserved_task IS NOT NULL")
    count('failed_tasks_still_linked_to_pending_bodies', "SELECT COUNT(*) FROM bm_tasks q WHERE q.status='failed' AND EXISTS (SELECT 1 FROM bm_task_sources ts JOIN bm_events e USING(event_id) JOIN bm_bodies b USING(event_id) WHERE ts.task_id=q.task_id AND e.state='valid' AND e.compacted_summary_id IS NULL AND e.revision=ts.revision AND e.body_hash=ts.body_hash)")
    turn_states = ('played', 'completed', 'cancelled', 'failed', 'generating', 'awaiting_playback')
    turn_counts = {key: db.execute('SELECT COUNT(*) FROM bm_turns WHERE status=?', (key,)).fetchone()[0] for key in turn_states}
    turn_counts['other'] = queries['bm_turns_rows'] - sum(turn_counts.values())
    task_states = ('committed', 'leased', 'failed', 'expired', 'cancelled', 'superseded')
    task_counts = {key: db.execute('SELECT COUNT(*) FROM bm_tasks WHERE status=?', (key,)).fetchone()[0] for key in task_states}
    task_counts['other'] = queries['bm_tasks_rows'] - sum(task_counts.values())
    source_counts = {key: db.execute('SELECT COUNT(*) FROM bm_events WHERE source=?', (key,)).fetchone()[0] for key in ('user_said', 'assistant_reply', 'assistant_played', 'camera_observed', 'device_event', 'memory_command')}
    timestamps = {}
    for label, query in {
        'last_turn_created_utc': 'SELECT MAX(created_utc) FROM bm_turns',
        'last_turn_closed_utc': 'SELECT MAX(closed_utc) FROM bm_turns',
        'last_event_recorded_utc': 'SELECT MAX(recorded_utc) FROM bm_events',
        'last_summary_created_utc': 'SELECT MAX(created_utc) FROM bm_summaries',
    }.items():
        value = db.execute(query).fetchone()[0]
        timestamps[label] = datetime.datetime.fromtimestamp(value, datetime.timezone.utc).isoformat() if value is not None else None
    pending_sources = {key: db.execute("SELECT COUNT(*) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.compacted_summary_id IS NULL AND e.source=?", (key,)).fetchone()[0] for key in ('user_said','assistant_reply','assistant_played','camera_observed','device_event','memory_command')}
    scope_counts = {key: db.execute("SELECT COUNT(*) FROM bm_turns WHERE scope_kind=?", (key,)).fetchone()[0] for key in ('conversation','profile','device')}
    cutoff = time.time() - 300
    ready_visual = db.execute("SELECT COUNT(*),MIN(e.closed_utc),MAX(e.closed_utc) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.compacted_summary_id IS NULL AND e.closed_utc<=? AND e.source='camera_observed'",(cutoff,)).fetchone()
    compaction_eligibility = {'visual_bodies_past_300s_window':ready_visual[0], 'oldest_eligible_visual_age_s':max(0,time.time()-ready_visual[1]) if ready_visual[1] is not None else None}
    quick = db.execute('PRAGMA quick_check(1)').fetchall()
    quick_check_ok = quick == [('ok',)]
    db.execute('ROLLBACK')
finally:
    db.close()

after = path.stat()
metadata_unchanged = (before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino)
assert Path('/proc/97308/cmdline').read_bytes() == gui_cmd
assert Path('/proc/97308/stat').read_text().rsplit(')', 1)[1].split()[19] == gui_birth
assert (BUSINESS / 'startup/config.json').read_bytes() == startup_raw
import http.client
worker_metadata = {}
connection = http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
try:
    connection.request('GET','/api/state')
    response = connection.getresponse()
    body = response.read(2097153)
    assert response.status == 200 and len(body) <= 2097152
    state = json.loads(body)
    business = state.get('board_business',{})
    if not isinstance(business,dict): business = {}
    for group, keys in (
        ('memory',('running','completed','discarded','model_calls_inside_transaction')),
        ('retention',('enabled','running')),
        ('writer',('held',)),
        ('clock',('anchored','persistent','same_boot','event_time_available','safe_for_compaction'))):
        value = business.get(group,{})
        if not isinstance(value,dict): value = {}
        worker_metadata[group] = {key:value[key] for key in keys if key in value and type(value[key]) in (bool,int,float)}
    value = business.get('memory',{})
    if isinstance(value,dict) and 'error' in value:
        worker_metadata['memory']['error_present'] = bool(value['error'])
        allowed_reasons = {'','clock_unverified','cancelled','candidate_rejected','database_busy','model_failed'}
        worker_metadata['memory']['error_reason'] = value['error'] if type(value['error']) is str and value['error'] in allowed_reasons else 'UNLISTED_REDACTED'
    del body, state, business
except (OSError,ValueError,AssertionError,http.client.HTTPException) as exc:
    worker_metadata = {'unavailable_error_type':type(exc).__name__}
finally:
    connection.close()
print(json.dumps({
    'schema': 'aura-production-memory-aggregate-readonly-live-gui-2',
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'boot_id': BOOT,
    'database_path': str(path), 'database_bytes': before.st_size,
    'database_mtime_utc': datetime.datetime.fromtimestamp(before.st_mtime, datetime.timezone.utc).isoformat(),
    'schema_version': 1, 'data_origin': 'board', 'memory_source_sha256': source_sha,
    'retention_configured_enabled': config.get('retention_enabled'), 'services': services,
    'counts': queries, 'turn_states': turn_counts, 'task_states': task_counts,
    'pending_valid_body_sources':pending_sources, 'turn_scope_counts':scope_counts, 'compaction_eligibility':compaction_eligibility, 'live_worker_metadata':worker_metadata,
    'event_sources': source_counts, 'timestamps': timestamps, 'quick_check_ok': quick_check_ok,
    'database_file_metadata_unchanged': metadata_unchanged, 'live_gui_writer_may_update_database': True, 'database_opened_read_only': True,
    'raw_text_names_ids_or_summaries_exported': False, 'worker_or_store_constructed': False,
    'database_or_service_mutation_requested': False,
}, sort_keys=True))
