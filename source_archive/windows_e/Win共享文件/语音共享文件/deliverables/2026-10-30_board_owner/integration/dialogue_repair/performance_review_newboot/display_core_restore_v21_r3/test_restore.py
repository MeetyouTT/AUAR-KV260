"""Public deterministic tests for the single core-policy restoration."""
import copy
import json
from pathlib import Path
import sys
import types
import unittest

import run_restore
sys.path.insert(0, str(run_restore.R2))
import restore_core as subject
import read_only_guard as guard


class Function:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *arguments):
        return self.callback(*arguments)


class Session:
    def __init__(self):
        self.now = 0.
        self.display = 123
        self.policy = dict(guard.TEMPORARY)
        self.enabled = True
        self.writes = []
        self.resets = 0
        self.tick = True
        self.x = types.SimpleNamespace(XSetScreenSaver=Function(self.set_policy),
            XResetScreenSaver=Function(self.reset), XSync=Function(lambda *args: 1))

    def set_policy(self, display, timeout, interval, blank, exposures):
        self.writes.append((timeout, interval, blank, exposures))
        self.policy = dict(timeout=timeout, interval=interval, prefer_blank=blank, allow_exposures=exposures)
        return 1

    def reset(self, display):
        self.resets += 1
        return 1

    def query(self):
        return dict(screen_saver=dict(self.policy), dpms_enabled=self.enabled, dpms_level=0,
            dpms_timeouts=[600, 600, 600], xss_state=3 if self.policy['timeout'] == 0 else 0,
            xss_kind=0, xss_idle_ms=int((self.now % 5 if self.tick else self.now) * 1000))

    def sleep(self, seconds):
        self.now += seconds


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.session = Session()
        self.saved = []

    def run_probe(self, live=lambda: {}, finish=lambda: None, persist=None):
        persist = persist or (lambda value: self.saved.append(copy.deepcopy(value)))
        return subject.restore_and_observe(self.session, live, persist, {}, finish,
                                           clock=lambda: self.session.now, sleep=self.session.sleep)

    def test_single_original_core_restore_and_single_initial_reset(self):
        result = self.run_probe()
        self.assertEqual(self.session.writes, [(600, 600, 1, 1)])
        self.assertEqual(self.session.resets, 1)
        self.assertEqual(len(result['samples']), 31)
        self.assertEqual(result['idle_drop_count'], 6)
        self.assertEqual(result['dpms_write_calls'], 0)
        self.assertEqual(result['passive_observer_reset_calls'], 0)
        self.assertEqual(result['status'], 'ORIGINAL_POLICY_RESTORED_PAUSED_KEEPALIVE_OBSERVED')

    def test_intent_persisted_before_mutation(self):
        def save(value):
            if value['status'] == 'CORE_RESTORE_INTENT_SAVED':
                self.assertEqual(self.session.writes, [])
                self.assertEqual(self.session.resets, 0)
        self.run_probe(persist=save)

    def test_intent_disk_failure_leaves_mixed_policy(self):
        def save(value):
            raise OSError('synthetic failure')
        with self.assertRaises(OSError):
            self.run_probe(persist=save)
        self.assertEqual(self.session.writes, [])
        self.assertEqual(self.session.resets, 0)

    def test_missing_tick_is_unconfirmed_and_retains_original(self):
        self.session.tick = False
        result = self.run_probe()
        self.assertEqual(result['status'], 'ORIGINAL_POLICY_RESTORED_KEEPALIVE_UNCONFIRMED')
        self.assertEqual(self.session.policy, guard.ORIGINAL)
        self.assertEqual(self.session.resets, 1)
        self.assertTrue(self.session.enabled)

    def test_owner_change_before_write_prevents_mutation(self):
        def changed():
            raise guard.Refused('LIVE_OWNER_CHANGED')
        with self.assertRaises(guard.Refused):
            self.run_probe(live=changed)
        self.assertEqual(self.session.writes, [])

    def test_pause_change_after_write_stops_without_fallback(self):
        def changed():
            if self.session.now >= 2.:
                raise guard.Refused('LIVE_PAUSE_CHANGED')
            return {}
        with self.assertRaises(guard.Refused):
            self.run_probe(live=changed)
        self.assertEqual(self.session.writes, [(600, 600, 1, 1)])
        self.assertEqual(self.session.resets, 1)
        self.assertTrue(self.session.enabled)

    def test_source_change_at_final_guard_does_not_trigger_other_writes(self):
        def changed():
            raise guard.Refused('FINAL_SEALED_OWNER_CHANGED')
        with self.assertRaises(guard.Refused):
            self.run_probe(finish=changed)
        self.assertEqual(len(self.session.writes), 1)
        self.assertEqual(self.session.resets, 1)

    def test_dpms_disabled_before_restore_is_refused(self):
        self.session.enabled = False
        with self.assertRaisesRegex(guard.Refused, '^ACTUAL_MIXED_POLICY_CHANGED$'):
            self.run_probe()
        self.assertEqual(self.session.writes, [])

    def test_missing_required_symbol_refuses_before_mutation(self):
        del self.session.x.XSync
        with self.assertRaises(AttributeError):
            self.run_probe()
        self.assertEqual(self.session.writes, [])

    def test_root_actual_metadata_is_pinned_and_matches_before(self):
        common, arguments = run_restore.local_inputs()
        evidence = arguments['current_policy_evidence']['result']
        subject.validate_before(evidence['sample'])
        self.assertEqual(evidence['owners'], arguments['baseline_owners'])
        self.assertEqual(evidence['final_owners'], arguments['baseline_owners'])

    def test_no_dpms_mutations_or_fallback_in_candidate(self):
        source = Path(subject.__file__).read_text('utf-8')
        for token in ('DPMSEnable(', 'DPMSDisable(', 'DPMSSetTimeouts(', 'DPMSForceLevel('):
            self.assertNotIn(token, source)
        self.assertIn('signal.alarm(85)', run_restore.build_remote())


if __name__ == '__main__':
    unittest.main(verbosity=2)
