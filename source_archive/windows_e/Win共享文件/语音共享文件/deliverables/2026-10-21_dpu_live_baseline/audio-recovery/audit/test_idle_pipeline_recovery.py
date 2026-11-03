"""Lifecycle regression against the exact recovered engine, without native Gst."""
import importlib.util
import pathlib
import sys
import types
import unittest

from idle_pipeline_recovery import IdlePipelineRecovery

ROOT = pathlib.Path(__file__).resolve().parents[1] / 'live-source'
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('recovered_persistent', ROOT / 'tools/gstreamer_persistent_engine.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Pipeline:
    def __init__(self, failing=False):
        self.states = []
        self.failing = failing

    def set_state(self, state):
        self.states.append(state)
        return 'FAILURE' if self.failing and state == 'PLAYING' else 'SUCCESS'

    def get_bus(self):
        return types.SimpleNamespace(timed_pop_filtered=lambda *args: None)

    def get_clock(self):
        return None


class Engine(IdlePipelineRecovery, module.PersistentGstAudioEngine):
    pass


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000.
        self.opened = []
        self.gst = types.SimpleNamespace(
            State=types.SimpleNamespace(PLAYING='PLAYING', NULL='NULL'),
            StateChangeReturn=types.SimpleNamespace(FAILURE='FAILURE'),
            MessageType=types.SimpleNamespace(ERROR='ERROR'))

        def factory(gst, device):
            pipeline = Pipeline()
            self.opened.append(pipeline)
            return pipeline, object(), object()

        self.factory = factory
        # configure before __init__: the inherited constructor can call release.
        self.engine = Engine.__new__(Engine)
        self.engine.configure_idle_recovery(factory)
        module.PersistentGstAudioEngine.__init__(self.engine, self.gst, 'MCP01',
            clock=lambda: self.now, pipeline_factory=factory)

    def recover(self, **kw):
        fields = dict(expected_token=self.engine.token, new_token=self.engine.token + 1,
                      controller_idle=True, capture_idle=True)
        fields.update(kw)
        return self.engine.recover_idle(**fields)

    def test_stop_keeps_existing_pipeline(self):
        first = self.engine.pipeline
        self.engine.command({'type': 'stop', 'token': 1})
        self.assertIs(self.engine.pipeline, first)
        self.assertEqual(first.states, ['PLAYING'])

    def test_busy_content_never_released(self):
        for field, value in [('active', True), ('paused', True), ('audible', True),
                             ('queue', [b'pending']), ('intervals', [1])]:
            original = getattr(self.engine, field)
            setattr(self.engine, field, value)
            self.assertFalse(self.recover(), field)
            self.assertEqual(len(self.opened), 1)
            setattr(self.engine, field, original)

    def test_external_idle_and_pending_commands_guard(self):
        for kw in ({'controller_idle': False}, {'controller_idle': 1},
                   {'capture_idle': False}, {'capture_idle': 1}, {'commands_pending': True}):
            self.assertFalse(self.recover(**kw))
        self.assertEqual(len(self.opened), 1)

    def test_token_guards_do_not_mutate(self):
        for kw in ({'expected_token': -1}, {'new_token': 0}, {'new_token': 2}, {'expected_token': False}):
            self.assertFalse(self.recover(**kw))
        self.assertEqual(self.engine.token, 0)
        self.assertEqual(len(self.opened), 1)

    def test_rebuild_invalidates_old_generation_and_clock(self):
        old = self.engine.pipeline
        self.engine.references.append({'sequence': 55, 'pcm': b'old'})
        self.engine.reference_sequence = 55
        self.engine.next_pts = 9000000000
        self.engine.device_ready = True
        self.assertTrue(self.recover())
        self.assertEqual(old.states, ['PLAYING', 'NULL'])
        self.assertEqual(self.engine.next_pts, 0)
        self.assertFalse(self.engine.device_ready)
        self.assertEqual(self.engine.take_references(), [])
        self.assertEqual(self.engine.reference_sequence, 55)
        self.assertEqual(self.engine.token, 1)
        self.assertFalse(self.engine.command({'type': 'play', 'token': 0}))
        self.assertEqual(self.engine.snapshot()['device_state'], 'RECOVERING')

    def test_failure_releases_new_pipeline_and_reports_error(self):
        failed = Pipeline(failing=True)
        self.engine._recovery_factory = lambda *args: (failed, object(), object())
        self.assertTrue(self.recover())
        self.assertIsNone(self.engine.pipeline)
        self.assertIn('recovery start failed', self.engine.error)
        self.assertEqual(self.engine.recovery_state, 'ERROR')
        self.assertEqual(failed.states, ['PLAYING', 'NULL'])

    def test_warmup_timeout_releases(self):
        self.recover()
        self.now += 8
        self.assertEqual(self.engine.poll()['recovery_state'], 'ERROR')
        self.assertIsNone(self.engine.pipeline)

    def test_clock_ready_does_not_claim_usb_health(self):
        self.recover()
        self.engine.device_ready = True
        snapshot = self.engine.poll()
        self.assertEqual(snapshot['recovery_state'], 'READY_UNVERIFIED')
        self.assertEqual(snapshot['usb_playback_health'], 'UNVERIFIED')

    def test_retry_backoff_and_burst_limit(self):
        self.recover()
        self.engine.recovery_state = 'READY_UNVERIFIED'
        self.now += 59
        self.assertFalse(self.recover())
        self.now += 1
        self.assertTrue(self.recover())
        self.engine.recovery_state = 'READY_UNVERIFIED'
        self.now += 100
        self.assertFalse(self.recover())
        self.now += 441
        self.assertTrue(self.recover())

    def test_reference_epoch_changes_with_rebuild(self):
        self.recover()
        self.engine.references.append({'sequence': 1, 'pcm': b'new'})
        self.assertEqual(self.engine.take_references()[0]['pipeline_epoch'], 1)

    def test_new_turn_waits_for_warmup_and_close_still_releases(self):
        self.recover()
        self.assertFalse(self.engine.command({'type': 'stream', 'token': 2}))
        self.assertFalse(self.engine.active)
        self.assertTrue(self.engine.command({'type': 'close', 'token': 2}))
        self.assertEqual(self.engine.poll()['recovery_state'], 'CLOSED')
        self.assertIsNone(self.engine.pipeline)

    def test_fail_drops_undelivered_references(self):
        self.recover()
        self.engine.references.append({'sequence': 3, 'pcm': b'silence'})
        self.engine.fail('simulated sink error')
        self.assertEqual(self.engine.take_references(), [])
        self.assertIsNone(self.engine.bus)


if __name__ == '__main__':
    unittest.main()
