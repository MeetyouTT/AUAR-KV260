"""Rebind the frozen public ASR probe to root's saved v20 deployment evidence."""
import ast
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
OLD = HERE.parent/'asr_threads_public'
REPAIR = HERE.parents[1]
MAPPING = REPAIR/'release_v20_identity_history_candidate/identity_history_evidence/source_mapping.json'
SPEC = REPAIR/'release_v20_identity_history_candidate/identity_history_evidence/spec.json'
OLD_PACKAGE = 'b2d0026aeea18a7a5ea5684c7f5c19dd6c7b944a8bf6bb9bbda00fcae22b5079'
MAPPING_SHA = 'a7141992428e47d49ef80828ce9a0b33df6bffe32b613343ba01f937f68fdafc'
SPEC_SHA = 'cd67e77691b415d8133015911806c98aaf328feed44945e492c8b0cd421099c7'
STARTUP = 'd24b0d0007e2aa2b417f459891c7f39f168502a58374334ceab69e31af5881dd'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(name, data):
    (HERE/name).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


old_manifest_raw = (OLD/'PACKAGE_MANIFEST.json').read_bytes()
assert sha(old_manifest_raw) == OLD_PACKAGE
old_manifest = json.loads(old_manifest_raw)
old_files = {}
for relative, row in old_manifest['files'].items():
    raw = (OLD/relative).read_bytes()
    assert sha(raw) == row['sha256']
    old_files[relative] = raw
mapping_raw, spec_raw = MAPPING.read_bytes(), SPEC.read_bytes()
assert sha(mapping_raw) == MAPPING_SHA and sha(spec_raw) == SPEC_SHA
mapping, spec = json.loads(mapping_raw), json.loads(spec_raw)
assert mapping['startup_sha256'] == spec['startup_sha256'] == STARTUP
assert mapping['component_pins'] == spec['component_sha256']
assert len(mapping['component_pins']) == 380
assert spec['expected_final_listening_enabled'] is False
assert [mapping[role]['pid'] for role in ('supervisor','gtk','camera')] == [121485,121489,1335]
assert mapping['component_pins']['board/runtime/audio/board_asr.py'] == '4edb865881c887d6a290a02e078e14386bd95d017b79820b143b5a1e329997c3'
assert mapping['configuration_sha256'] == mapping['component_pins']['config/board_avatar_gtk.json'] == '5518b6705083eb9e2fae7e19a47c003182995fe8660cbc6031860c9905da9786'

probe = old_files['probe_small_threads.py'].decode('utf-8')
old_startup = old_manifest['baseline_startup_sha256']
assert probe.count("STARTUP='" + old_startup + "'") == 1
assert probe.count("len(baseline['component_pins'])==379") == 1
probe = probe.replace("STARTUP='" + old_startup + "'", "STARTUP='" + STARTUP + "'")
probe = probe.replace("len(baseline['component_pins'])==379", "len(baseline['component_pins'])==380")
ast.parse(probe)
restored = probe.replace("STARTUP='" + STARTUP + "'", "STARTUP='" + old_startup + "'")
restored = restored.replace("len(baseline['component_pins'])==380", "len(baseline['component_pins'])==379")
assert restored.encode('utf-8') == old_files['probe_small_threads.py']
updated = dict(old_files)
updated['probe_small_threads.py'] = probe.encode('utf-8')
updated['baseline.json'] = mapping_raw
for relative, raw in updated.items():
    (HERE/relative).write_bytes(raw)
(HERE/'test_probe.py').write_bytes((OLD/'test_probe.py').read_bytes())

package = dict(schema='aura.public-small-thread-package.v1', baseline_startup_sha256=STARTUP,
    baseline_spec_sha256=SPEC_SHA, original_frozen_package_sha256=OLD_PACKAGE,
    files={name:dict(sha256=sha(raw), bytes=len(raw)) for name,raw in updated.items()})
write_json('PACKAGE_MANIFEST.json', package)
package_sha = sha((HERE/'PACKAGE_MANIFEST.json').read_bytes())
stage = '/home/root/aura-public-small-threads-v20-20261031/' + package_sha[:16]
write_json('REBASE_PROOF.json', dict(schema='aura.public-asr-thread-rebase-proof.v1',
    original_package_sha256=OLD_PACKAGE, source_mapping_sha256=MAPPING_SHA, spec_sha256=SPEC_SHA,
    baseline_startup_sha256=STARTUP, component_count=380,
    original_probe_restored_byte_exact=True,
    probe_changes=['startup_sha256','component_count_379_to_380'],
    comparator_byte_exact=True, public_helper_byte_exact=True, original_test_file_byte_exact=True,
    owners={role:mapping[role] for role in ('supervisor','gtk','camera')},
    baseline_expected_listening_enabled=False, production_config_sha256=mapping['configuration_sha256'],
    model_directory='/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6',
    model_sha256='3ef6c19369b912f7caf3cef8e545c5ccd1a33d9d7ec792a46668dc41c4b229ec',
    tokens_sha256='4b2d964e18b9cf139b473003b6698fb2ed9a2a5ec55b93daa677b28f578897aa',
    asr_dependencies='/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps',
    sherpa_runtime_version_guard='1.13.8',
    external_model_bytes_checked_by_original_BoardParaformer_constructor=True,
    original_bundle_modified=False))
write_json('HANDOFF.json', dict(schema='aura.public-small-thread-v20-handoff.v1',
    status='LOCAL_PREPARED_PENDING_DRY_TESTS', package_sha256=package_sha, stage=stage,
    command='python3 -B ' + stage + '/probe_small_threads.py --package-sha256 ' + package_sha + ' --execute-root-only',
    dry_command='python3 -B ' + stage + '/probe_small_threads.py --package-sha256 ' + package_sha,
    outer_ssh_timeout_seconds=190, total_probe_budget_seconds=140, per_slot_wait_seconds=45,
    order=[3,2,2,3], warmups_per_slot=2, measured_decodes_per_slot=2,
    full_pcm_cases=['P00 public 0.wav, 89834 samples', 'S01 fixed synthetic public WAV'],
    controller_rule='root executes this probe serially before frontend probe and keeps saved listening false/PAUSED throughout',
    gui_and_camera='same pinned owners visible and active; metadata guards before and after every stage',
    background_compaction='before/after counters reported; changes invalidate a simple isolated-load interpretation',
    model_construct_and_warmup_excluded_from_decode_comparison=True,
    production_configuration_write=False, microphone_open=False, playback=False,
    model_endpoint=False, private_database=False, model_or_audio_staged=False,
    files=package['files'], actual_result_available=False,
    baseline=dict(startup_sha256=STARTUP, source_mapping_sha256=MAPPING_SHA, spec_sha256=SPEC_SHA,
                  component_count=380, expected_listening_enabled=False)))
print(json.dumps(dict(status='REBASED_LOCAL_ONLY', package_sha256=package_sha, stage=stage)))
