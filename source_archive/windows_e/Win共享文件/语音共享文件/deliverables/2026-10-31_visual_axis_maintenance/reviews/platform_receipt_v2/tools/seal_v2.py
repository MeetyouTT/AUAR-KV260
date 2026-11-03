"""Seal the corrected read-only policy and receipt interpretation; no board IO."""
from pathlib import Path
import ast
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT.parents[1]
BUSINESS = TASK.parents[1]
V1 = TASK / 'reviews/platform_readonly_v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    delta = read(ROOT / 'evidence/policy_delta.json')
    tests = read(ROOT / 'evidence/layout_tests.json')
    script = ROOT / 'probe_bundle_v2/run_readonly_probe.py'
    policy = ROOT / 'probe_bundle_v2/probe_policy.json'
    assert tests['tests'] == 6 and tests['passed'] and not tests['failures'] and not tests['errors']
    assert sha(script) == tests['v2_script_sha256'] == delta['v2_script_sha256']
    assert sha(policy) == delta['v2_policy_sha256']
    assert sha(V1 / 'probe_bundle/run_readonly_probe.py') == delta['v1_script_sha256']
    assert sha(V1 / 'probe_bundle/probe_policy.json') == delta['v1_policy_sha256']
    prior = read(V1 / 'evidence/probe_tests_v1_final.json')
    assert prior['tests'] == 28 and prior['passed']
    assert prior['script_sha256'] == delta['v1_script_sha256']
    r2 = TASK / 'reviews/v24_compatibility/review_bundle_r2/candidate_manifest_r2.json'
    assert sha(r2) == '701c8a612500b3a1b25d071e499c3e6ef6ae52c9177263fab6bd6d6b7b428f82'
    for row in read(r2)['changed_files']:
        assert sha(TASK / 'reviews/v24_compatibility/candidate_r2' / row['path']) == row['r2_sha256']
    syntax = 0
    for path in ROOT.rglob('*.py'):
        ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        syntax += 1

    camera_snapshot = read(BUSINESS / 'deliverables/2026-10-30_board_owner/integration/resume_camera_pin/actual_metadata_snapshot_v4.json')
    protected = json.loads(camera_snapshot['files']['meta']['content'])['protected']
    source_proofs = []
    for role, rel, markers in (
            ('NATIVE_CHECKPOINT_SHUTDOWN', 'actual_board/vision/native_startup.py', ['def shutdown(config, state, owner)']),
            ('CAMERA_SHUTDOWN_ORDER', 'actual_board/vision/ui_camera_service.py', ['worker.join(timeout=2)', 'state.identity.close()'])):
        path = TASK / 'audit_sources/camera' / (rel.replace('/', '__') + '.txt')
        assert sha(path) == camera_snapshot['files'][rel]['sha256']
        lines = path.read_text(encoding='utf-8').splitlines()
        source_proofs.append(dict(role=role, source=str(path), sha256=sha(path),
            basis='OLD_BOOT_8100_SOURCE_SNAPSHOT_REQUIRES_CURRENT_CAMERA_CLOSURE_CHECK',
            anchors={m:next(i for i, line in enumerate(lines, 1) if m in line) for m in markers}))
    protection = BUSINESS / 'deliverables/2026-10-24_native_critical_live/source/aura/board/vision/native_protection.py'
    known = {v for k, v in protected.items() if k.endswith('/board/vision/native_protection.py')}
    source_proofs.append(dict(role='NATIVE_CHECKPOINT_DOMAIN_CONSTRAINTS', source=str(protection),
        sha256=sha(protection), matches_saved_protected_source=sha(protection) in known,
        current_live_camera_source_verified=False))
    save(ROOT / 'evidence/coexistence_source_proofs.json', source_proofs)

    archive_path = ROOT / 'axis_v24_readonly_probe_v2.zip'
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in (script, policy):
            info = zipfile.ZipInfo(path.name, date_time=(2026, 11, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None and len(archive.namelist()) == 2
        for path in (script, policy):
            assert hashlib.sha256(archive.read(path.name)).hexdigest() == sha(path)
    manifest = dict(schema='aura-axis-readonly-probe-v2-bundle-1',
        status='CORRECTED_READONLY_POLICY_READY_MAIN_WINDOW_ONLY',
        v2_board_executed=False, motion_deployable=False,
        script_sha256=sha(script), policy_sha256=sha(policy), zip_sha256=sha(archive_path),
        zip_bytes=archive_path.stat().st_size, static_fingerprint_entries=46,
        corrected_driver_path_indices=[42,43,44], fingerprint_hashes_unchanged=True,
        startup_boot_owner_policy_unchanged=True, existing_probe_behavior_unchanged=True,
        new_layout_tests=6, new_layout_tests_passed=True, inherited_io_test_count=28,
        inherited_test_result_sha256=sha(V1 / 'evidence/probe_tests_v1_final.json'),
        new_test_result_sha256=sha(ROOT / 'evidence/layout_tests.json'),
        actual_v1_receipt_sha256=delta['receipt_sha256'],
        original_bundle_and_receipt_preserved=True, syntax_checked_files=syntax,
        r2_candidate_manifest_sha256=sha(r2), r2_sources_unchanged=True,
        actual_platform_from_receipt='BENCHMARK_B4096',
        corrected_driver_paths_current_match=None,
        this_window_imported_motion_driver_or_accessed_device=False,
        camera_memory_common_animation_or_production_source_modified=False)
    save(ROOT / 'probe_bundle_v2_manifest.json', manifest)
    print(json.dumps({k:manifest[k] for k in ('status', 'script_sha256', 'policy_sha256',
        'zip_bytes', 'new_layout_tests', 'inherited_io_test_count', 'v2_board_executed')}))


if __name__ == '__main__':
    main()
