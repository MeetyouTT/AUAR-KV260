"""Read local frozen evidence and prepare an isolated R2 GUI review copy."""
from pathlib import Path
import hashlib
import json

REVIEW = Path(__file__).resolve().parents[1]
TASK = REVIEW.parents[1]
BUSINESS = TASK.parents[1]
OWNER = BUSINESS / 'deliverables/2026-10-30_board_owner/integration'
V24 = OWNER / 'dialogue_repair/release_v24_memory_followup_candidate/memory_followup_evidence'
V23 = OWNER / 'dialogue_repair/release_v23_memory_summary_candidate/memory_summary_evidence'
WIDE = BUSINESS.parent / '协作任务/2026-10-28_整机联动与舵机范围/offline_wide'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    assert sha(V24 / 'spec.json') == '9015c45aa735035e2185b998ae68f97ddeb7bcbf5252301143a235dce2f3ffe1'
    assert sha(V24 / 'source_mapping.json') == '6fb9899571078207b7460ae71d6da52ccd211c150b7d39f54f4003e672ec21c9'
    mapping = read(V24 / 'source_mapping.json')
    old = read(V23 / 'source_mapping.json')['component_pins']
    current = mapping['component_pins']
    changed = [dict(component=k, before_sha256=old.get(k), after_sha256=current.get(k))
               for k in sorted(set(old) | set(current)) if old.get(k) != current.get(k)]
    assert len(old) == len(current) == 380
    assert [x['component'] for x in changed] == ['board/runtime/board_memory_policy.py']
    assert changed[0]['after_sha256'] == 'd6e459f913a6c3d9827e0d90322cb9a2fb17ada87144b853dfdf02ed300f36c6'
    canonical = read(V24 / 'canonical_update_state.json')
    assert canonical['phase'] == 'COMMITTED'
    assert canonical['spec_sha256'] == sha(V24 / 'spec.json')
    assert canonical['ready_sha256'] == sha(V24 / 'ready.json')
    gui = []
    for row in read(TASK / 'evidence/baseline_manifest.json')['entries']:
        if row['path'].startswith('aura/'):
            rel = row['path'][5:]
            assert current[rel] == row['sha256']
            gui.append(dict(component=rel, sha256=current[rel], matches_v24=True))
    assert len(gui) == 23
    ready = read(V24 / 'ready.json')
    save(REVIEW / 'evidence/v24_before_pin_check.json', dict(
        schema='aura-visual-axis-v24-compatibility-1', status='RELEVANT_BEFORE_PINS_MATCH_V24',
        spec_sha256=sha(V24 / 'spec.json'), mapping_sha256=sha(V24 / 'source_mapping.json'),
        canonical_update_state='COMMITTED', startup_sha256=mapping['startup_sha256'],
        manifest_sha256=mapping['source_manifest_sha256'],
        v23_to_v24_changes=changed, unchanged_components=379, relevant_components=gui,
        saved_main_pid=ready['main_pid'], saved_gtk_pid=ready['gtk_pid'],
        saved_listening_enabled=ready['listening_enabled'],
        saved_listening_state=ready['listening_state'],
        saved_microphone_opened=ready['physical_microphone_opened'],
        source='LOCAL_FROZEN_EVIDENCE', current_live_state_claimed=False))

    controller_path = WIDE / 'manifests/controller-manifest.json'
    firmware_path = WIDE / 'manifests/candidate-manifest.json'
    config = read(TASK / 'baseline/aura/config/pan_face.local.json')
    assert sha(controller_path) == config['manifest_sha256']
    assert sha(firmware_path) == config['arguments']['manifest-sha256']
    controller = read(controller_path)
    entries = []
    for row in controller['files']:
        rel = row['source_rel']
        local = WIDE / 'source/controller' / rel
        available = local.is_file()
        if available:
            assert sha(local) == row['sha256']
        if rel.endswith('.py'):
            assert sha(TASK / 'baseline/controller' / rel) == row['sha256']
        entries.append(dict(relative_path=rel, board_destination=row['destination'],
            expected_sha256=row['sha256'], bytes=row['bytes'],
            local_archive_available=available, local_archive_pin_matches=True if available else None,
            current_board_pin_matches=None))
    assert len(entries) == 25
    assert sum(x['relative_path'].endswith('.py') for x in entries) == 22
    save(REVIEW / 'evidence/controller_manifest_chain.json', dict(
        schema='aura-referenced-wide-controller-chain-1',
        status='LOCAL_MANIFEST_CHAIN_CLOSED_BOARD_FILES_NOT_CHECKED',
        controller_manifest_sha256=sha(controller_path),
        firmware_manifest_sha256=sha(firmware_path),
        referenced_by_v24_pan_config=True, archive_python_pins_verified=22,
        file_count=25, entries=entries,
        controller_manifest_live_bytes_match=None, actual_firmware_kind='UNKNOWN',
        actual_vart_kind='UNKNOWN', current_stopped_reference_us=None,
        current_direction_verified=None))

    r1 = read(TASK / 'review_bundle/candidate_manifest.json')
    for row in r1['changed_files']:
        source = TASK / 'candidate' / row['path']
        assert sha(source) == row['after_sha256']
        target = REVIEW / 'candidate_r2' / row['path']
        if target.exists():
            raise FileExistsError('Review copy already exists; do not overwrite R2 work')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    save(REVIEW / 'evidence/r1_preserved.json', dict(
        r1_manifest_sha256=sha(TASK / 'review_bundle/candidate_manifest.json'),
        r1_test_result_sha256=sha(TASK / 'evidence/after_fix_safety_final.json'),
        r1_test_count=46, r1_result='PASSED',
        r1_candidate_unchanged=True, production_source_modified=False,
        memory_or_camera_source_modified=False, device_accessed=False))
    print(json.dumps(dict(status='V24_REVIEW_PREPARED', unchanged_components=379,
        relevant_before_pins=23, referenced_controller_files=25,
        controller_python_pins=22, live_device_checked=False)))


if __name__ == '__main__':
    main()
