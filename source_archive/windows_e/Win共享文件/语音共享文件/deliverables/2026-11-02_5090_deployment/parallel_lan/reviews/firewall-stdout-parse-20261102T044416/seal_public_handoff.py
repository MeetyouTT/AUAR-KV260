"""Local-only handoff assembly; no runtime imports, processes or network IO."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

REVIEW = Path(__file__).resolve().parent
LAN = REVIEW.parents[1]
TX = LAN / 'transactions/2524d38f24674cdca495ed726f38b41d'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


probe = read(TX / 'board_public_probe.json')
inspection = read(LAN / 'latest_inspection.json')
transaction = read(TX / 'transaction.json')
original = read(REVIEW / 'transaction_before/transaction.json')
changed_keys = [key for key in original if original[key] != transaction[key]]
added_keys = sorted(set(transaction) - set(original))
assert changed_keys == ['phase']
assert added_keys == ['board_probe_receipt', 'board_probe_utc']
assert probe['status'] == 'PUBLIC_BOARD_LLM_AND_TTS_RAM_ONLY_PASS'
assert inspection['status'] == 'FRESH_IDLE_MODEL_OWNER_CONFIRMED'
assert inspection['session_id'] == probe['host_session_id'] == '2f3a707efa62401d81fc20ef22a379cb'
assert inspection['health']['active'] is False and inspection['health']['pending'] == 0
assert inspection['health']['counts'] == {'accepted_llm': 1, 'accepted_tts': 1, 'completed': 2}
firewall_check = read(LAN / 'firewall_result.json')
assert firewall_check['status'] == 'CHECKED_EXACT_RULE'
assert firewall_check['other_rules_before'] == firewall_check['other_rules_after']
report = dict(
    schema='aura-lan-public-board-ready-1',
    status='LAN_PUBLIC_BOARD_MODEL_PROBE_PASS_PHYSICAL_ACCEPTANCE_PENDING',
    assembled_utc=datetime.now(timezone.utc).isoformat(),
    transaction_id=transaction['transaction_id'], session_id=inspection['session_id'],
    endpoint=inspection['endpoint'], configuration_sha256=inspection['configuration_sha256'],
    board_boot_id=probe['board_boot_id'],
    public_probe_receipt=str(TX / 'board_public_probe.json'),
    public_probe_receipt_sha256=sha(TX / 'board_public_probe.json'),
    llm=probe['llm'], tts=probe['tts'],
    after_inspection_utc=inspection['utc'],
    after_inspection_receipt=str(LAN / 'latest_inspection.json'),
    after_inspection_sha256=sha(LAN / 'latest_inspection.json'),
    launcher=inspection['record']['owner'], main_owner=inspection['main_owner'],
    tts_owner=inspection['tts_owner'], tts_ownership=inspection['tts_ownership'],
    fixed_daemon=inspection['protected']['fixed_daemon'],
    listeners=inspection['listeners'], state_status=inspection['state']['status'],
    owns_fixed_model=inspection['state']['owns_fixed_model'],
    after_health=dict(active=False, pending=0, counts=inspection['health']['counts'],
                      model=inspection['health']['backend']['model'],
                      tts=inspection['health']['backend']['tts'],
                      num_step=inspection['health']['backend']['num_step'],
                      voice=inspection['health']['backend']['voice']),
    repair_provenance=str(LAN / 'CLI_STDOUT_FIX.json'),
    repair_source_manifest_sha256=sha(LAN / 'source_manifest_cli_stdout_fix.json'),
    actual_transaction_only_changed_existing_keys=changed_keys,
    actual_transaction_added_keys=added_keys,
    original_transaction_bytes_preserved_under=str(REVIEW / 'transaction_before'),
    firewall_check_receipt_utc=firewall_check['utc'],
    firewall_check_receipt_sha256=sha(LAN / 'firewall_result.json'),
    firewall_check_other_rules=firewall_check['other_rules_after'],
    firewall_check_other_rules_modified=False,
    firewall_fingerprint_cross_version_note='PS7 Apply before/after hash a6edb72ee21527324c9b8c6fe02506a2963091c2d06c80e63790f74531c128fd; PS5.1 Check before/after hash f83891cd8eb0bf262fa079aec0a9180948f145321e7cdf603a393d5b307a2c47. Each operation matched internally. Cross-version hash difference alone does not identify a rule change; raw full fingerprint values were not retained for cross-version comparison.',
    audio_device_opened=False, audio_played=False, microphone_opened=False,
    business_database_opened=False, board_file_modified=False,
    response_text_or_pcm_archived=False, physical_playback_or_dialogue_acceptance=False,
    board_gui_status_not_assessed_by_this_subtask=True,
    actual_model_network_operation_ownership_returned_to='root',
    further_model_requests_checks_or_controls_by_this_agent=False,
)
path = LAN / 'LAN_PUBLIC_BOARD_READY.json'
path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(status=report['status'], receipt=str(path), sha256=sha(path),
                     post_state=report['state_status'], post_health=report['after_health']), ensure_ascii=True, indent=2))
