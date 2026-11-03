"""No network/model/device calls: injectable owned-startup state machine."""
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

TOOLS = Path(__file__).resolve().parents[1] / 'candidate' / 'tools'
sys.path.insert(0, str(TOOLS))
from service_instance_lock import ServiceInstanceLock
import startup_vram as module
from startup_vram import (PROJECT_HOST, PROJECT_MODEL, PROJECT_MODELS_DIRECTORY,
    ProjectOllamaOwner, StartupVramError, FixedProjectOllamaApi, prepare_cold_tts_startup)

ROW = {'name': PROJECT_MODEL, 'model': PROJECT_MODEL, 'size_vram': 13874694716}


class Clock:
    def __init__(self): self.now = 10.
    def __call__(self): return self.now
    def wait(self, seconds): self.now += seconds


class FakeApi:
    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [[ROW], [ROW], []]
        self.calls = []
        self.reply = {'model': PROJECT_MODEL, 'done': True, 'done_reason': 'unload', 'response': ''}
    def ps(self, *, deadline):
        self.calls.append(('ps', deadline))
        value = self.rows.pop(0) if len(self.rows) > 1 else self.rows[0]
        if isinstance(value, Exception): raise value
        return value
    def unload(self, model, *, deadline):
        self.calls.append(('unload', deadline, model))
        return self.reply


class StartupTests(unittest.TestCase):
    def setUp(self):
        owned = Path(__file__).resolve().parent
        self.tmp = tempfile.TemporaryDirectory(prefix='aura-startup-fixture-', dir=owned)
        if not Path(self.tmp.name).resolve().is_relative_to(owned):
            raise RuntimeError('Temporary fixture left its owned workspace')
        self.addCleanup(self.tmp.cleanup)
        self.lock = ServiceInstanceLock(Path(self.tmp.name) / 'service.lock').acquire()
        self.addCleanup(self.lock.release)
        self.clock = Clock()
        self.api = FakeApi()
        self.owner = ProjectOllamaOwner(123, 'created-token', r'C:\Programs\Ollama\ollama.exe',
            PROJECT_HOST, PROJECT_MODELS_DIRECTORY, True)
        self.config = {'model': PROJECT_MODEL, 'ollama_host': PROJECT_HOST}
        self.policy = {'mode': 'adaptive', 'calibration_id': 'owned-fixture', 'gpu_uuid': 'GPU-fixture',
            'tts_cold_extra_mib': 4742, 'tts_extra_mib': 146, 'reserve_mib': 128}
        self.free = [250, 250, 6000]
        self.deadlines = []
    def owner_probe(self, deadline):
        self.deadlines.append(deadline); return self.owner
    def memory(self, deadline):
        self.deadlines.append(deadline)
        value = self.free.pop(0) if len(self.free) > 1 else self.free[0]
        return types.SimpleNamespace(gpu_uuid='GPU-fixture', free_mib=value, observed_at=self.clock())
    def run_prepare(self, **overrides):
        values = dict(lock=self.lock, deadline=11., expected_owner=self.owner, verify_owner=self.owner_probe,
            voice_is_listening=lambda deadline: False, memory_sample=self.memory,
            api=self.api, clock=self.clock, wait=self.clock.wait)
        values.update(overrides)
        return prepare_cold_tts_startup(self.config, self.policy, **values)
    def unloads(self): return [r for r in self.api.calls if r[0] == 'unload']

    def test_only_owned_model_is_unloaded_for_insufficient_cold_capacity(self):
        value = self.run_prepare()
        self.assertEqual(value['status'], 'released_project_cache')
        self.assertTrue(value['capacity_verified'])
        self.assertEqual(value['required_free_mib'], 4870)
        self.assertEqual(self.unloads(), [('unload', 11., PROJECT_MODEL)])
        self.assertTrue(all(row[1] == 11. for row in self.api.calls))
        self.assertTrue(all(d == 11. for d in self.deadlines))

    def test_free_threshold_uses_cold_not_steady_and_exact_threshold_passes(self):
        self.free = [4870]
        value = self.run_prepare()
        self.assertEqual(value['status'], 'sufficient')
        self.assertFalse(self.unloads())

    def test_steady_capacity_alone_does_not_permit_cold_start(self):
        self.free = [300, 300, 6000]
        self.assertTrue(self.run_prepare()['unloaded'])

    def test_memory_recovering_before_post_preserves_project_cache(self):
        self.free = [250, 6000]
        self.assertEqual(self.run_prepare()['status'], 'sufficient')
        self.assertFalse(self.unloads())

    def test_observe_skips_all_inspection_and_mutation(self):
        self.policy['mode'] = 'observe'
        value = self.run_prepare(verify_owner=Mock(side_effect=AssertionError('must not inspect')))
        self.assertEqual(value['status'], 'skipped_observe')
        self.assertFalse(value['capacity_verified']); self.assertFalse(self.api.calls)

    def test_missing_calibration_skips_operation(self):
        del self.policy['calibration_id']
        self.assertEqual(self.run_prepare()['status'], 'skipped_uncalibrated')
        self.assertFalse(self.api.calls)

    def test_11434_config_never_calls_api(self):
        self.config['ollama_host'] = 'http://127.0.0.1:11434'
        with self.assertRaises(StartupVramError): self.run_prepare()
        self.assertFalse(self.api.calls)

    def test_other_model_config_never_calls_api(self):
        self.config['model'] = 'someone-elses-model'
        with self.assertRaises(StartupVramError): self.run_prepare()
        self.assertFalse(self.api.calls)

    def test_no_lifetime_lock_prevents_all_calls(self):
        self.lock.release()
        with self.assertRaises(StartupVramError): self.run_prepare()
        self.assertFalse(self.api.calls)

    def test_voice_listener_or_unknown_state_prevents_calls(self):
        for state in (True, None):
            with self.subTest(state=state), self.assertRaises(StartupVramError):
                self.run_prepare(voice_is_listening=lambda deadline: state)
        self.assertFalse(self.api.calls)

    def test_no_inflight_must_be_explicitly_established(self):
        with self.assertRaises(StartupVramError):
            self.run_prepare(verify_owner=lambda deadline: replace(self.owner, no_inflight=False))
        self.assertFalse(self.api.calls)

    def test_malformed_owner_evidence_fails_closed(self):
        with self.assertRaises(StartupVramError):
            self.run_prepare(verify_owner=lambda deadline: replace(self.owner, models_directory=None))
        self.assertFalse(self.api.calls)

    def test_owner_change_immediately_before_unload_prevents_post(self):
        count = [0]
        def changed(deadline):
            count[0] += 1
            return self.owner if count[0] == 1 else replace(self.owner, pid=124)
        with self.assertRaises(StartupVramError): self.run_prepare(verify_owner=changed)
        self.assertFalse(self.unloads())

    def test_other_11435_model_is_left_untouched(self):
        self.api.rows = [[ROW, {'name': 'other', 'model': 'other'}]]
        with self.assertRaises(StartupVramError): self.run_prepare()
        self.assertFalse(self.unloads())

    def test_other_model_appearing_before_post_is_left_untouched(self):
        self.api.rows = [[ROW], [{'name': 'other', 'model': 'other'}]]
        with self.assertRaises(StartupVramError): self.run_prepare()
        self.assertFalse(self.unloads())

    def test_wrong_or_stale_gpu_sample_cannot_trigger_unload(self):
        for sample in (
            types.SimpleNamespace(gpu_uuid='GPU-other', free_mib=250, observed_at=10.),
            types.SimpleNamespace(gpu_uuid='GPU-fixture', free_mib=250, observed_at=8.),
            types.SimpleNamespace(gpu_uuid='GPU-fixture', free_mib=None, observed_at=10.)):
            with self.subTest(sample=sample), self.assertRaises(StartupVramError):
                self.run_prepare(memory_sample=lambda deadline: sample)
        self.assertFalse(self.unloads())

    def test_insufficient_without_owned_cache_fails_without_mutation(self):
        self.api.rows = [[]]
        with self.assertRaises(StartupVramError): self.run_prepare()
        self.assertFalse(self.unloads())

    def test_natural_expiry_does_not_issue_unload(self):
        self.api.rows = [[ROW], [], []]
        value = self.run_prepare()
        self.assertEqual(value['status'], 'naturally_released')
        self.assertFalse(self.unloads())

    def test_acknowledgement_alone_is_not_memory_recovery(self):
        self.api.rows = [[ROW], [ROW], [], []]
        self.free = [250, 250, 300, 6000]
        self.assertEqual(self.run_prepare()['after_free_mib'], 6000)
        self.assertGreater(self.clock(), 10.)
        self.assertEqual(len(self.unloads()), 1)

    def test_memory_recovery_alone_is_not_model_disappearance(self):
        self.api.rows = [[ROW], [ROW], [ROW], []]
        self.free = [250, 250, 6000, 6000]
        self.assertTrue(self.run_prepare()['unloaded'])
        self.assertGreater(self.clock(), 10.)

    def test_no_retry_unload_or_budget_extension_on_timeout(self):
        self.api.rows = [[ROW]]; self.free = [250]
        with self.assertRaises(TimeoutError): self.run_prepare(deadline=10.2)
        self.assertEqual(self.unloads(), [('unload', 10.2, PROJECT_MODEL)])
        self.assertLessEqual(self.clock(), 10.200001)

    def test_expired_original_deadline_prevents_initial_api(self):
        with self.assertRaises(TimeoutError): self.run_prepare(deadline=10.)
        self.assertFalse(self.api.calls)

    def test_api_consuming_remaining_budget_prevents_post(self):
        original = self.api.ps
        def slow(*, deadline): self.clock.wait(.2); return original(deadline=deadline)
        self.api.ps = slow
        with self.assertRaises(TimeoutError): self.run_prepare(deadline=10.1)
        self.assertFalse(self.unloads())

    def test_unload_response_requires_explicit_success(self):
        self.api.reply = {'done': True, 'done_reason': 'stop', 'model': PROJECT_MODEL, 'response': ''}
        with self.assertRaises(StartupVramError): self.run_prepare()
        self.assertEqual(len(self.unloads()), 1)


class ApiProtocolTests(unittest.TestCase):
    def test_constructor_has_no_network_side_effect(self):
        with patch.object(module.http.client, 'HTTPConnection') as connection:
            FixedProjectOllamaApi()
        connection.assert_not_called()

    def test_exact_fixed_unload_body_omits_prompt_and_uses_shared_deadline(self):
        clock = Clock()
        api = FixedProjectOllamaApi(clock=clock)
        api._request = Mock(return_value={})
        api.unload(PROJECT_MODEL, deadline=11.)
        api._request.assert_called_once_with('POST', '/api/generate',
            {'model': PROJECT_MODEL, 'keep_alive': 0, 'stream': False}, deadline=11.)
        with self.assertRaises(StartupVramError): api.unload('other', deadline=11.)
        self.assertEqual(api._request.call_count, 1)

    def test_http_connect_header_body_share_absolute_budget_and_close(self):
        clock = Clock()
        connection = Mock()
        connection.connect.side_effect = lambda: clock.wait(.2)
        response = Mock(status=200)
        response.read.return_value = b'{"models":[]}'
        connection.getresponse.return_value = response
        timer = Mock()
        with patch.object(module.http.client, 'HTTPConnection', return_value=connection) as factory:
            with patch.object(module.threading, 'Timer', return_value=timer) as timer_factory:
                value = FixedProjectOllamaApi(clock=clock).ps(deadline=11.)
        factory.assert_called_once_with('127.0.0.1', 11435, timeout=1.)
        self.assertAlmostEqual(timer_factory.call_args.args[0], .8)
        timer_factory.call_args.args[1]()
        connection.sock.shutdown.assert_called_once()
        response.read.assert_called_once_with(module.MAX_RESPONSE + 1)
        self.assertEqual(value, [])
        timer.start.assert_called_once(); timer.cancel.assert_called_once(); connection.close.assert_called_once()

    def test_unapproved_http_route_cannot_connect(self):
        with patch.object(module.http.client, 'HTTPConnection') as connection:
            with self.assertRaises(ValueError):
                FixedProjectOllamaApi()._request('DELETE', '/api/delete', {}, deadline=100.)
        connection.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
