"""Reconcile the saved board receipt and correct only the probe's driver layout."""
from pathlib import Path, PurePosixPath
import ast
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT.parents[1]
BUSINESS = TASK.parents[1]
V1 = TASK / 'reviews/platform_readonly_v1'
WIDE = BUSINESS.parent / '协作任务/2026-10-28_整机联动与舵机范围/offline_wide'
RECEIPT_SHA = '18de8abae51cb20911051ebf8026fb82bdd190378b02205065bb74afaf064f9e'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def normalized_source(source):
    tree = ast.parse(source)
    assignments = [node for node in tree.body if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'POLICY_SHA256' for t in node.targets)]
    assert len(assignments) == 1
    assignments[0].value = ast.Constant(value='POLICY_HASH_OMITTED_FOR_BEHAVIOR_COMPARISON')
    return ast.dump(tree, include_attributes=False)


def main():
    path = TASK / 'evidence/root_platform_readonly_v24_1793522299017286000.json'
    assert sha(path.read_bytes()) == RECEIPT_SHA
    receipt = read(path)
    observation = receipt['observation']
    assert receipt['status'] == 'ROOT_READONLY_EXECUTED'
    assert observation['status'] == 'READONLY_INCOMPLETE' and observation['observations_valid'] is True
    assert all(observation[k] is True for k in ('before_context_matches', 'after_context_matches',
        'before_owners_match', 'after_owners_match', 'same_owner_context', 'platform_stable'))
    assert receipt['motion_commands_sent'] == receipt['service_commands_sent'] == receipt['production_files_written'] == 0
    for period in ('listening_before', 'listening_after'):
        assert receipt[period] == dict(microphone_open=False, paused=True, playing=False)
    assert observation['platform']['firmware_kind'] == observation['platform']['vart_kind'] == 'BENCHMARK_B4096'
    v1_policy_path = V1 / 'probe_bundle/probe_policy.json'
    v1_script_path = V1 / 'probe_bundle/run_readonly_probe.py'
    assert sha(v1_policy_path.read_bytes()) == receipt['supplied_sha256']['probe_policy.json']
    assert sha(v1_script_path.read_bytes()) == receipt['supplied_sha256']['run_readonly_probe.py']
    old_policy = read(v1_policy_path)

    firmware = read(WIDE / 'manifests/candidate-manifest.json')
    bench_source_path = BUSINESS / 'deliverables/2026-10-23_pan_joint_firmware/scripts/bench_identity_stop.py'
    bench = bench_source_path.read_text(encoding='utf-8').replace(
        'aura-visual-servo-b4096-v2', 'aura-visual-servo-b4096-wide-v1').replace('0x778d2512', '0x10282601')
    assert sha(bench.encode()) == firmware['bench_sha256']
    bench_entry = next(row for row in old_policy['files'] if row['role'] == 'CONTEXT_VALIDATOR_SOURCE')
    assert bench_entry['sha256'] == firmware['bench_sha256']
    assert observation['files'][bench_entry['index']]['state'] == 'MATCH'
    tree = ast.parse(bench)
    function = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'validated_context')
    driver_assignment = next(x for x in function.body if isinstance(x, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'driver' for t in x.targets))
    assert isinstance(driver_assignment.value, ast.BinOp) and isinstance(driver_assignment.value.op, ast.Div)
    assert ast.unparse(driver_assignment.value) == "root / 'driver'"
    returned = next(x for x in function.body if isinstance(x, ast.Return))
    assert isinstance(returned.value, ast.Tuple) and isinstance(returned.value.elts[0], ast.Name)
    assert returned.value.elts[0].id == 'driver'
    package = WIDE / 'source/scripts/package_wide.py'
    assert "driver=bundle/'driver'" in package.read_text(encoding='utf-8')
    pin_index = {row['path']: row['sha256'] for row in read(WIDE / 'SOURCE_AND_EVIDENCE_MANIFEST.json')['files']}
    assert sha(package.read_bytes()) == pin_index['source/scripts/package_wide.py']
    proof_path = ROOT / 'audit_sources/reconstructed_wide_bench.py.txt'
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text(bench, encoding='utf-8', newline='\n')
    assert sha(proof_path.read_bytes()) == firmware['bench_sha256']
    save(ROOT / 'evidence/driver_layout_proof.json', dict(
        status='HASH_BOUND_VALIDATED_CONTEXT_RETURNS_DRIVER_SUBDIRECTORY',
        old_bench_source_sha256=sha(bench_source_path.read_bytes()),
        reconstructed_wide_bench_sha256=sha(bench.encode()),
        actual_board_bench_receipt_index=bench_entry['index'], actual_board_bench_matched=True,
        reconstruction_transformations=['REPLACE_APP_V2_WITH_WIDE_V1', 'REPLACE_BUILD_778D2512_WITH_10282601'],
        driver_assignment_line=driver_assignment.lineno, return_line=returned.lineno,
        driver_relative_directory='driver', package_source_sha256=sha(package.read_bytes()),
        source_parsed_only_not_imported_or_executed=True))

    policy = copy.deepcopy(old_policy)
    policy['revision'] = 'V24_FIXED_OWNERS_DRIVER_LAYOUT_V2'
    changes = []
    unknown = [row for row in observation['files'] if row['state'] != 'MATCH']
    assert [(row['index'], row['state']) for row in unknown] == [(42, 'UNAVAILABLE'), (43, 'UNAVAILABLE'), (44, 'UNAVAILABLE')]
    for row in policy['files']:
        if row['role'] == 'FIRMWARE_DRIVER_FILE':
            old = row['path']
            row['path'] = str(PurePosixPath(old).parent / 'driver' / PurePosixPath(old).name)
            changes.append(dict(index=row['index'], expected_sha256=row['sha256'],
                v1_requested_path=old, corrected_expected_path=row['path'],
                v1_result='UNAVAILABLE', corrected_path_live_result=None,
                interpretation='V1_WRONG_DIRECTORY_NOT_EVIDENCE_OF_MISSING_DRIVER'))
    assert len(changes) == 3
    assert {k:v for k,v in policy.items() if k not in ('revision', 'files')} == {
        k:v for k,v in old_policy.items() if k not in ('revision', 'files')}
    bundle = ROOT / 'probe_bundle_v2'
    save(bundle / 'probe_policy.json', policy)
    policy_sha = sha((bundle / 'probe_policy.json').read_bytes())
    old_script = v1_script_path.read_text(encoding='utf-8')
    old_sha = sha(v1_policy_path.read_bytes())
    assert old_script.count(old_sha) == 1
    new_script = old_script.replace(old_sha, policy_sha)
    assert normalized_source(old_script) == normalized_source(new_script)
    (bundle / 'run_readonly_probe.py').write_text(new_script, encoding='utf-8')
    save(ROOT / 'evidence/policy_delta.json', dict(
        schema='aura-axis-driver-directory-correction-1', receipt_sha256=RECEIPT_SHA,
        v1_script_sha256=sha(v1_script_path.read_bytes()), v1_policy_sha256=old_sha,
        v2_script_sha256=sha((bundle / 'run_readonly_probe.py').read_bytes()), v2_policy_sha256=policy_sha,
        changes=changes, changed_fingerprint_paths=3, unchanged_fingerprint_entries=43,
        startup_boot_owner_and_hash_expectations_unchanged=True,
        manual_release_payload_paths_unchanged=True, probe_behavior_ast_identical=True,
        no_driver_import_device_or_model_service_access=True))
    save(ROOT / 'evidence/reconciled_receipt.json', dict(
        status='ACTUAL_PLATFORM_BLOCKED_PROBE_DRIVER_PATHS_CORRECTED_LOCALLY',
        receipt_sha256=RECEIPT_SHA, saved_observation_valid=True, newly_observed_live_here=False,
        actual_platform=observation['platform'], bindings=observation['bindings'],
        controller_files_matched=25, controller_manifest_matched=True,
        wide_runtime_files_on_disk_matched=4, wide_runtime_files_loaded=False,
        fixed_entries_matched=43, v1_wrong_driver_path_unavailable=3,
        corrected_driver_paths_live_verified=False, manual_payload_matched=3,
        health=observation['health'], current_stopped_reference_us=None,
        current_direction_qualified=None, current_identity_threshold=None,
        motion_enabled=False, current_driver_build_register_readback=None,
        source_path_errors_do_not_invalidate_firmware_sysfs_results=True,
        next_probe_is_main_window_only=True))
    print(json.dumps(dict(status='RECEIPT_RECONCILED_AND_DRIVER_POLICY_CORRECTED',
        controller_files_matched=25, wide_disk_files_matched=4,
        corrected_driver_paths=3, actual_firmware='BENCHMARK_B4096', board_executed_here=False)))


if __name__ == '__main__':
    main()
