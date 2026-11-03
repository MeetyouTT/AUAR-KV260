"""Actual old/new engines over a controlled appsrc queue, no audio devices."""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest

TREE=Path('/home/ghmd/Win共享文件/语音共享文件/aura')
sys.path.insert(0,str(TREE))
from tests.framework.test_gstreamer_audio import FakePipeline,GST
from tests.framework.test_persistent_audio import Buffer


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


old=load('reviewed_unbounded_audio_engine',TREE/'tools/gstreamer_persistent_engine.py')
new=load('candidate_bounded_audio_engine',Path(__file__).with_name('gstreamer_persistent_engine.py'))


class Source:
    def __init__(self):
        self.level=0;self.drain=True;self.pushes=[];self.read_error=None;self.forced_level=None
    def get_property(self,name):
        if self.read_error:raise self.read_error
        if self.forced_level is not None:return self.forced_level
        if self.drain:self.level=0
        return self.level
    def emit(self,name,buffer):
        assert name=='push-buffer'
        self.pushes.append(buffer);self.level+=len(buffer.pcm)
        return 1


class Rig:
    def __init__(self,module):
        self.module=module;self.now=0;self.sink_time=0
        self.pipeline=FakePipeline();self.source=Source()
        self.pipeline.get_clock=lambda:SimpleNamespace(get_time=lambda:self.now)
        self.pipeline.get_base_time=lambda:0
        self.gst=SimpleNamespace(**vars(GST),Buffer=Buffer,FlowReturn=SimpleNamespace(OK=1))
        def factory(gst,device):
            sink=SimpleNamespace(query_position=lambda fmt:(True,self.sink_time))
            return self.pipeline,self.source,sink
        self.engine=module.PersistentGstAudioEngine(self.gst,'TEST_ONLY',clock=lambda:self.now/1e9,pipeline_factory=factory)
        self.advance(1.1)
        self.source.level=0;self.source.pushes.clear()
    def advance(self,seconds,*,sink_moves=True):
        target=self.now+round(seconds*1e9)
        while self.now<target:
            self.now=min(target,self.now+10000000)
            if sink_moves:self.sink_time=self.now
            self.engine.poll()


class QueueBoundTests(unittest.TestCase):
    def rig(self,module=new):
        rig=Rig(module);self.addCleanup(rig.engine.release);return rig

    def test_old_engine_exceeds_nominal_limit_when_downstream_stalls(self):
        rig=self.rig(old);rig.source.drain=False
        rig.advance(2,sink_moves=False)
        self.assertEqual(len(rig.source.pushes),100)
        self.assertEqual(rig.source.level,96000)
        self.assertGreater(rig.source.level,7680)
        self.assertEqual(rig.engine.snapshot()['device_state'],'IDLE_READY')

    def test_native_queue_stays_bounded_during_stall_and_faults_after_finite_wait(self):
        rig=self.rig();rig.source.drain=False
        rig.advance(1,sink_moves=False)
        self.assertEqual(rig.source.level,new.MAX_APPSRC_BYTES)
        self.assertEqual(len(rig.source.pushes),8)
        self.assertIsNotNone(rig.engine.pipeline)
        rig.advance(2,sink_moves=False)
        self.assertEqual(len(rig.source.pushes),8)
        self.assertIsNone(rig.engine.pipeline)
        self.assertIn('remained full',rig.engine.error)
        self.assertFalse(rig.engine.device_ready)

    def test_full_queue_does_not_pop_or_mark_unsubmitted_speech(self):
        rig=self.rig();rig.source.drain=False;rig.source.level=new.MAX_APPSRC_BYTES
        rig.engine.command({'type':'stream','token':1})
        speech=b'\x23\x01'*480
        rig.engine._append(speech,'answer')
        before=list(rig.engine.queue)
        rig.advance(.5,sink_moves=False)
        self.assertEqual(list(rig.engine.queue),before)
        self.assertEqual(rig.engine.position,0)
        self.assertEqual(rig.engine.answer_position,0)
        self.assertFalse(rig.engine.ready)
        self.assertIsNone(rig.engine.last_data_end)
        self.assertEqual(rig.source.pushes,[])

    def test_transient_backpressure_preserves_pcm_and_content_offsets(self):
        rig=self.rig();rig.source.drain=False;rig.source.level=new.MAX_APPSRC_BYTES
        rig.engine.command({'type':'stream','token':1})
        speech=b'\x23\x01'*960
        rig.engine._append(speech,'answer')
        rig.engine.command({'type':'end','token':1})
        rig.advance(.3,sink_moves=False)
        self.assertEqual(len(rig.engine.queue),2)
        rig.source.drain=True
        rig.advance(.3)
        submitted=b''.join(buffer.pcm for buffer in rig.source.pushes if any(buffer.pcm))
        self.assertEqual(submitted,speech)
        self.assertTrue(rig.engine.done)
        self.assertEqual(rig.engine.position,.04)
        self.assertEqual(rig.engine.answer_position,.04)
        self.assertEqual(rig.engine.error,'')

    def test_partial_final_packet_checks_actual_byte_count(self):
        rig=self.rig();rig.source.drain=False;rig.source.level=new.MAX_APPSRC_BYTES-2
        rig.engine.command({'type':'stream','token':1});rig.engine._append(b'\x23\x01','answer')
        rig.advance(.02,sink_moves=False)
        self.assertEqual(rig.source.level,new.MAX_APPSRC_BYTES)
        self.assertEqual([p.pcm for p in rig.source.pushes],[b'\x23\x01'])

    def test_stop_and_close_remain_responsive_during_backpressure(self):
        rig=self.rig();rig.source.drain=False;rig.source.level=new.MAX_APPSRC_BYTES
        rig.engine.command({'type':'stream','token':1});rig.engine._append(b'\x23\x01'*480,'answer')
        rig.advance(.2,sink_moves=False)
        self.assertTrue(rig.engine.command({'type':'stop','token':2}))
        self.assertFalse(rig.engine.active);self.assertFalse(rig.engine.queue)
        self.assertTrue(rig.engine.command({'type':'close','token':3}))
        self.assertIsNone(rig.engine.pipeline)

    def test_query_failure_releases_device_and_does_not_pop_speech(self):
        rig=self.rig();rig.source.read_error=AttributeError('missing current-level-bytes')
        rig.engine.command({'type':'stream','token':1});rig.engine._append(b'\x23\x01'*480,'answer')
        rig.advance(.02,sink_moves=False)
        self.assertIsNone(rig.engine.pipeline)
        self.assertEqual(rig.engine.position,0)
        self.assertEqual(rig.source.pushes,[])
        self.assertIn('queue query failed',rig.engine.error)

    def test_invalid_levels_are_faults(self):
        for value in (-1,new.MAX_APPSRC_BYTES+1,False,1.5,'123'):
            with self.subTest(value=value):
                rig=self.rig();rig.source.forced_level=value;rig.advance(.02)
                self.assertIsNone(rig.engine.pipeline)
                self.assertIn('Invalid persistent appsrc queue level',rig.engine.error)

    def test_normal_path_keeps_same_first_content_timing_and_pcm(self):
        rigs=[self.rig(old),self.rig(new)]
        for rig in rigs:
            rig.engine.command({'type':'stream','token':1})
            rig.engine._append(b'\x23\x01'*960,'answer')
            rig.engine.command({'type':'end','token':1});rig.advance(.3)
        before,after=rigs
        self.assertEqual([(x.pts,x.duration,x.pcm) for x in before.source.pushes],
                         [(x.pts,x.duration,x.pcm) for x in after.source.pushes])
        self.assertEqual(before.engine.started_at,after.engine.started_at)
        self.assertEqual(before.engine.snapshot(),after.engine.snapshot())

    def test_transient_drain_resets_backpressure_timeout(self):
        rig=self.rig();rig.source.drain=False;rig.source.level=new.MAX_APPSRC_BYTES
        rig.advance(1.2,sink_moves=False);self.assertIsNotNone(rig.engine.pipeline)
        rig.source.drain=True;rig.advance(.05)
        rig.source.drain=False;rig.source.level=new.MAX_APPSRC_BYTES
        rig.advance(1.2,sink_moves=False);self.assertIsNotNone(rig.engine.pipeline)


if __name__=='__main__':unittest.main()
