"""Package the two read-only files and verify preserved R2 evidence locally."""
from pathlib import Path
import ast
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    script = ROOT / 'probe_bundle/run_readonly_probe.py'
    policy_path = ROOT / 'probe_bundle/probe_policy.json'
    policy = read(policy_path)
    tests = read(ROOT / 'evidence/probe_tests_v1_final.json')
    generated = read(ROOT / 'evidence/probe_policy_manifest.json')
    assert tests['tests'] == 28 and tests['passed'] and not tests['failures'] and not tests['errors']
    assert sha(script) == tests['script_sha256'] == generated['script_sha256']
    assert sha(policy_path) == generated['policy_sha256']
    assert "POLICY_SHA256 = '" + sha(policy_path) + "'" in script.read_text(encoding='utf-8')
    assert len(policy['files']) == 46 and len(policy['manual_driver_files']) == 3
    assert sum(x['role'] == 'CONTROLLER_FILE' for x in policy['files']) == 25
    syntax = 0
    for p in ROOT.rglob('*.py'):
        ast.parse(p.read_text(encoding='utf-8-sig'), filename=str(p))
        syntax += 1
    r2 = TASK / 'reviews/v24_compatibility/review_bundle_r2/candidate_manifest_r2.json'
    assert sha(r2) == '701c8a612500b3a1b25d071e499c3e6ef6ae52c9177263fab6bd6d6b7b428f82'
    for row in read(r2)['changed_files']:
        assert sha(TASK / 'reviews/v24_compatibility/candidate_r2' / row['path']) == row['r2_sha256']
    for name, count in (('r2_gui_targeted.json', 8), ('r2_controller_targeted.json', 41)):
        evidence = read(TASK / 'reviews/v24_compatibility/evidence' / name)
        assert evidence['tests'] == count and evidence['passed']
    supplied = TASK / 'evidence/root_readonly_v24_1793520246085075300.json'
    assert sha(supplied) == 'ec2541900e745d39941d940e396deae0d11e606321a70b5b494323d5d4005b89'

    file_index = dict(schema='aura-axis-probe-static-file-index-1',
        policy_sha256=sha(policy_path), fixed_fingerprint_entries=policy['files'],
        additional_manual_driver_entries=policy['manual_driver_files'],
        manual_payload_hashes_source='ONLY_THE_HASH_VERIFIED_MANUAL_RELEASE_MANIFEST',
        paths_are_static_policy_not_observed_output=True)
    save(ROOT / 'probe_file_index.json', file_index)
    archive_path = ROOT / 'axis_v24_readonly_probe_v1.zip'
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in (script, policy_path):
            info = zipfile.ZipInfo(path.name, date_time=(2026, 11, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {'run_readonly_probe.py', 'probe_policy.json'}
        assert hashlib.sha256(archive.read(script.name)).hexdigest() == sha(script)
        assert hashlib.sha256(archive.read(policy_path.name)).hexdigest() == sha(policy_path)
    manifest = dict(schema='aura-axis-readonly-probe-bundle-1',
        status='READY_FOR_MAIN_WINDOW_READONLY_EXECUTION', board_executed=False,
        motion_deployable=False, script_sha256=sha(script), policy_sha256=sha(policy_path),
        zip_sha256=sha(archive_path), zip_bytes=archive_path.stat().st_size,
        test_count=28, tests_passed=True, syntax_checked_files=syntax,
        test_result_sha256=sha(ROOT / 'evidence/probe_tests_v1_final.json'),
        supplied_projection_sha256=sha(supplied),
        fixed_startup_sha256=policy['startup_sha256'], expected_context='V24_FIXED_OWNERS',
        static_fingerprint_entries=46, additional_manual_driver_entries=3,
        r2_candidate_manifest_sha256=sha(r2), r2_sources_unchanged=True,
        camera_or_memory_or_common_sources_modified=False,
        runtime_frozen_publisher_or_bindings_modified=False,
        this_window_used_ssh_uart_model_service_or_mmio=False,
        checked_files_are_not_imported_or_executed=True,
        output_contains_fixed_enums_numbers_booleans_only=True,
        output_contains_no_arbitrary_errors_media_or_identity_data=True)
    save(ROOT / 'probe_bundle_manifest.json', manifest)
    print(json.dumps({k: manifest[k] for k in ('status', 'test_count', 'static_fingerprint_entries',
        'additional_manual_driver_entries', 'zip_bytes', 'script_sha256', 'policy_sha256', 'board_executed')}))


if __name__ == '__main__':
    main()
