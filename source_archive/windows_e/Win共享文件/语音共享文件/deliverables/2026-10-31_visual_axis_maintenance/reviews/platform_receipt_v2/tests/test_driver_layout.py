"""Independent layout proof plus fake-file reproduction of the v1 omission."""
from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT.parents[1]
V1 = TASK / 'reviews/platform_readonly_v1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = load('readonly_probe_v2_under_test', ROOT / 'probe_bundle_v2/run_readonly_probe.py')
fixtures = load('readonly_probe_v1_public_fixtures', V1 / 'tests/test_readonly_probe.py')
build = load('local_receipt_layout_helpers', ROOT / 'tools/reconcile_and_build.py')
old = read(V1 / 'probe_bundle/probe_policy.json')
new = read(ROOT / 'probe_bundle_v2/probe_policy.json')


def real_layout_fixture(correct_policy):
    fixture = fixtures.Fixture()
    for row in fixture.policy['files']:
        if row['role'] != 'FIRMWARE_DRIVER_FILE':
            continue
        old_path = row['path']
        correct_path = new['files'][row['index']]['path']
        fixture.hashes[correct_path] = fixture.hashes.pop(old_path)
        fixture.sizes[correct_path] = fixture.sizes.pop(old_path)
        if correct_policy:
            row['path'] = correct_path
    return fixture


class DriverLayoutTests(unittest.TestCase):
    def test_layout_is_proven_by_hash_bound_board_validator(self):
        proof = read(ROOT / 'evidence/driver_layout_proof.json')
        source = (ROOT / 'audit_sources/reconstructed_wide_bench.py.txt').read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(), proof['reconstructed_wide_bench_sha256'])
        self.assertTrue(proof['actual_board_bench_matched'])
        tree = ast.parse(source.decode())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'validated_context')
        assignment = next(n for n in function.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'driver' for t in n.targets))
        self.assertEqual(ast.unparse(assignment.value), "root / 'driver'")

    def test_only_three_fingerprint_paths_and_revision_change(self):
        self.assertEqual(set(old), set(new))
        self.assertEqual({k:v for k,v in old.items() if k not in ('files', 'revision')},
                         {k:v for k,v in new.items() if k not in ('files', 'revision')})
        changed = []
        for a, b in zip(old['files'], new['files']):
            if a != b:
                changed.append(a['index'])
                self.assertEqual({k:v for k,v in a.items() if k != 'path'}, {k:v for k,v in b.items() if k != 'path'})
                self.assertEqual(Path(b['path']).parent.name, 'driver')
        self.assertEqual(changed, [42, 43, 44])

    def test_original_path_policy_reproduces_three_unavailable(self):
        fixture = real_layout_fixture(False)
        result = probe.run_probe(fixture.policy, fixture, fixture.health, clock=lambda: 100.)
        self.assertEqual([r['index'] for r in result['files'] if r['state'] == 'UNAVAILABLE'], [42, 43, 44])
        self.assertTrue(result['observations_valid'])
        self.assertFalse(result['motion_qualified'])

    def test_corrected_policy_reads_driver_directory_without_changing_gates(self):
        fixture = real_layout_fixture(True)
        result = probe.run_probe(fixture.policy, fixture, fixture.health, clock=lambda: 100.)
        self.assertEqual(result['status'], 'READONLY_OBSERVED')
        self.assertTrue(all(r['state'] == 'MATCH' for r in result['files'][42:45]))
        self.assertFalse(result['motion_qualified'])
        self.assertFalse(result['bindings']['manual_boot_matches_current'])
        self.assertIsNone(result['current_stopped_reference_us'])

    def test_probe_functions_are_unchanged_from_28_test_version(self):
        a = (V1 / 'probe_bundle/run_readonly_probe.py').read_text(encoding='utf-8')
        b = (ROOT / 'probe_bundle_v2/run_readonly_probe.py').read_text(encoding='utf-8')
        self.assertEqual(build.normalized_source(a), build.normalized_source(b))

    def test_corrected_paths_remain_unknown_until_main_reads_them(self):
        delta = read(ROOT / 'evidence/policy_delta.json')
        self.assertTrue(all(row['corrected_path_live_result'] is None for row in delta['changes']))
        reconciled = read(ROOT / 'evidence/reconciled_receipt.json')
        self.assertFalse(reconciled['corrected_driver_paths_live_verified'])
        self.assertFalse(reconciled['wide_runtime_files_loaded'])
        self.assertEqual(reconciled['actual_platform']['firmware_kind'], 'BENCHMARK_B4096')


if __name__ == '__main__':
    unittest.main()
