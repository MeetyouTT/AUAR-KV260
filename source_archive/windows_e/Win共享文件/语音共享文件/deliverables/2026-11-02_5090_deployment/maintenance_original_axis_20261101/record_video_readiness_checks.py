"""Update current evidence from independent read-only restore and memory audits."""
import datetime
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
camera_name = 'camera_restore_audit_video_20261101/CAMERA_RESTORE_READONLY_AUDIT.json'
memory_name = 'video_demo_readiness_20261101/MEMORY_CURRENT_READONLY.json'
camera = json.loads((OUT / camera_name).read_text(encoding='utf-8'))['board_result']
memory = json.loads((OUT / memory_name).read_text(encoding='utf-8'))['board_result']
assert len(camera['checks']) == 17 and all(camera['checks'].values())
assert camera['database_opened_or_copied'] is False
assert memory['database_opened_read_only'] is True and memory['quick_check_ok'] is True
assert memory['raw_text_names_ids_or_summaries_exported'] is False
path = OUT / 'DEPLOYMENT_CURRENT.json'
value = json.loads(path.read_text(encoding='utf-8'))
assert value['startup_sha256'] == '3f5e81abc20ce5169ac91ae302611cba8958175a6a2bdb615fd9b858353120d5'
assert value['camera_owner']['pid'] == camera['camera_owner']['pid'] == 79866
backup = HERE / 'deployment_current.before_video_readiness_checks.json'
assert not backup.exists()
shutil.copy2(path, backup)
counts = memory['counts']
value.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    camera_restoration_audit_passed=True, camera_restoration_audit_receipt=camera_name,
    camera_restore_checkpoint_sha256=camera['checkpoint_sha256'],
    camera_run_config_path=camera['actual_run_config_path'],
    camera_run_config_sha256=camera['actual_run_config_sha256'],
    native_cumulative_primary_overruns_at_last_probe=camera['samples'][-1]['native']['primary_period_overruns'])
value['remaining'] = [item for item in value['remaining'] if item != 'fresh full original camera checkpoint restoration audit']
value['memory_status'] = {
    'observed_utc': memory['utc'], 'quick_check_ok': True,
    'conversation_turn_records': counts['bm_turns_rows'],
    'valid_summaries': counts['valid_summaries'],
    'current_facts': counts['current_facts'],
    'profile_catalog_count': counts['bm_profiles_rows'],
    'pending_user_bodies': counts['uncompacted_valid_user_bodies'],
    'pending_played_assistant_bodies': counts['uncompacted_valid_played_bodies'],
    'pending_bodies_all_sources': counts['uncompacted_valid_bodies'],
    'failed_tasks_linked_to_pending_bodies': counts['failed_tasks_still_linked_to_pending_bodies'],
    'worker_observed_in_current_gui': True,
    'summaries_committed_since_maintenance_pause': 12,
    'receipt': memory_name,
    'personal_memory_binding_acceptance_passed': False,
    'long_term_retrieval_acceptance_passed_in_current_boot': False}
path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'camera_restore_audit_passed': True, 'valid_summaries': counts['valid_summaries'],
    'full_three_minute_integrated_demo_ready': value['full_three_minute_integrated_demo_ready'],
    'device_operations': False}))
