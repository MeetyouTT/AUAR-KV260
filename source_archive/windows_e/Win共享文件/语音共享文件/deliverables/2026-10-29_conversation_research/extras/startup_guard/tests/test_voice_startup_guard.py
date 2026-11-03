"""Owned temp config fixtures; actual lock, no real ports/process/GPU calls."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parents[1]
RESEARCH = HERE.parents[1]
sys.path.insert(0, str(RESEARCH / 'candidate/tools'))
sys.path.insert(0, str(HERE / 'candidate/tools'))
from service_instance_lock import ServiceAlreadyRunning, ServiceInstanceLock
import voice_startup_guard as module
from voice_startup_guard import (HOST, MODEL, MODEL_DIRECTORY, ColdStartupCapacityError,
    ReadOnlyStartupChecks, StartupGuardError, voice_startup_guard)

# Actual frozen GPU policy validation is pure stdlib, without probe/model calls.
gpu_source = RESEARCH.parent / '2026-10-29_gpu_coordination/candidate/common/gpu_coordination.py'
spec = importlib.util.spec_from_file_location('startup_guard_test_gpu_policy', gpu_source)
gpu = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gpu; spec.loader.exec_module(gpu)
UUID = 'GPU-00000000-1111-2222-3333-444444444444'


class Clock:
    def __init__(self): self.now = 10.
    def __call__(self): return self.now


class FixtureChecks(ReadOnlyStartupChecks):
    def __init__(self, fixture):
        super().__init__(clock=fixture.clock)
        self.fixture = fixture; self.calls = []; self.owner_count = 0; self.voice_count = 0
        self.free = 2098; self.total = 16311; self.uuid = UUID; self.age = 0.
        self.listener = False; self.version = '0.40.13'; self.rows = [{'name': MODEL, 'model': MODEL}]
        self.sha = fixture.record['bindings']['executable_sha256']
        self.after_owner = None
    def validate_gpu_policy(self, value): return asdict(gpu.GpuPolicy.from_dict(value))
    def voice_is_listening(self, deadline):
        self.calls.append(('voice', deadline)); self.voice_count += 1
        return self.listener if not callable(self.listener) else self.listener(self.voice_count)
    def ownership(self, deadline):
        self.calls.append(('owner', deadline)); self.owner_count += 1
        if self.after_owner: self.after_owner(self.owner_count)
        return deepcopy(self.fixture.current)
    def executable_sha256(self, filename, deadline):
        self.calls.append(('exe', deadline)); return self.sha
    def ollama_json(self, path, deadline):
        self.calls.append((path, deadline))
        if path == '/api/version': return {'version': self.version}
        if path == '/api/ps': return {'models': deepcopy(self.rows)}
        raise AssertionError('No mutable API route is allowed')
    def memory_sample(self, deadline):
        self.calls.append(('memory', deadline))
        return types.SimpleNamespace(gpu_uuid=self.uuid, total_mib=self.total,
            free_mib=self.free, observed_at=self.clock() - self.age)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        owned = HERE / 'tests'
        self.tmp = tempfile.TemporaryDirectory(prefix='owned-startup-adapter-', dir=owned)
        if not Path(self.tmp.name).resolve().is_relative_to(owned): raise RuntimeError('Fixture left owned directory')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.aura = self.root / 'aura'
        (self.aura / 'config').mkdir(parents=True)
        self.runtime_root = self.root / 'model_host'; self.runtime_root.mkdir()
        self.record_path = self.root / 'deliverables/2026-10-18_board_dialogue/project_ollama_process.json'
        self.record_path.parent.mkdir(parents=True)
        self.clock = Clock()
        self.policy = {'mode': 'adaptive', 'calibration_id': 'fixture-startup-cold', 'gpu_uuid': UUID,
            'reserve_mib': 128, 'llm_extra_mib': 128, 'llm_cold_extra_mib': 1000,
            'tts_extra_mib': 146, 'tts_cold_extra_mib': 4742}
        self.runtime = {'schema_version': 1, 'fit_target_mib': 4096,
            'calibration_id': 'fixture-layout-4096', 'gpu_uuid': UUID, 'ollama_version': '0.40.13'}
        self.current = {'pid': 123, 'creation_utc': 'stable-creation', 'executable': r'C:\Ollama\ollama.exe',
            'command_line': r'C:\Ollama\ollama.exe serve', 'parent_pid': 99,
            'listeners': [{'LocalAddress': '127.0.0.1', 'LocalPort': 11435, 'OwningProcess': 123}]}
        self.write('board_dialogue_model.json', {'model': MODEL, 'ollama_host': HOST})
        self.write('model_storage.local.json', {'ollama_directory': MODEL_DIRECTORY})
        self.write('gpu_runtime.local.json', self.policy)
        runtime_sha = self.write('ollama_runtime.local.json', self.runtime)
        self.record = {'pid': 123, 'host': HOST, 'models': MODEL_DIRECTORY, 'ready': True,
            'launch_environment_applied': True, 'effective_runner_budget_verified': False,
            'runtime_policy': dict(self.runtime, config_sha256=runtime_sha),
            'ownership': deepcopy(self.current),
            'bindings': {'ollama_version': '0.40.13', 'gpu_uuid': UUID, 'gpu_total_mib': 16311,
                'executable': self.current['executable'], 'executable_sha256': 'a' * 64}}
        self.save_record()
        self.checks = FixtureChecks(self)
    def write(self, name, value):
        raw = json.dumps(value, sort_keys=True).encode()
        (self.aura / 'config' / name).write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()
    def save_record(self): self.record_path.write_text(json.dumps(self.record), encoding='utf-8')
    def guard(self, **kw):
        values = dict(host=HOST, model=MODEL, listen='192.168.50.1', port=8792,
            deadline=310., checks=self.checks, clock=self.clock)
        values.update(kw)
        return voice_startup_guard(self.aura, self.runtime_root, **values)
    def assert_guard_error(self, error=StartupGuardError, **kw):
        with self.assertRaises(error):
            with self.guard(**kw): self.fail('Must fail before constructing any model')

    def test_insufficient_is_immediate_explicit_and_never_claims_idle(self):
        with self.assertRaises(ColdStartupCapacityError) as caught:
            with self.guard(): self.fail('Cold model must not be constructed')
        evidence = caught.exception.evidence
        self.assertEqual(evidence['cold_sample']['free_mib'], 2098)
        self.assertEqual(evidence['cold_sample']['required_free_mib'], 4870)
        self.assertFalse(evidence['no_inflight_proven']); self.assertFalse(evidence['automatic_unload'])
        self.assertTrue(evidence['extra']['controlled_reload_required'])
        self.assertIn('controlled owned-service reload', str(caught.exception))
        self.assertEqual(self.clock(), 10.)
        self.assertTrue(all(route not in ('/api/generate', '/api/chat') for route, _ in self.checks.calls))

    def test_sufficient_keeps_lifetime_lock_until_service_cleanup(self):
        self.checks.free = 6000
        with self.guard() as evidence:
            self.assertTrue(evidence['capacity_verified']); self.assertFalse(evidence['no_inflight_proven'])
            with self.assertRaises(ServiceAlreadyRunning):
                ServiceInstanceLock(self.runtime_root / 'voice8792.instance.lock').acquire()
        with ServiceInstanceLock(self.runtime_root / 'voice8792.instance.lock'): pass

    def test_service_exception_releases_lifetime_lock(self):
        self.checks.free = 6000
        with self.assertRaisesRegex(ValueError, 'owned fake service'):
            with self.guard(): raise ValueError('owned fake service')
        with ServiceInstanceLock(self.runtime_root / 'voice8792.instance.lock'): pass

    def test_existing_listener_blocks_before_owner_or_gpu(self):
        self.checks.listener = True
        self.assert_guard_error()
        self.assertEqual([c[0] for c in self.checks.calls], ['voice'])

    def test_listener_appearing_during_inspection_blocks_before_gpu(self):
        self.checks.listener = lambda count: count > 1
        self.assert_guard_error()
        self.assertNotIn('memory', [c[0] for c in self.checks.calls])

    def test_wrong_target_never_queries(self):
        for kw in ({'host': 'http://127.0.0.1:11434'}, {'model': 'other'}, {'port': 8791}):
            with self.subTest(kw=kw): self.assert_guard_error(**kw)
        self.assertEqual(self.checks.calls, [])

    def test_configured_model_or_storage_mismatch_blocks(self):
        self.write('model_storage.local.json', {'ollama_directory': r'E:\Win共享文件\models'})
        self.assert_guard_error(); self.assertEqual(self.checks.calls, [])

    def test_record_pid_creation_and_environment_must_match(self):
        for key, value in (('pid', 124), ('creation_utc', 'restarted'), ('executable', r'C:\Other\ollama.exe')):
            prior = deepcopy(self.current); self.current[key] = value
            with self.subTest(key=key): self.assert_guard_error()
            self.current = prior
        self.assertNotIn('memory', [c[0] for c in self.checks.calls])

    def test_runtime_policy_edit_requires_controlled_restart(self):
        self.runtime['fit_target_mib'] = 2048
        self.write('ollama_runtime.local.json', self.runtime)
        self.assert_guard_error()

    def test_binary_hash_drift_blocks_before_api(self):
        self.checks.sha = 'b' * 64
        self.assert_guard_error()
        self.assertNotIn('/api/version', [c[0] for c in self.checks.calls])

    def test_server_version_drift_blocks(self):
        self.checks.version = '0.40.14'; self.assert_guard_error()
        self.assertNotIn('/api/ps', [c[0] for c in self.checks.calls])

    def test_other_project_endpoint_model_is_preserved_and_rejected(self):
        self.checks.rows = [{'name': 'other', 'model': 'other'}]; self.assert_guard_error()
        self.assertNotIn('memory', [c[0] for c in self.checks.calls])

    def test_empty_ps_and_absent_voice_never_prove_no_inflight(self):
        self.checks.rows = []
        with self.assertRaises(ColdStartupCapacityError) as caught:
            with self.guard(): pass
        self.assertFalse(caught.exception.evidence['no_inflight_proven'])

    def test_owner_restart_mid_inspection_is_rejected(self):
        def restart(count):
            if count == 2: self.current['creation_utc'] = 'later-creation'
        self.checks.after_owner = restart; self.assert_guard_error()

    def test_policy_edit_mid_inspection_is_rejected(self):
        def change(count):
            if count == 2:
                value = dict(self.policy, reserve_mib=256); self.write('gpu_runtime.local.json', value)
        self.checks.after_owner = change; self.assert_guard_error()

    def test_wrong_gpu_total_uuid_or_stale_sample_is_rejected(self):
        for name, value in (('total', 16384), ('uuid', 'GPU-other'), ('age', 1.)):
            prior = getattr(self.checks, name); setattr(self.checks, name, value)
            with self.subTest(name=name): self.assert_guard_error()
            setattr(self.checks, name, prior)

    def test_original_deadline_is_shared_and_not_renewed(self):
        self.checks.free = 6000
        with self.guard(deadline=10.5): pass
        self.assertTrue(all(deadline == 10.5 for _, deadline in self.checks.calls))

    def test_elapsed_budget_prevents_next_stage(self):
        def consume(count): self.clock.now += 1.
        self.checks.after_owner = consume
        self.assert_guard_error(TimeoutError, deadline=10.5)
        self.assertNotIn('exe', [c[0] for c in self.checks.calls])

    def test_expired_or_extended_budget_rejected_before_checks(self):
        self.assert_guard_error(TimeoutError, deadline=10.)
        self.assert_guard_error(deadline=311.)
        self.assertEqual(self.checks.calls, [])

    def test_observe_retains_lock_but_reports_unverified_capacity(self):
        self.write('gpu_runtime.local.json', {'mode': 'observe'})
        with self.guard() as evidence:
            self.assertEqual(evidence['status'], 'skipped_observe')
            self.assertFalse(evidence['capacity_verified'])
            self.assertFalse(evidence['no_inflight_proven'])
        self.assertEqual([c[0] for c in self.checks.calls], ['voice'])

    def test_invalid_enforcement_policy_fails_before_listener_or_gpu(self):
        invalid = dict(self.policy, calibration_id='')
        self.write('gpu_runtime.local.json', invalid)
        self.assert_guard_error()
        self.assertEqual(self.checks.calls, [])

    def test_a_different_held_lock_cannot_substitute_for_service_lifetime_lock(self):
        with ServiceInstanceLock(self.runtime_root / 'other-owned.lock') as wrong:
            with self.assertRaises(StartupGuardError):
                module.cold_capacity_preflight(self.aura, self.runtime_root, lock=wrong,
                    deadline=310., checks=self.checks, clock=self.clock)
        self.assertEqual(self.checks.calls, [])


class DefaultCheckTests(unittest.TestCase):
    def test_inspector_subprocess_uses_remaining_budget_and_fixed_readonly_command(self):
        clock = Clock(); checks = ReadOnlyStartupChecks(clock=clock)
        result = types.SimpleNamespace(returncode=0, stdout=b'[]')
        with patch.object(module.subprocess, 'run', return_value=result) as run:
            self.assertFalse(checks.voice_is_listening(10.05))
        self.assertAlmostEqual(run.call_args.kwargs['timeout'], .05)
        command = run.call_args.args[0][-1]
        self.assertIn('LocalPort -eq 8792', command)
        self.assertIn('-ErrorAction Stop', command)
        self.assertNotIn('Stop-Process', command)

    def test_inspector_timeout_is_not_retried_or_extended(self):
        checks = ReadOnlyStartupChecks(clock=Clock())
        with patch.object(module.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fixture', .05)) as run:
            with self.assertRaises(subprocess.TimeoutExpired): checks.ownership(10.05)
        self.assertEqual(run.call_count, 1)

    def test_mutating_api_routes_are_impossible(self):
        with patch.object(module.http.client, 'HTTPConnection') as connection:
            with self.assertRaises(StartupGuardError):
                ReadOnlyStartupChecks(clock=Clock()).ollama_json('/api/generate', 11.)
        connection.assert_not_called()

    def test_oversized_or_bad_owner_query_output_is_rejected(self):
        checks = ReadOnlyStartupChecks(clock=Clock())
        result = types.SimpleNamespace(returncode=1, stdout=b'')
        with patch.object(module.subprocess, 'run', return_value=result):
            with self.assertRaises(StartupGuardError): checks.ownership(11.)


if __name__ == '__main__': unittest.main(verbosity=2)
