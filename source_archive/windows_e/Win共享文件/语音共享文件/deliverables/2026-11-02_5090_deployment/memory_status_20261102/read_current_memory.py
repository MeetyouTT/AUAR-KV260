"""Read counts and worker health only; preserve earlier receipts."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
source = OUT / 'video_demo_readiness_20261101/collect_memory_current_readonly.py'
code = source.read_text(encoding='utf-8')
assert hashlib.sha256(code.encode()).hexdigest() == '8bcb7288e8699f5f90637c321c597315d0945f05435381e3557daeb4aec4597a'
# The axis configuration transaction has since published a new startup and GUI.
# Pin the actual recorded release; keep the original source and strict guards.
current = json.loads((OUT / 'DEPLOYMENT_CURRENT.json').read_text(encoding='utf-8'))
assert current['startup_sha256'] == 'bcb773cd5bf306ac536df0373d1c1b27d01b6564a35839f2623b274442c13a59'
assert current['gui_owners']['supervisor'] == {
    'pid':97308, 'birth_ticks':'2694906',
    'command_sha256':'48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'}
for old, new in (
    ('3f5e81abc20ce5169ac91ae302611cba8958175a6a2bdb615fd9b858353120d5',current['startup_sha256']),
    ('82126','97308'), ('2524927','2694906')):
    assert old in code
    code = code.replace(old,new)
needle = 'source = aura / \'common/board_memory.py\''
assert code.count(needle) == 1
code = code.replace(needle, "assert len(startup['component_sha256']) == 380\nassert all(hashlib.sha256((aura / name).read_bytes()).hexdigest() == sha for name,sha in startup['component_sha256'].items())\n" + needle)
needle = "    quick = db.execute('PRAGMA quick_check(1)').fetchall()"
addition = '''    pending_sources = {key: db.execute("SELECT COUNT(*) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.compacted_summary_id IS NULL AND e.source=?", (key,)).fetchone()[0] for key in ('user_said','assistant_reply','assistant_played','camera_observed','device_event','memory_command')}
    scope_counts = {key: db.execute("SELECT COUNT(*) FROM bm_turns WHERE scope_kind=?", (key,)).fetchone()[0] for key in ('conversation','profile','device')}
    cutoff = time.time() - 300
    ready_visual = db.execute("SELECT COUNT(*),MIN(e.closed_utc),MAX(e.closed_utc) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.compacted_summary_id IS NULL AND e.closed_utc<=? AND e.source='camera_observed'",(cutoff,)).fetchone()
    compaction_eligibility = {'visual_bodies_past_300s_window':ready_visual[0], 'oldest_eligible_visual_age_s':max(0,time.time()-ready_visual[1]) if ready_visual[1] is not None else None}
'''
assert code.count(needle) == 1
code = code.replace(needle, addition + needle)
needle = 'print(json.dumps({'
addition = '''import http.client
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
'''
assert code.count(needle) == 1
code = code.replace(needle, addition + needle)
needle = "'counts': queries, 'turn_states': turn_counts, 'task_states': task_counts,"
assert code.count(needle) == 1
code = code.replace(needle, needle + "\n    'pending_valid_body_sources':pending_sources, 'turn_scope_counts':scope_counts, 'compaction_eligibility':compaction_eligibility, 'live_worker_metadata':worker_metadata,")
compile(code, '<readonly-memory-status>', 'exec')

transport = OUT.parent / '2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('memory_readonly_transport',transport)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
start = datetime.datetime.now(datetime.timezone.utc)
result = json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=30))
receipt = {
    'host_start_utc':start.isoformat(),
    'host_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'collector_sha256_lf':hashlib.sha256(code.encode()).hexdigest(),
    'base_collector_sha256_lf':'8bcb7288e8699f5f90637c321c597315d0945f05435381e3557daeb4aec4597a',
    'board_result':result}
destination = HERE / ('MEMORY_CURRENT_' + start.strftime('%H%M%S') + '.json')
with destination.open('x',encoding='utf-8') as handle:
    json.dump(receipt,handle,ensure_ascii=False,indent=2)
    handle.write('\n')
with (HERE / ('collector_' + start.strftime('%H%M%S') + '.py')).open('x',encoding='utf-8') as handle:
    handle.write(code)
print(json.dumps({'receipt':str(destination),'board_result':result},ensure_ascii=True))
