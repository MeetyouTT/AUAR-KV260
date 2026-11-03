"""Freeze reviewed local-only affinity work without claiming a board trial."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

root = Path('/home/ghmd/aura-affinity-trial-20261022')
out = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_cpu_affinity_candidate_r2')
required = ('affinity_camera_launcher.py', 'thread_affinity_trial.py',
         'test_affinity_trial.py', 'example_policy_kv260.json',
         'test-results-r2.txt', 'evidence/owned-child-affinity.json', 'README.md')
for name in required:
    assert (root / name).is_file(), name
names = []
for line in (root / 'FILES.sha256').read_text().splitlines():
    digest, name = line.split('  ', 1)
    relative = Path(name)
    assert not relative.is_absolute() and '..' not in relative.parts
    assert (root / name).is_file() and not (root / name).is_symlink()
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
    names.append(name)
assert len(names) == len(set(names))
assert set(required) <= set(names)
validation = json.loads((root / 'validation.json').read_text())
result = (root / validation['result_log']).read_text()
test_count = int(re.search(r'^Ran (\d+) tests', result, re.MULTILINE).group(1))
assert test_count >= 28 and test_count == validation['unique_tests'] and '\nOK\n' in result
gil = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_gil_interval_trial')
board = json.loads((gil / 'evidence/final-active-audit.json').read_text())
native = json.loads((gil / 'pinned-native-bundle.json').read_text())['manifest']['files']
long = json.loads((gil / 'evidence/long-600s.json').read_text())['report']
tree = ast.parse((root / 'affinity_camera_launcher.py').read_text())
constants = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
             if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
             and node.targets[0].id in ('ROLE_SOURCES', 'CAMERA_SHA')}
assert constants['CAMERA_SHA'] == long['experimental_process_setting']['target_sha256']
for role, (relative, qualname, pinned_sha) in constants['ROLE_SOURCES'].items():
    expected = native[relative]['sha256'] if relative in native else board['source_hashes'][relative]
    assert pinned_sha == expected, (role, pinned_sha, expected)
    assert hashlib.sha256((root / 'source-reference/aura' / relative).read_bytes()).hexdigest() == expected
evidence = json.loads((root / 'evidence/owned-child-affinity.json').read_text())
assert evidence['scope'] == 'localhost owned subprocess fixtures; not KV260'
assert evidence['parent_cpus_before'] == evidence['parent_cpus_after']
assert evidence['success_exit'] == 0 and evidence['failure_exit'] == 70
assert all(evidence['post_launch'].values())
success = evidence['success_records']
assert sum(row['event'] == 'APPLIED' for row in success) == 4
assert sum(row['event'] == 'RESTORED' for row in success) == 4
assert sum(row['event'] == 'ALL_ROLES_COMMITTED' for row in success) == 1
failure = evidence['failure_records']
assert sum(row['event'] == 'RESTORED' for row in failure) == 3
assert not any(row['event'] == 'ALL_ROLES_COMMITTED' for row in failure)
assert failure[-1]['event'] == 'ABORT_OWNED_PROCESS'
assert not failure[-1]['scopes_still_active']
probe = Path('/home/ghmd/aura-model-inventory-20261021/two_terminal_final_state_20261022')
assert json.loads(probe.with_suffix('.status.json').read_text())['exit_code'] == 0
snapshot = json.loads(probe.with_suffix('.response.json').read_text())
assert snapshot['face_health']['backend'] == 'DPU_YUNET_INT8'
assert not snapshot['schedule']['optional']['yunet']['overruns']
assert not out.exists(), 'Do not rewrite a frozen shared deliverable'
out.mkdir(parents=True)
for name in names:
    target = out / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / name, target)
shutil.copyfile(root / 'FILES.sha256', out / 'reviewed-local-FILES.sha256')
(out / 'evidence/production-snapshot-after-gil.json').write_text(json.dumps(snapshot, indent=2) + '\n')
shutil.copyfile(Path(__file__), out / 'freeze_candidate.py')
release = {
    'schema': 'aura-cpu-affinity-candidate-1',
    'written_utc': datetime.now(timezone.utc).isoformat(),
    'software_tests_passed': test_count,
    'role_pins_match_independent_board_baseline_and_native_overlay': True,
    'supersedes_rejected_delivery': '2026-10-22_cpu_affinity_candidate',
    'real_os_test_scope': 'owned Ubuntu child processes, not KV260',
    'enabled_launcher_four_role_transaction_verified': True,
    'missing_role_exit_70_and_restoration_verified': True,
    'parent_process_cpu_mask_unchanged': True,
    'default_enabled': False,
    'supports_dual_model_only': True,
    'rejects_three_model_dependency_cycle_policy': True,
    'requires_original_gil_seconds': .005,
    'only_sets_current_thread_via_pid_zero': True,
    'unknown_descendants_may_inherit_creator_mask': True,
    'exclusive_cpu_cores_guaranteed': False,
    'board_deployed': False,
    'board_speedup_or_cpu_gain_proven': False,
    'board_freshness_passed': False,
    'production_snapshot_camera_pid': snapshot['pid'],
    'production_snapshot_scope': 'separate read-only observation of original production after GIL trial',
    'windows_receipt_confirmed': False,
}
(out / 'release.json').write_text(json.dumps(release, indent=2) + '\n')
for p in out.rglob('*.py'):
    ast.parse(p.read_text(), filename=str(p))
for p in out.rglob('*.json'):
    json.loads(p.read_text())
files = sorted(p for p in out.rglob('*') if p.is_file())
(out / 'FILES.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()
    + '  ' + str(p.relative_to(out)) + '\n' for p in files))
print(json.dumps({'delivery': str(out), 'hashed_files': len(files), 'board_deployed': False}))
