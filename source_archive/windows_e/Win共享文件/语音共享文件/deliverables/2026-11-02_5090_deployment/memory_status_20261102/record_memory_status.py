"""Record the fresh memory readback without changing any device state."""
import datetime
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
receipt = 'memory_status_20261102/MEMORY_CURRENT_082236.json'
observed = json.loads((OUT / receipt).read_text(encoding='utf-8'))['board_result']
assert observed['quick_check_ok'] is True
assert observed['raw_text_names_ids_or_summaries_exported'] is False
assert observed['live_worker_metadata']['memory']['running'] is True
assert observed['live_worker_metadata']['memory']['error_present'] is False
path = OUT / 'DEPLOYMENT_CURRENT.json'
raw = path.read_bytes()
value = json.loads(raw)
assert value['startup_sha256'] == 'bcb773cd5bf306ac536df0373d1c1b27d01b6564a35839f2623b274442c13a59'
backup = HERE / 'deployment_current_before_memory_status_082236.json'
with backup.open('xb') as stream:
    stream.write(raw)
counts = observed['counts']
value['memory_status'] = {
    'observed_utc':observed['utc'], 'quick_check_ok':True,
    'conversation_turn_records':counts['bm_turns_rows'],
    'conversation_scope_records':observed['turn_scope_counts']['conversation'],
    'device_scope_records':observed['turn_scope_counts']['device'],
    'valid_summaries':counts['valid_summaries'],
    'current_facts':counts['current_facts'],
    'profile_catalog_count':counts['bm_profiles_rows'],
    'pending_user_bodies':counts['uncompacted_valid_user_bodies'],
    'pending_played_assistant_bodies':counts['uncompacted_valid_played_bodies'],
    'pending_bodies_all_sources':counts['uncompacted_valid_bodies'],
    'pending_body_sources':observed['pending_valid_body_sources'],
    'compaction_eligibility':observed['compaction_eligibility'],
    'failed_tasks_historical':observed['task_states']['failed'],
    'failed_tasks_linked_to_pending_bodies':counts['failed_tasks_still_linked_to_pending_bodies'],
    'worker_running':True,
    'worker_error_present':False,
    'worker_completed_in_current_gui':observed['live_worker_metadata']['memory']['completed'],
    'worker_discarded_in_current_gui':observed['live_worker_metadata']['memory']['discarded'],
    'receipt':receipt,
    'personal_memory_binding_acceptance_passed':False,
    'long_term_retrieval_acceptance_passed_in_current_boot':False,
    'scope':'Fresh current startup and GUI owner verified; 380 component pins checked; board SQLite read-only aggregates and filtered worker health'}
value['updated_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
new = (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
temp = HERE / 'deployment_current_memory_status_082236.tmp'
with temp.open('xb') as stream:
    stream.write(new)
    stream.flush()
    os.fsync(stream.fileno())
assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(raw).digest()
os.replace(temp,path)
print(json.dumps({'updated_memory_only':True,'valid_summaries':counts['valid_summaries'],
                  'worker_running':True,'worker_error_present':False,'device_operations':False}))
