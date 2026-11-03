"""Public fake filesystem/HTTP tests; never open device or service endpoints."""
import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
SCRIPT = HERE / 'probe_bundle/run_readonly_probe.py'
spec = importlib.util.spec_from_file_location('axis_readonly_probe_under_test', SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
ORIGINAL_POLICY = json.loads((HERE / 'probe_bundle/probe_policy.json').read_text(encoding='utf-8'))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class Fixture:
    def __init__(self):
        self.policy = copy.deepcopy(ORIGINAL_POLICY)
        self.data, self.hashes, self.sizes, self.missing = {}, {}, {}, set()
        self.read_calls, self.hash_calls, self.health_calls = [], [], 0
        self.hash_overrides = {}
        old_boot = 'public-historical-boot'
        roles = {row['role']: row for row in self.policy['files'] if row['role'] != 'CONTROLLER_FILE'}
        payload = {row['name']: digest(('public ' + row['name']).encode()) for row in self.policy['manual_driver_files']}
        documents = {
            'GUI_MANUAL_CONFIG': dict(boot_id=old_boot, fdt_sha256=digest(b'historical fdt')),
            'GUI_FACE_CONFIG_COPY': dict(manifest_sha256=roles['CONTROLLER_MANIFEST']['sha256']),
            'EFFECTIVE_FACE_CONFIG': dict(manifest_sha256=roles['CONTROLLER_MANIFEST']['sha256']),
            'GUI_DIRECTION_COPY': dict(boot_id=old_boot),
            'EFFECTIVE_DIRECTION': dict(boot_id=old_boot),
            'CONTROLLER_MANIFEST': dict(schema='public-controller-fixture'),
            'FIRMWARE_MANIFEST': dict(schema='public-firmware-fixture'),
            'MANUAL_RELEASE_MANIFEST': dict(payload_files=payload),
        }
        # Fixture JSON is public. Bind the fixture policy to those bytes, then
        # preserve each original role/path boundary while testing the checker.
        for row in self.policy['files']:
            if row['parse_json']:
                raw = json.dumps(documents[row['role']], sort_keys=True).encode()
                self.data[row['path']] = raw
                row['sha256'], row['bytes'] = digest(raw), len(raw)
            self.hashes[row['path']] = row['sha256']
            self.sizes[row['path']] = row['bytes'] if row['bytes'] is not None else 1
        controller_sha = next(row['sha256'] for row in self.policy['files'] if row['role'] == 'CONTROLLER_MANIFEST')
        for row in self.policy['files']:
            if row['role'] in ('GUI_FACE_CONFIG_COPY', 'EFFECTIVE_FACE_CONFIG'):
                raw = json.dumps(dict(manifest_sha256=controller_sha), sort_keys=True).encode()
                self.data[row['path']] = raw
                row['sha256'], row['bytes'] = digest(raw), len(raw)
                self.hashes[row['path']], self.sizes[row['path']] = row['sha256'], len(raw)
        for row in self.policy['manual_driver_files']:
            self.hashes[row['path']], self.sizes[row['path']] = payload[row['name']], 1
        self.hashes[self.policy['startup_path']] = self.policy['startup_sha256']
        os_paths = self.policy['os_paths']
        self.data[os_paths['boot']] = self.policy['boot_id'].encode() + b'\n'
        self.data[os_paths['firmware']] = self.policy['firmware_names']['WIDE_V1'].encode() + b'\0'
        self.data[os_paths['fpga_state']] = b'operating\n'
        self.data[os_paths['vart']] = self.policy['vart_lines']['WIDE_V1'].encode()
        self.data[os_paths['board_cid']] = self.policy['board_cid'].encode()
        self.hashes[os_paths['fdt']] = digest(b'current public fdt')
        for owner in self.policy['owners']:
            parts = ['0'] * 24
            parts[19] = str(owner['birth_ticks'])
            self.data['/proc/%d/stat' % owner['pid']] = (
                '%d (public fixture) ' % owner['pid'] + ' '.join(parts)).encode()
            self.hashes['/proc/%d/cmdline' % owner['pid']] = owner['command_sha256']
        camera = next(x for x in self.policy['owners'] if x['role'] == 'CAMERA')
        health = dict(pid=camera['pid'], board_boot_id=self.policy['boot_id'],
            service_epoch='public-service', camera_epoch='public-camera',
            capture_frames=100, detected_frames=50, camera_error='', detector_error='',
            identity=dict(ready=True, backend='DPU_SFACE_INT8', error='', processed=10,
                face_targets=dict(processed=20, worker_faults=0)),
            dpu_schedule=dict(primary_calls=50, primary_period_overruns=2,
                optional=dict(yunet=dict(native_failures=0), sface=dict(native_failures=1))))
        self.health_values = [health, copy.deepcopy(health)]
        self.health_values[1]['capture_frames'] += 10
        self.health_values[1]['detected_frames'] += 5

    def row(self, role):
        return next(row for row in self.policy['files'] if row['role'] == role)

    def read(self, path, limit):
        self.read_calls.append(path)
        if path in self.missing or path not in self.data:
            return 'UNAVAILABLE', None, 0
        raw = self.data[path]
        return ('OK', raw, len(raw)) if len(raw) <= limit else ('BYTE_LIMIT', None, len(raw))

    def digest(self, path, expected_size=None):
        self.hash_calls.append(path)
        if path in self.hash_overrides:
            return self.hash_overrides[path](self.hash_calls.count(path))
        if path in self.missing or path not in self.hashes:
            return 'UNAVAILABLE', None, 0
        size = self.sizes.get(path, 1)
        if expected_size is not None and size != expected_size:
            return 'SIZE_MISMATCH', None, 0
        return 'OK', self.hashes[path], size

    def health(self, policy):
        index = self.health_calls
        self.health_calls += 1
        return 'OK', copy.deepcopy(self.health_values[index])

    def run(self):
        return probe.run_probe(self.policy, self, self.health, clock=lambda: 100.)


class ProbeBehaviorTests(unittest.TestCase):
    def test_matching_inventory_never_becomes_motion_permission(self):
        f = Fixture()
        result = f.run()
        self.assertEqual(result['status'], 'READONLY_OBSERVED')
        self.assertTrue(result['observations_valid'])
        self.assertFalse(result['motion_qualified'])
        self.assertIsNone(result['current_stopped_reference_us'])
        self.assertIsNone(result['driver_build_register_readback'])
        self.assertEqual(len([x for x in result['files'] if x['role'] == 'CONTROLLER_FILE']), 25)

    def test_current_benchmark_is_reported_only_from_current_fixture(self):
        f = Fixture()
        f.data[f.policy['os_paths']['firmware']] = f.policy['firmware_names']['BENCHMARK_B4096'].encode()
        f.data[f.policy['os_paths']['vart']] = f.policy['vart_lines']['BENCHMARK_B4096'].encode()
        result = f.run()
        self.assertEqual(result['platform']['firmware_kind'], 'BENCHMARK_B4096')
        self.assertEqual(result['platform']['vart_kind'], 'BENCHMARK_B4096')
        self.assertFalse(result['platform']['vart_exact_wide'])
        self.assertFalse(result['motion_qualified'])

    def test_unreadable_firmware_stays_unknown(self):
        f = Fixture()
        f.missing.add(f.policy['os_paths']['firmware'])
        result = f.run()
        self.assertEqual(result['status'], 'READONLY_INCOMPLETE')
        self.assertEqual(result['platform']['firmware_kind'], 'UNKNOWN')
        self.assertIsNone(result['platform_stable'])

    def test_startup_change_stops_before_health_and_firmware_reads(self):
        f = Fixture()
        f.hashes[f.policy['startup_path']] = '0' * 64
        result = f.run()
        self.assertEqual(result['status'], 'CONTEXT_MISMATCH')
        self.assertTrue(result['before_owners_match'])
        self.assertEqual(f.health_calls, 0)
        self.assertNotIn(f.policy['os_paths']['firmware'], f.read_calls)

    def test_reused_pid_with_different_birth_is_rejected(self):
        f = Fixture()
        camera = next(x for x in f.policy['owners'] if x['role'] == 'CAMERA')
        path = '/proc/%d/stat' % camera['pid']
        f.data[path] = f.data[path].replace(str(camera['birth_ticks']).encode(), b'9999999')
        self.assertEqual(f.run()['status'], 'CONTEXT_MISMATCH')
        self.assertEqual(f.health_calls, 0)

    def test_effective_gui_config_change_is_not_hidden_by_component_copy(self):
        f = Fixture()
        f.hashes[f.row('EFFECTIVE_GUI_CONFIG')['path']] = '0' * 64
        result = f.run()
        self.assertEqual(result['status'], 'CONTEXT_MISMATCH')
        self.assertTrue(result['before_owners_match'])
        self.assertEqual(f.health_calls, 0)

    def test_command_hash_change_is_rejected(self):
        f = Fixture()
        camera = next(x for x in f.policy['owners'] if x['role'] == 'CAMERA')
        f.hashes['/proc/%d/cmdline' % camera['pid']] = 'f' * 64
        self.assertEqual(f.run()['status'], 'CONTEXT_MISMATCH')

    def test_owner_change_after_check_invalidates_results(self):
        f = Fixture()
        camera = next(x for x in f.policy['owners'] if x['role'] == 'CAMERA')
        path = '/proc/%d/cmdline' % camera['pid']
        f.hash_overrides[path] = lambda n: ('OK', camera['command_sha256'] if n == 1 else 'f' * 64, 1)
        result = f.run()
        self.assertEqual(result['status'], 'CONTEXT_CHANGED')
        self.assertFalse(result['observations_valid'])
        self.assertIsNone(result['health'])
        self.assertIsNone(result['files'])

    def test_platform_change_after_check_invalidates_results(self):
        f = Fixture()
        f.hash_overrides[f.policy['os_paths']['fdt']] = lambda n: ('OK', str(n) * 64, 1)
        result = f.run()
        self.assertEqual(result['status'], 'PLATFORM_CHANGED')
        self.assertFalse(result['observations_valid'])
        self.assertIsNone(result['platform'])

    def test_controller_file_mismatch_has_only_index_and_fixed_role(self):
        f = Fixture()
        row = f.row('CONTROLLER_FILE')
        f.hashes[row['path']] = '0' * 64
        result = f.run()
        failed = result['files'][row['index']]
        self.assertEqual(failed['state'], 'MISMATCH')
        self.assertNotIn('path', failed)
        self.assertNotIn('sha256', failed)

    def test_effective_config_is_checked_separately_from_gui_copy(self):
        f = Fixture()
        f.missing.add(f.row('EFFECTIVE_FACE_CONFIG')['path'])
        result = f.run()
        self.assertTrue(result['before_context_matches'])
        self.assertEqual(result['files'][f.row('GUI_FACE_CONFIG_COPY')['index']]['state'], 'MATCH')
        self.assertEqual(result['files'][f.row('EFFECTIVE_FACE_CONFIG')['index']]['state'], 'UNAVAILABLE')
        self.assertEqual(result['platform']['firmware_kind'], 'WIDE_V1')
        self.assertIsNone(result['bindings']['effective_face_release_reference_matches'])

    def test_old_boot_or_nominal_center_does_not_prove_position(self):
        result = Fixture().run()
        self.assertFalse(result['bindings']['manual_boot_matches_current'])
        self.assertFalse(result['bindings']['direction_boot_matches_current'])
        self.assertIsNone(result['current_stopped_reference_us'])
        self.assertIsNone(result['current_direction_qualified'])
        self.assertIsNone(result['physical_angle_degrees'])

    def test_missing_counters_are_not_zero(self):
        f = Fixture()
        for health in f.health_values:
            health['identity'].pop('ready')
            health['identity']['face_targets'].pop('worker_faults')
        result = f.run()['health']
        self.assertIsNone(result['identity_ready'])
        self.assertIsNone(result['counters']['face_worker_faults'])
        self.assertIsNone(result['deltas']['face_worker_faults'])

    def test_bool_negative_and_nan_do_not_become_counters(self):
        for bad in (True, -1, float('nan'), float('inf')):
            with self.subTest(bad=bad):
                f = Fixture()
                f.health_values[1]['capture_frames'] = bad
                result = f.run()['health']
                self.assertIsNone(result['counters']['capture_frames'])
                self.assertIsNone(result['deltas']['capture_frames'])

    def test_counter_rollback_has_unknown_delta(self):
        f = Fixture()
        f.health_values[1]['capture_frames'] = 1
        self.assertIsNone(f.run()['health']['deltas']['capture_frames'])

    def test_health_owner_mismatch_is_not_trusted(self):
        f = Fixture()
        f.health_values[1]['pid'] += 1
        health = f.run()['health']
        self.assertEqual(health['status'], 'HEALTH_CONTEXT_UNVERIFIED')
        self.assertIsNone(health['counters'])

    def test_health_epoch_change_is_not_trusted(self):
        f = Fixture()
        f.health_values[1]['camera_epoch'] = 'other-camera'
        self.assertIsNone(f.run()['health']['deltas'])

    def test_private_strings_and_identity_data_never_leave_projection(self):
        f = Fixture()
        for health in f.health_values:
            health['identity'].update(error='PRIVATE_SENTINEL', display_name='PRIVATE_SENTINEL',
                                     person_id='PRIVATE_SENTINEL', embedding=['PRIVATE_SENTINEL'])
        result = f.run()
        raw = json.dumps(result, allow_nan=False)
        self.assertNotIn('PRIVATE_SENTINEL', raw)
        self.assertNotIn('display_name', raw)
        self.assertNotIn('embedding', raw)
        self.assertTrue(result['health']['identity_error_present'])

    def test_manual_payload_is_followed_only_after_manifest_hash_match(self):
        f = Fixture()
        row = f.row('MANUAL_RELEASE_MANIFEST')
        f.hashes[row['path']] = 'f' * 64
        result = f.run()
        self.assertTrue(all(x['state'] == 'MANIFEST_UNVERIFIED' for x in result['manual_driver_files']))
        self.assertTrue(all(x['path'] not in f.hash_calls for x in f.policy['manual_driver_files']))


class ProbeReadOnlySurfaceTests(unittest.TestCase):
    def test_checked_sources_are_never_imported_or_executed(self):
        tree = ast.parse(SCRIPT.read_text(encoding='utf-8'))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(x.name for x in node.names)
            if isinstance(node, ast.ImportFrom):
                imports.add(node.module)
        self.assertLessEqual(imports, {'hashlib', 'http.client', 'json', 'math', 'os', 'pathlib', 'stat', 'sys', 'time'})
        names = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        self.assertFalse(names & {'write', 'write_text', 'write_bytes', 'unlink', 'rename', 'replace',
                                 'kill', 'system', 'popen', 'execv', 'Popen', 'CDLL', 'mmap'})

    def test_unlisted_path_is_rejected_before_open(self):
        reader = probe.FileReader(ORIGINAL_POLICY)
        with patch.object(probe.os, 'open') as opened:
            code, _, _ = reader.read('/unlisted/private/path', 128)
        self.assertEqual(code, 'FORBIDDEN_PATH')
        opened.assert_not_called()

    def test_character_device_or_symlink_is_not_opened(self):
        path = ORIGINAL_POLICY['os_paths']['fdt']
        reader = probe.FileReader(ORIGINAL_POLICY)
        for mode in (stat.S_IFCHR, stat.S_IFLNK):
            with self.subTest(mode=mode):
                with patch.object(probe.os, 'lstat', return_value=SimpleNamespace(st_mode=mode, st_size=0)), \
                        patch.object(probe.os, 'open') as opened:
                    code, _, _ = reader.read(path, 128)
                self.assertEqual(code, 'NOT_REGULAR')
                opened.assert_not_called()

    def test_policy_tamper_stops_before_reader_or_http(self):
        output = io.StringIO()
        with patch.object(probe, 'read_policy', return_value=b'PRIVATE_SENTINEL'), \
                patch.object(probe, 'FileReader') as reader, \
                patch.object(probe, 'get_health') as health, contextlib.redirect_stdout(output):
            code = probe.main()
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())['status'], 'POLICY_MISMATCH')
        self.assertNotIn('PRIVATE_SENTINEL', output.getvalue())
        reader.assert_not_called()
        health.assert_not_called()

    def test_nonregular_policy_companion_is_not_opened(self):
        with patch.object(probe.os, 'lstat', return_value=SimpleNamespace(st_mode=stat.S_IFLNK)), \
                patch.object(probe.os, 'open') as opened:
            raw = probe.read_policy('fixed-policy-companion')
        self.assertIsNone(raw)
        opened.assert_not_called()

    def test_read_limit_allows_exact_length_without_write_flags(self):
        path = ORIGINAL_POLICY['os_paths']['fdt']
        reader = probe.FileReader(ORIGINAL_POLICY)
        with patch.object(probe.os, 'lstat', return_value=SimpleNamespace(st_mode=stat.S_IFREG, st_size=3)), \
                patch.object(probe.os, 'open', return_value=73) as opened, \
                patch.object(probe.os, 'fstat', return_value=SimpleNamespace(st_mode=stat.S_IFREG)), \
                patch.object(probe.os, 'read', side_effect=[b'abc', b'']), \
                patch.object(probe.os, 'close') as closed:
            code, value, size = reader.read(path, 3)
        self.assertEqual((code, value, size), ('OK', b'abc', 3))
        self.assertEqual(opened.call_args.args[1] & (probe.os.O_WRONLY | probe.os.O_RDWR), 0)
        closed.assert_called_once_with(73)

    def test_byte_budget_returns_no_partial_content(self):
        path = ORIGINAL_POLICY['os_paths']['fdt']
        policy = copy.deepcopy(ORIGINAL_POLICY)
        policy['limits']['total_bytes'] = 2
        reader = probe.FileReader(policy)
        with patch.object(probe.os, 'lstat', return_value=SimpleNamespace(st_mode=stat.S_IFREG, st_size=3)), \
                patch.object(probe.os, 'open', return_value=73), \
                patch.object(probe.os, 'fstat', return_value=SimpleNamespace(st_mode=stat.S_IFREG)), \
                patch.object(probe.os, 'read', return_value=b'abc'), \
                patch.object(probe.os, 'close'):
            code, value, size = reader.read(path, 10)
        self.assertEqual(code, 'BYTE_LIMIT')
        self.assertIsNone(value)

    def test_http_error_never_exports_error_text(self):
        connection = SimpleNamespace(request=lambda *args: (_ for _ in ()).throw(OSError('PRIVATE_SENTINEL')),
                                     close=lambda: None)
        with patch.object(probe.http.client, 'HTTPConnection', return_value=connection):
            code, value = probe.get_health(ORIGINAL_POLICY)
        self.assertEqual(code, 'UNAVAILABLE')
        self.assertIsNone(value)

    def test_http_only_uses_existing_loopback_health(self):
        calls = []
        body = json.dumps({'safe': True}).encode()
        response = SimpleNamespace(status=200, read=lambda limit: body)
        connection = SimpleNamespace(request=lambda method, path: calls.append((method, path)),
            getresponse=lambda: response, close=lambda: None)
        with patch.object(probe.http.client, 'HTTPConnection', return_value=connection) as factory:
            code, value = probe.get_health(ORIGINAL_POLICY)
        self.assertEqual(code, 'OK')
        self.assertEqual(calls, [('GET', '/health')])
        self.assertEqual(factory.call_args.args, ('127.0.0.1', 8790))


if __name__ == '__main__':
    unittest.main()
