"""Use the original paired fake-device integration for changed control paths."""
import importlib.util
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value)
    return value

fixture=load('half_duplex_entry_fixture',HERE.parent/'direct_speech_entry/tests/test_direct_speech.py')
load('tools.board_recording',HERE/'instrumentation_candidate/after/tools/board_recording.py')
load('tools.handsfree_recording',HERE/'before/tools/handsfree_recording.py')
load('tools.barge_in_recording',HERE/'before/tools/barge_in_recording.py')
fixture.voice=load('half_duplex_voice',HERE/'after/tools/voice_first_recording.py')
fixture.production=load('half_duplex_production',HERE/'after/tools/production_listening.py')

class HalfDuplexTests(fixture.EntryTests):
    def test_generating_does_not_start_interruption_capture(self):
        owner,tx,inner,pair=self.make(barge_enabled=True)
        self.assertFalse(owner.barge_enabled)
        owner.capture.finish();owner.tick()
        self.assertTrue(owner.monitor_entered)
        self.assertEqual(owner.monitor_stats['submitted'],1)
        self.assertEqual(owner.public()['handsfree_dialogue']['conversation_mode'],'half_duplex')
        # The fixture interruption factory raises if called. Both generating
        # and actual playback must leave that second workload inactive.
        inner.state.update(phase='THINKING',playing=True);owner.tick()
        inner.state.update(phase='SPEAKING',playing=True);owner.tick()
        self.assertIsNone(owner.barge_capture)

    def test_new_automatic_capture_rebinds_speech_owner_before_start(self):
        owner,tx,inner,pair=self.make()
        old=owner.capture;old.cancel();owner.capture_kind='barge'
        owner._listen()
        self.assertIsNot(owner.capture,old)
        self.assertIsNotNone(owner.capture.on_speech_start)
        owner.capture.finish();owner.tick()
        self.assertEqual(len(tx.submitted),1)
        self.assertTrue(owner.monitor_entered)
        self.assertEqual(self.camera_calls,0)
