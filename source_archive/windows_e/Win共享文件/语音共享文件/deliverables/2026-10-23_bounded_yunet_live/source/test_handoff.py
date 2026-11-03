"""Fault injection for owned transition ordering and foreign-state refusal."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import handoff


class FakeOps:
    def __init__(self,fail=None):
        self.events=[];self.target='original';self.audio=True;self.guard=True;self.fail=fail;self.failed=False
    def step(self,name):
        self.events.append(name)
        if self.fail==name and not self.failed:
            self.failed=True;raise RuntimeError('injected '+name)
    def verify(self):self.step('verify')
    def ready(self,target):return self.target==target and self.audio
    def assert_idle_or_stopped(self):self.step('idle')
    def assert_guard_armed(self):self.step('guard');assert self.guard
    def stop_audio(self):self.step('stop_audio');self.audio=False
    def wait_pcm_closed(self):self.step('pcm_closed');assert not self.audio
    def switch_camera(self,target):self.step('camera_'+target);assert not self.audio;self.target=target
    def wait_camera(self,target):self.step('ready_'+target);assert self.target==target and not self.audio
    def restore_preference(self):self.step('preference')
    def start_audio(self):self.step('start_audio');self.audio=True
    def wait_audio_ready(self):self.step('audio_ready');assert self.audio


class ProtocolTests(unittest.TestCase):
    def test_audio_is_closed_before_camera_and_reopened_after_health(self):
        ops=FakeOps();handoff.transition(ops,'candidate')
        self.assertLess(ops.events.index('guard'),ops.events.index('stop_audio'))
        self.assertLess(ops.events.index('pcm_closed'),ops.events.index('camera_candidate'))
        self.assertLess(ops.events.index('ready_candidate'),ops.events.index('start_audio'))
        self.assertEqual(ops.target,'candidate');self.assertTrue(ops.audio)

    def test_original_ready_restore_is_idempotent_without_service_restart(self):
        ops=FakeOps();ops.guard=False
        self.assertTrue(handoff.transition(ops,'original')['already_ready'])
        self.assertEqual(ops.events,['verify'])

    def test_baseline_force_restarts_same_camera_with_audio_closed(self):
        ops=FakeOps();handoff.transition(ops,'original',force=True)
        self.assertIn('camera_original',ops.events);self.assertTrue(ops.audio)

    def test_no_guard_or_busy_ui_cannot_stop_audio(self):
        ops=FakeOps();ops.guard=False
        with self.assertRaises(AssertionError):handoff.transition(ops,'candidate')
        self.assertNotIn('stop_audio',ops.events)
        ops=FakeOps('idle')
        with self.assertRaises(RuntimeError):handoff.transition(ops,'candidate')
        self.assertNotIn('stop_audio',ops.events)

    def test_all_transition_failures_restore_original_and_audio(self):
        for failure in ('stop_audio','pcm_closed','camera_candidate','ready_candidate','preference','start_audio','audio_ready'):
            with self.subTest(failure=failure):
                ops=FakeOps(failure)
                with self.assertRaises(RuntimeError):handoff.owned_operation(ops,'candidate',lambda:None)
                self.assertTrue(ops.audio);self.assertEqual(ops.target,'original')

    def test_observation_failure_restores_after_successful_switch(self):
        ops=FakeOps()
        def fail():raise RuntimeError('observation failed')
        with self.assertRaises(RuntimeError):handoff.owned_operation(ops,'candidate',fail)
        self.assertEqual(ops.target,'original');self.assertTrue(ops.audio)

    def test_success_returns_observation_and_still_restores_original(self):
        ops=FakeOps();value=handoff.owned_operation(ops,'candidate',lambda:123)
        self.assertEqual(value,123);self.assertEqual(ops.target,'original');self.assertTrue(ops.audio)


class PinChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.unit=self.root/'camera.unit';self.unit.write_bytes(b'original')
        self.wrapper=self.root/'wrapper.py';self.wrapper.write_bytes(b'pass\n')
        self.source=self.root/'source.py';self.source.write_bytes(b'pass\n')
        self.pref=self.root/'pref.json';self.pref.write_bytes(b'original-pref')
        self.ops=handoff.BoardOps.__new__(handoff.BoardOps);self.ops.folder=self.root
        self.ops.m=SimpleNamespace(UNIT=self.unit,atomic=lambda p,data:Path(p).write_bytes(data))
        self.ops.meta={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'protected':{str(self.source):handoff.digest(self.source)},
            'unit_hashes':{'original':handoff.digest(self.unit),'candidate':hashlib.sha256(b'candidate').hexdigest()},
            'wrapper':str(self.wrapper),'wrapper_sha256':handoff.digest(self.wrapper),'xserver_pid':99,
            'preference_sha256':handoff.digest(self.pref),'allowed_preference_hashes':[handoff.digest(self.pref)]}
        self.ops.pid=lambda name:99;self.ops.active=lambda name:True
        self.patches=[patch.object(handoff,'BOOT',self.ops.meta['boot']),patch.object(handoff,'PREF',self.pref)]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()
    def test_original_and_owned_candidate_units_are_allowed(self):
        self.ops.verify();self.unit.write_bytes(b'candidate');self.ops.verify()
    def test_foreign_unit_or_source_is_refused_without_overwrite(self):
        self.unit.write_bytes(b'foreign')
        with self.assertRaises(AssertionError):self.ops.verify()
        self.assertEqual(self.unit.read_bytes(),b'foreign')
        self.unit.write_bytes(b'original');self.source.write_bytes(b'foreign')
        with self.assertRaises(AssertionError):self.ops.verify()
    def test_changed_wrapper_or_xserver_is_refused(self):
        self.wrapper.write_bytes(b'foreign')
        with self.assertRaises(AssertionError):self.ops.verify()
        self.wrapper.write_bytes(b'pass\n');self.ops.pid=lambda name:100
        with self.assertRaises(AssertionError):self.ops.verify()
    def test_boot_mismatch_is_refused(self):
        self.ops.meta['boot']='different'
        with self.assertRaises(AssertionError):self.ops.verify()
    def test_foreign_preference_is_not_clobbered(self):
        self.pref.write_bytes(b'user-changed')
        with self.assertRaises(AssertionError):self.ops.verify()
        self.assertEqual(self.pref.read_bytes(),b'user-changed')
    def test_preference_only_restores_recorded_owned_stop_change(self):
        original=self.pref.read_bytes();(self.root/'preference.original').write_bytes(original)
        self.pref.write_bytes(b'owned-stop-save')
        self.ops.meta['allowed_preference_hashes'].append(handoff.digest(self.pref))
        self.ops.restore_preference();self.assertEqual(self.pref.read_bytes(),original)
    def test_idle_guard_refuses_recording_or_motion(self):
        self.ops.m.ui_idle=lambda:None
        state={'pending_job':None,'playing':False,'paused':False,'local_recording':{'state':'IDLE','can_stop':False},
               'local_transcription':{'service':{'pending':False}},'manual_pan':{'automatic_following':False,'pulse_us':None}}
        self.ops.ui=lambda:state
        self.ops.assert_idle_or_stopped()
        for section,key,value in [('local_recording','can_stop',True),('manual_pan','pulse_us',1500)]:
            old=state[section][key];state[section][key]=value
            with self.assertRaises(AssertionError):self.ops.assert_idle_or_stopped()
            state[section][key]=old

    def test_missing_audio_device_is_not_treated_as_pcm_closed(self):
        with patch.object(handoff.Path,'exists',return_value=False):
            with self.assertRaises(RuntimeError):self.ops.wait_pcm_closed()

    def test_pcm_close_cursor_covers_subsequent_camera_and_audio_startup(self):
        self.ops.m.kernel_cursor=lambda:'owned-quiescent-cursor'
        saved=[];self.ops.save_meta=lambda:saved.append(True)
        with patch.object(handoff.Path,'exists',return_value=True),patch.object(handoff.Path,'read_text',return_value='closed'):
            self.ops.wait_pcm_closed()
        self.assertEqual(self.ops.meta['quiescent_cursor'],'owned-quiescent-cursor')
        self.assertEqual(saved,[True])


if __name__=='__main__':unittest.main()
