"""Read only the fixed public docs/metadata files; write a metadata check report."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
OWNER = REPAIR.parents[1]
PROJECT = OWNER.parents[1]
SHARED = PROJECT.parent


def load(path):
    return json.loads(path.read_bytes().decode('utf-8-sig'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    checks = []

    def check(condition, name):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    plan = load(HERE / 'plan.json')
    before = load(HERE / 'before_manifest.json')
    journal = load(HERE / 'journal.json')
    obs_path = REPAIR / 'current_observation_v14.json'
    obs = load(obs_path)
    pointer = plan['current_observation']
    check(sha(obs_path.read_bytes()) == pointer['sha256'], 'canonical_observation_hash')
    check(obs['startup_sha256'] == '39b102a4a505db491cf06b90e3a5232bfb656c79cb0a3c221551d76d414a9a0a', 'v14_startup')
    check(obs['source_manifest_sha256'] == 'a2545970650f60b95cdc6e4f0a31c234f37adb5f0662c9f04ded791352f53353', 'v14_manifest')
    check(obs['component_pins'] == 378 and obs['configuration_sha256'] == 'faa5bead11f6c212412cf295db7d11c092c51848a5b08b49d78449ed613ba6d7', 'v14_config_and_pins')
    check(len(before) == len(plan['after']) == journal['modified_existing_documents'] == 10, 'fixed_ten_existing_documents')
    check(all(value is False for value in obs['current_revision_acceptance'].values()), 'no_v14_gate_promoted')
    check(obs['strict_listening_updater']['executed'] is False and obs['strict_listening_updater']['code_changed'] is False, 'strict_updater_not_bypassed')

    for key, item in obs['evidence'].items():
        path = SHARED / item['path']
        check(path.is_file() and sha(path.read_bytes()) == item['sha256'], 'evidence_hash:' + key)
    strict_path = SHARED / obs['evidence']['strict_updater_not_executed']['path']
    strict_source = strict_path.read_text(encoding='utf-8-sig')
    check("require(live.get('continuous_capture_passed') is True" in strict_source and
          "'live_revision_binding_mismatch'" in strict_source, 'strict_live_gate_remains_in_source')
    check(obs['strict_listening_updater']['saved_live_startup_sha256'] != obs['startup_sha256'] and
          obs['strict_listening_updater']['saved_control_startup_sha256'] != obs['startup_sha256'], 'old_live_controls_are_not_v14')

    for name, item in before.items():
        original = (SHARED / item['archive']).read_bytes()
        path = SHARED / item['target']
        actual = path.read_bytes()
        check(sha(original) == item['sha256'] and len(original) == item['bytes'], 'byte_exact_archive:' + name)
        check(sha(actual) == plan['after'][name]['sha256'], 'after_hash:' + name)
        if path.suffix == '.json':
            old, current = json.loads(original.decode('utf-8-sig')), load(path)
            check(current['current_observation'] == pointer, 'json_current_pointer:' + name)
            check(current['status'] == obs['status'], 'json_observation_status:' + name)
            if 'verified_listening' in old:
                check(current['verified_listening'] is None and current['historical_verified_listening'][-1] == old['verified_listening'], 'old_verified_receipt_preserved_not_current:' + name)
            if 'response_latency' in old:
                check(current['response_latency'] is None and current['historical_response_latency'][-1] == old['response_latency'], 'old_latency_preserved_not_current:' + name)
            if 'listening_revision_history' in old:
                check(current['listening_revision_history'] == old['listening_revision_history'], 'revision_history_unchanged:' + name)
            if 'production' in current:
                check(current['production']['startup_sha256'] == obs['startup_sha256'] and
                      current['production']['component_pins'] == 378 and
                      current['production']['current_observation'] == pointer, 'production_metadata_current:' + name)
                check(current['production']['last_verified_ui_supervisor_pid'] is None and
                      current['production']['last_observed_ui_supervisor_pid'] == obs['supervisor_pid'], 'observed_pids_not_verified_pids:' + name)
            if 'production_business_live' in current:
                embedded = current['production_business_live']
                check(embedded['startup_sha256'] == obs['startup_sha256'] and embedded['verified_listening'] is None,
                      'embedded_live_current:' + name)
            for key in ('controls_verified', 'continuous_capture_passed', 'priority_scope_passed', 'short_capture_verified'):
                if key in current:
                    check(current[key] is False, 'current_gate_not_inherited:' + name + ':' + key)
        elif name.endswith('接续_20261030.txt'):
            check(actual.endswith(original), 'continuation_entire_old_file_preserved')
        else:
            tags = ['dialogue-current-20261031'] if name == 'project/README.md' else ['board-business-live-20261030']
            if name == 'analysis/README.md':
                tags.append('performance-dialogue-plan-20261031')
            for tag in tags:
                pattern = re.compile(re.escape(('<!-- ' + tag + ' -->').encode()) + b'(.*?)' +
                                     re.escape(('<!-- /' + tag + ' -->').encode()), re.S)
                old_match = pattern.search(original)
                current_match = pattern.search(actual)
                check(old_match is not None and current_match is not None and old_match.group(1) in actual,
                      'old_prose_exact_in_inline_archive:' + name + ':' + tag)
                if tag != 'performance-dialogue-plan-20261031':
                    check(obs['startup_sha256'].encode() in current_match.group(1) and b'1129a2a7' not in current_match.group(1),
                          'current_prose_no_v10_entry:' + name)

    short = obs['human_dialogue_window']
    check(len(short['completed_round_metadata']) == 4 and short['short_asr_round_count'] == 3, 'all_four_rounds_not_only_faster_subset')
    check(max(r['asr_ms'] for r in short['completed_round_metadata']) > 15000, 'long_asr_round_retained')
    check(short['speaker_first_audio_measured'] is False and obs['runtime_followup']['speaker_first_audio_measured'] is False, 'queued_audio_not_acoustic_first_sound')
    check(obs['runtime_followup']['capture_failures'] == 1 and obs['runtime_followup']['memory'] ==
          {'running': True, 'completed': 74, 'discarded': 6}, 'later_capture_failure_and_discard_not_hidden')
    check(obs['latest_runtime_observation']['listening']['state'] == 'PAUSED' and
          obs['latest_runtime_observation']['pending'] is False and
          obs['latest_runtime_observation']['current_live_state_claimed'] is False, 'maintenance_pause_not_claimed_listening')
    memory = obs['memory_observations']
    check(memory['initial']['store']['valid_summaries'] == 287 and memory['followup']['store']['valid_summaries'] == 298,
          'initial_visual_progress_window_bound')
    latest = memory['latest']
    check(latest['store']['valid_summaries'] == 361 and latest['store']['backlog_events'] == 927 and
          latest['worker']['completed'] == 90 and latest['worker']['discarded'] == 10, 'latest_memory_growth_and_tasks')
    check(latest['missing_body_classification']['unexplained'] == 0 and latest['store']['compacted_bodies_remaining'] == 0,
          'missing_body_explanation_not_suppressed')
    check(18 < obs['public_name_abba']['median_llm_wall_reduction_percent'] < 20 and
          obs['public_name_abba']['trials'] == 4 and obs['public_name_abba']['tts_requests'] == 0, 'small_abba_model_only')
    check(obs['unchanged_boundaries']['weights_root'] == 'D:/AIModels' and
          obs['windows_model_owner']['business_database_opened'] is False, 'storage_and_role_unchanged')
    report = {'status': 'PASS', 'checks_passed': len(checks), 'checks': checks,
              'current_observation_sha256': sha(obs_path.read_bytes()),
              'modified_existing_documents': 10, 'strict_verified_state_updater_unchanged': True,
              'devices_models_private_databases_accessed': False, 'production_candidate_code_modified': False,
              'all_history_byte_archived': True, 'no_new_v14_acceptance_claim': True}
    raw = (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    (HERE / 'consistency_check.json').write_bytes(raw)
    print(json.dumps({k: v for k, v in report.items() if k != 'checks'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
