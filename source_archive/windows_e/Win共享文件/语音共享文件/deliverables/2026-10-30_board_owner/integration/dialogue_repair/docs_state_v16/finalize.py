"""Validate already-written documents and freeze metadata. Does not rewrite docs."""
import datetime
import hashlib
import json
from pathlib import Path
import re

BASE = Path(r'E:\Win共享文件')
HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
def sha(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(p.read_bytes())
def ref(p):
    b = p.read_bytes()
    return {'path': p.relative_to(BASE).as_posix(), 'path_base': str(BASE), 'sha256': sha(b), 'bytes': len(b)}
def save(p, d):
    with p.open('xb') as f:
        f.write((json.dumps(d, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

rows = load(HERE / 'before_manifest.json')['files']
targets = {r['key']: BASE / r['path'] for r in rows}
old = {r['key']: (BASE / r['archive']).read_bytes() for r in rows}
canonical = REPAIR / 'current_observation_v16.json'
obs = load(canonical)
checks = []
def check(name, passed):
    checks.append({'check': name, 'passed': bool(passed)})
    assert passed, name

for r in rows:
    check('original_bytes_preserved:' + r['key'], sha((BASE / r['archive']).read_bytes()) == r['sha256'])
sources = []
for evidence in obs['evidence'].values():
    f = BASE / evidence['path']
    sealed = HERE / 'evidence' / f.relative_to(REPAIR)
    check('evidence_unchanged:' + f.name, sha(f.read_bytes()) == evidence['sha256'] == sha(sealed.read_bytes()))
    sources.append({'original': ref(f), 'sealed_copy': ref(sealed)})

keys = ['dialogue_STATUS', 'implementation', 'production_live', 'resume_verification', 'character_switch', 'windows_coordination']
for key in keys:
    d = load(targets[key])
    for field in [None] + [f for f in ['production', 'production_business_live'] if isinstance(d.get(f), dict)]:
        x = d if field is None else d[field]
        label = key + ':' + str(field)
        check('current_pins:' + label, all(x[k] == obs[k] for k in ['startup_sha256', 'source_manifest_sha256', 'configuration_sha256', 'component_pins']))
        check('paused_not_restored:' + label, not x['microphone_open'] and x['last_observed_listening_state'] == 'PAUSED' and not x['automatic_listening_restored'])
        check('no_inherited_acceptance:' + label, not x['controls_verified'] and not x['continuous_capture_passed'] and not x['full_physical_dialogue_acceptance'])
        check('canonical_ref:' + label, x['current_observation']['sha256'] == sha(canonical.read_bytes()))
        check('no_capture_fix_claim:' + label, x['later_capture_failure_count'] is None and not x['v16_zero_capture_counters_prove_v15_fixed'])
        check('memory_recovery_not_cause_or_health:' + label, x['latest_memory_runtime_counters']['completed'] == 29 and x['latest_memory_runtime_counters']['discarded'] == 18 and not x['latest_memory_runtime_counters']['whole_store_health_verified'] and not x['memory_retry_history']['root_cause_confirmed'])
    check('history_archive_link:' + key, d['continuation_history'][-1]['original_bytes_archive']['sha256'] == sha(old[key]))
for key in ['owner_continuation', 'performance_plan', 'analysis_performance_plan']:
    check('historic_full_bytes_suffix:' + key, targets[key].read_bytes().endswith(old[key]))
for key in ['project_AGENTS', 'project_README', 'analysis_README']:
    raw = targets[key].read_bytes()
    markers = re.findall(rb'<!-- ([^\n]*?) -->', raw)
    # Old single comment anchors are valid historical document markers, not blocks.
    def imbalance(b, m): return b.count(b'<!-- ' + m + b' -->') - b.count(b'<!-- /' + m + b' -->')
    check('no_new_unbalanced_markers:' + key, all(imbalance(raw, m) == imbalance(old[key], m) for m in markers if not m.startswith(b'/')))
check('windows_model_owner_unchanged', load(targets['windows_coordination'])['windows_model_owner'] == json.loads(old['windows_coordination'])['windows_model_owner'])
check('public_means_screening_only', obs['public_small_screening']['old_mean_decode_ms'] == 5788.5254375 and obs['public_small_screening']['small_mean_decode_ms'] == 2056.501 and not obs['public_small_screening']['new_human_waiting_acceptance'])
check('memory_initial_and_recovered_retained', obs['memory']['initial_retry']['failure_streak'] == 5 and obs['memory']['initial_retry']['last_delay_seconds'] == 48 and obs['memory']['latest_retry']['failure_streak'] == 0 and not obs['memory']['latest_worker']['error']['present'])
check('capture_paused_not_proof', not obs['capture']['snapshot_available'] and obs['capture']['failure_count'] is None and not obs['capture']['v16_zero_counters_prove_v15_capture_fixed'])
check('allocation_phasehold_not_deployed', not obs['pending']['frontend_allocation_deployed'] and not obs['pending']['phasehold_deployed'] and not obs['pending']['allocation_abba_complete'])
check('new_human_acceptance_not_claimed', not obs['current_revision_acceptance']['full_physical_dialogue_acceptance'])
check('document_updater_no_runtime_actions', not obs['document_update_actions']['devices_models_private_dbs_accessed'] and not obs['document_update_actions']['production_or_candidate_source_changed'] and not obs['document_update_actions']['strict_verified_state_updater_run'])

save(HERE / 'consistency.json', {'status': 'PASS', 'checks_passed': len(checks), 'checks': checks,
    'legacy_comment_anchor_note': 'Initial all-marker-pairs check rejected existing one-sided comment anchors. Existing anchor imbalance is preserved exactly; all added block markers balance.',
    'devices_models_private_databases_accessed': False, 'production_or_candidate_source_changed': False})
save(HERE / 'HANDOFF.json', {'schema': 'aura.docs-state-handoff.v1', 'status': 'V16_DOCUMENT_CONTINUATION_FROZEN',
    'revision': 'v16', 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'startup_sha256': obs['startup_sha256'], 'source_manifest_sha256': obs['source_manifest_sha256'],
    'configuration_sha256': obs['configuration_sha256'], 'component_pins': 378,
    'current_observation': ref(canonical), 'before_manifest': ref(HERE / 'before_manifest.json'),
    'consistency': ref(HERE / 'consistency.json'), 'current_note': ref(HERE / 'current_note.txt'),
    'updater': ref(HERE / 'update_docs.py'), 'finalizer': ref(Path(__file__)),
    'changed_documents': [dict(ref(p), key=k) for k, p in targets.items()], 'evidence': sources,
    'checks_passed': len(checks), 'strict_verified_state_updater_run': False,
    'scope': 'documents_and_already_saved_public_metadata_only', 'historical_bytes_preserved': True,
    'device_model_or_private_database_actions': False, 'new_source_or_configuration_deployed': False,
    'verification_scope_notice': obs['verification_scope_notice']})
print(json.dumps({'status': 'V16_DOCUMENT_CONTINUATION_FROZEN', 'checks_passed': len(checks),
    'handoff_sha256': sha((HERE / 'HANDOFF.json').read_bytes()), 'current_observation_sha256': sha(canonical.read_bytes()),
    'documents_updated': len(targets)}))
