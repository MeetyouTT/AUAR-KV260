"""Real VoiceFirst owner, fake capture/transport/pair; no device or model."""
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'listening_entry_fix/automatic_preference/test_production_listening.py'
spec=importlib.util.spec_from_file_location('old_listening_tests',BASE)
baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
spec=importlib.util.spec_from_file_location('cancel_rearm_candidate',HERE/'after/aura/tools/production_listening.py')
candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)
baseline.module=candidate


class CancelRearmTests(baseline.ListeningTests):
    def test_internal_cancel_and_close_do_not_persist_a_user_pause(self):
        path=self.root/'listening_preference.json'
        baseline.HandsFreeSettings(path).write(True)
        before=path.read_bytes()
        owner,_,_,_=self.make(ready=True,started=True)
        owner.tick();self.assertEqual(owner.capture.starts,1)
        result=owner.cancel()
        self.assertIsNone(result)
        self.assertEqual(owner.capture.state,'CANCELLED')
        self.assertTrue(owner.monitor_enabled)
        self.assertFalse(owner.monitor_owned)
        self.assertEqual(owner.monitor_state,'WAITING_SERVICE')
        self.assertEqual(path.read_bytes(),before)
        owner.tick();self.assertEqual(owner.capture.starts,1)
        self.now[0]+=.6
        owner.tick();self.assertEqual(owner.capture.starts,2)
        self.assertEqual(owner.monitor_state,'WAITING_WAKE')
        self.assertEqual(path.read_bytes(),before)
        owner.close()
        self.assertFalse(owner.monitor_enabled)
        self.assertEqual(path.read_bytes(),before)
        restarted,_,_,_=self.make(ready=True,started=True)
        restarted.tick();self.assertEqual(restarted.capture.starts,1)

    def test_cancel_rearms_without_creating_missing_preference(self):
        owner,_,_,_=self.make(ready=True,started=True)
        owner.tick();owner.cancel();self.now[0]+=1.;owner.tick()
        self.assertEqual(owner.capture.starts,2)
        self.assertFalse((self.root/'listening_preference.json').exists())

    def test_internal_cancel_does_not_bypass_feedback_or_native_gate(self):
        owner,business,tx,pair=self.make(ready=True,started=True)
        owner.tick();owner.cancel();pair.ready=False
        self.now[0]+=1.;owner.tick();self.assertEqual(owner.capture.starts,1)
        pair.ready=True;tx.feedback_ready=False
        owner.tick();self.assertEqual(owner.capture.starts,1)
        tx.feedback_ready=True;business.runtime.started=False
        owner.tick();self.assertEqual(owner.capture.starts,1)
        business.runtime.started=True
        owner.tick();self.assertEqual(owner.capture.starts,2)

    def test_shutdown_flags_and_already_paused_never_rearm(self):
        for flag in ('closed','_closing','runtime_closed','already_paused'):
            with self.subTest(flag=flag):
                owner,business,_,_=self.make(ready=True,started=True)
                owner.tick()
                if flag=='runtime_closed':business.runtime.closed=True
                elif flag=='already_paused':owner.monitor_enabled=False
                else:setattr(owner,flag,True)
                owner.cancel()
                self.assertFalse(owner.monitor_enabled)
                self.now[0]+=1.;owner.tick()
                self.assertEqual(owner.capture.starts,1)
                self.assertFalse((self.root/'listening_preference.json').exists())

    def test_original_cancel_exception_propagates_and_does_not_rearm(self):
        owner,business,_,pair=self.make(ready=True,started=True,bind=False)
        original=owner.cancel
        def failing_cancel():
            original()
            raise RuntimeError('public-cleanup-failure')
        owner.cancel=failing_cancel
        candidate.bind_automatic_listening(owner,business,pair)
        owner.tick()
        try:
            with self.assertRaisesRegex(RuntimeError,'public-cleanup-failure'):owner.cancel()
            self.assertFalse(owner.monitor_enabled)
            self.assertEqual(owner.capture.state,'CANCELLED')
        finally:owner.cancel=original


if __name__=='__main__':unittest.main()
