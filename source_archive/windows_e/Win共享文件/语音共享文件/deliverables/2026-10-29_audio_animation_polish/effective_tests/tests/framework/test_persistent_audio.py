"""Persistent device and sink-clock tests; fake Gst is not acoustic evidence."""
import base64
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import wave

from tools.gstreamer_persistent_engine import PersistentGstAudioEngine
from tests.framework.test_gstreamer_audio import FakePipeline,GST


class Buffer:
    @staticmethod
    def new_allocate(*args):return Buffer()
    def fill(self,offset,pcm):self.pcm=pcm


class PersistentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'clip.wav'
        self.pcm=b'\x20\x01'*4800
        with wave.open(str(self.path),'wb') as audio:
            audio.setparams((1,2,24000,0,'NONE','not compressed'));audio.writeframes(self.pcm)
        self.sha=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.now=0;self.sink_time=0;self.pushes=[];self.opens=0
        self.pipeline=FakePipeline()
        self.pipeline.get_clock=lambda:SimpleNamespace(get_time=lambda:self.now)
        self.pipeline.get_base_time=lambda:0
        self.gst=SimpleNamespace(**vars(GST),Buffer=Buffer,FlowReturn=SimpleNamespace(OK=1))
        def factory(gst,device):
            self.opens+=1
            source=SimpleNamespace(emit=lambda name,buffer:self.pushes.append(buffer) or 1,
                get_property=lambda name:0)
            sink=SimpleNamespace(query_position=lambda format:(True,self.sink_time))
            return self.pipeline,source,sink
        self.engine=PersistentGstAudioEngine(self.gst,'TEST_ONLY',clock=lambda:self.now/1e9,pipeline_factory=factory)
        self.addCleanup(self.engine.release)
        self.advance(1.1)

    def advance(self,seconds):
        target=self.now+round(seconds*1e9)
        while self.now<target:
            self.now=min(target,self.now+10000000);self.sink_time=self.now;self.engine.poll()

    def play(self,token):self.engine.command({'type':'play','token':token,'path':str(self.path),'sha256':self.sha})

    def test_two_clips_and_idle_keep_same_device_without_per_clip_padding(self):
        self.assertTrue(self.engine.device_ready)
        for token in (1,2):
            self.play(token);before=self.now;self.advance(.09)
            self.assertTrue(self.engine.ready)
            self.assertLess(self.engine.started_at-before/1e9,.1)
            self.advance(.3);self.assertTrue(self.engine.done)
            self.assertEqual(self.engine.position,.2)
            self.advance(.5)
        self.assertEqual(self.opens,1)
        self.assertIsNotNone(self.engine.pipeline)
        self.assertEqual(self.engine.snapshot()['device_state'],'IDLE_READY')

    def test_wall_schedule_does_not_forge_sink_content_time(self):
        self.play(1)
        self.now+=100000000;self.engine.poll()
        self.assertEqual(self.engine.position,0)
        self.assertFalse(self.engine.ready)

    def test_echo_reference_precedes_sound_while_history_clock_still_uses_sink(self):
        self.engine.take_references();self.play(1)
        self.now+=20000000;self.engine.poll()
        # Reference must precede echo, but must not forge playback completion.
        self.assertEqual(self.engine.position,0)
        self.engine.command({'type':'stop','token':2})
        rows=self.engine.take_references()
        self.assertTrue(any(any(row['pcm']) for row in rows))
        self.assertEqual([r['sequence'] for r in rows],sorted(r['sequence'] for r in rows))
        self.assertTrue(any(r['queued_end_ns']>self.sink_time for r in rows))

    def test_stream_feedback_not_counted_as_answer_and_audio_is_identical(self):
        self.engine.command({'type':'stream','token':1})
        self.engine.command({'type':'feedback','token':1,'path':str(self.path),'sha256':self.sha})
        for start in range(0,960,480):
            pcm=self.pcm[start*2:(start+480)*2]
            self.engine.command({'type':'pcm','token':1,'start_sample':start,'pcm':base64.b64encode(pcm).decode()})
        self.engine.command({'type':'end','token':1});self.advance(.4)
        self.assertTrue(self.engine.done)
        self.assertAlmostEqual(self.engine.position,.24)
        self.assertAlmostEqual(self.engine.answer_position,.04)
        emitted=b''.join(x.pcm for x in self.pushes if any(x.pcm))
        self.assertEqual(emitted,self.pcm+self.pcm[:1920])

    def test_stale_pcm_stop_and_duplicate_feedback_do_not_replay(self):
        self.engine.command({'type':'stream','token':1})
        value={'type':'feedback','token':1,'path':str(self.path),'sha256':self.sha}
        self.assertTrue(self.engine.command(value));self.assertFalse(self.engine.command(value))
        self.engine.command({'type':'stop','token':2})
        self.assertFalse(self.engine.command({'type':'pcm','token':1,'pcm':'AAAA','start_sample':0}))
        self.assertFalse(self.engine.queue)
        self.assertIsNotNone(self.engine.pipeline)

    def test_corrupt_clip_and_wrong_stream_offsets_rejected(self):
        with self.assertRaises(ValueError):self.engine.command({'type':'play','token':1,'path':str(self.path),'sha256':'0'*64})
        self.engine.command({'type':'stream','token':2})
        with self.assertRaises(ValueError):self.engine.command({'type':'pcm','token':2,'start_sample':1,'pcm':'AAAA'})

    def test_pause_freezes_after_queued_tail_and_resume_uses_same_device(self):
        self.play(1);self.advance(.1)
        self.engine.command({'type':'pause','token':1,'paused':True});self.advance(.15)
        position=self.engine.position;self.advance(.2);self.assertEqual(self.engine.position,position)
        self.engine.command({'type':'pause','token':1,'paused':False});self.advance(.3)
        self.assertTrue(self.engine.done);self.assertEqual(self.opens,1)
