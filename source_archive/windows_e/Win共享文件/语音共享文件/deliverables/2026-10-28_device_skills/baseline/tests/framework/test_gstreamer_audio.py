"""Lifecycle tests for cancellation, device errors and the sink clock contract."""
from collections import deque
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import wave

from tools.gstreamer_audio_engine import GstAudioEngine, validate_clip

GST = SimpleNamespace(State=SimpleNamespace(NULL=0, PAUSED=3, PLAYING=4),
    StateChangeReturn=SimpleNamespace(FAILURE=0, SUCCESS=1),
    MessageType=SimpleNamespace(ERROR=1, EOS=2), Format=SimpleNamespace(TIME=1), SECOND=1000000000)


class FakeBus:
    def __init__(self):
        self.messages = deque()

    def timed_pop_filtered(self, timeout, mask):
        return self.messages.popleft() if self.messages else None


class FakePipeline:
    def __init__(self):
        self.bus = FakeBus()
        self.state = GST.State.NULL
        self.fail_start = False

    def get_bus(self):
        return self.bus

    def set_state(self, state):
        self.state = state
        return GST.StateChangeReturn.FAILURE if self.fail_start and state==GST.State.PLAYING else GST.StateChangeReturn.SUCCESS

    def get_state(self, timeout):
        return GST.StateChangeReturn.SUCCESS, self.state, self.state


class GstAudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'voice.wav'
        self.write_clip()
        self.sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.seconds = 0.0
        self.position = 0
        self.query_ok = True
        self.pipeline = None
        self.engine = GstAudioEngine(GST, 'hw:CARD=MCP01,DEV=0', clock=lambda:self.seconds,
                                     pipeline_factory=self.build, startup_silence_seconds=0)

    def tearDown(self):
        self.engine.release()
        self.temp.cleanup()

    def write_clip(self, rate=24000, frames=24000):
        with wave.open(str(self.path), 'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(rate)
            stream.writeframes(b'\x01\x00'*frames)

    def build(self, gst, path, device):
        self.last_pipeline_path = Path(path)
        self.pipeline = FakePipeline()
        sink = SimpleNamespace(query_position=lambda format:(self.query_ok,self.position))
        return self.pipeline, sink

    def play(self, token=1):
        return self.engine.command({'type':'play','token':token,'path':str(self.path),'sha256':self.sha})

    def test_corrupt_cache_rejected_before_any_pipeline(self):
        self.path.write_bytes(self.path.read_bytes()+b'changed')
        self.play()
        self.assertIn('SHA256 mismatch',self.engine.error)
        self.assertIsNone(self.pipeline)

    def test_wrong_format_and_empty_cache_rejected(self):
        for rate,frames in [(16000,240),(24000,0)]:
            self.write_clip(rate,frames)
            with self.assertRaises(ValueError):
                validate_clip(self.path,hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_clock_uses_sink_position_not_wall_elapsed(self):
        self.play()
        self.seconds=5
        self.position=350000000
        self.assertEqual(self.engine.poll()['clock'],.35)
        self.position=100000000
        self.assertEqual(self.engine.poll()['clock'],.35)
        self.assertTrue(self.engine.ready)

    def test_pause_freezes_and_resume_continues_same_token(self):
        self.play()
        self.position=200000000
        self.engine.poll()
        self.engine.command({'type':'pause','token':1,'paused':True})
        self.position=500000000
        self.assertEqual(self.engine.poll()['clock'],.2)
        self.engine.command({'type':'pause','token':1,'paused':False})
        self.assertEqual(self.engine.poll()['clock'],.5)

    def test_cancel_releases_pipeline_and_discards_old_eos(self):
        self.play()
        old=self.pipeline
        self.engine.command({'type':'stop','token':2})
        old.bus.messages.append(SimpleNamespace(type=GST.MessageType.EOS))
        self.assertEqual(old.state,GST.State.NULL)
        self.assertFalse(self.engine.poll()['done'])
        self.assertFalse(self.play(1))
        self.assertIsNone(self.engine.pipeline)

    def test_old_pause_does_not_change_new_playback(self):
        self.play(5)
        self.assertFalse(self.engine.command({'type':'pause','token':4,'paused':True}))
        self.assertEqual(self.pipeline.state,GST.State.PLAYING)

    def test_device_error_is_reported_and_releases_audio(self):
        self.play()
        old=self.pipeline
        old.bus.messages.append(SimpleNamespace(type=GST.MessageType.ERROR,parse_error=lambda:('Device busy','debug')))
        state=self.engine.poll()
        self.assertEqual(state['error'],'Device busy')
        self.assertFalse(state['ready'])
        self.assertEqual(old.state,GST.State.NULL)

    def test_eos_settles_duration_and_releases_device(self):
        self.play()
        old=self.pipeline
        old.bus.messages.append(SimpleNamespace(type=GST.MessageType.EOS))
        state=self.engine.poll()
        self.assertTrue(state['done'])
        self.assertEqual(state['clock'],1.0)
        self.assertEqual(old.state,GST.State.NULL)

    def test_start_timeout_does_not_use_wall_clock_as_audio_position(self):
        self.play()
        self.query_ok=False
        self.seconds=9
        state=self.engine.poll()
        self.assertIn('timed out',state['error'])
        self.assertEqual(state['clock'],0)

    def test_pause_before_preroll_does_not_timeout(self):
        self.play()
        self.query_ok=False
        self.engine.command({'type':'pause','token':1,'paused':True})
        self.seconds=20
        self.assertEqual(self.engine.poll()['error'],'')
        self.engine.command({'type':'pause','token':1,'paused':False})
        self.seconds=21
        self.assertEqual(self.engine.poll()['error'],'')


    def startup_engine(self, seconds=.5):
        self.engine = GstAudioEngine(GST, 'hw:CARD=MCP01,DEV=0', clock=lambda:self.seconds,
                                    pipeline_factory=self.build, startup_silence_seconds=seconds)

    def test_startup_preserves_original_pcm_and_offsets_content_clock(self):
        self.startup_engine()
        original = self.path.read_bytes()
        self.play()
        padded = self.last_pipeline_path
        self.assertNotEqual(padded, self.path)
        with wave.open(str(padded), 'rb') as audio:
            pcm = audio.readframes(audio.getnframes())
            self.assertEqual(audio.getnframes(), 36000)
        self.assertEqual(pcm[:24000], bytes(24000))
        self.assertEqual(pcm[24000:], b'\x01\x00'*24000)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(self.engine.duration, 1.0)
        self.position = 300000000
        state = self.engine.poll()
        self.assertEqual(state['clock'], 0)
        self.assertFalse(state['ready'])
        self.position = 650000000
        state = self.engine.poll()
        self.assertAlmostEqual(state['clock'], .15)
        self.assertTrue(state['ready'])
        self.engine.command({'type':'stop', 'token':2})
        self.assertFalse(padded.exists())

    def test_startup_eos_cleans_temporary_and_keeps_original_duration(self):
        self.startup_engine()
        self.play()
        padded = self.last_pipeline_path
        self.pipeline.bus.messages.append(SimpleNamespace(type=GST.MessageType.EOS))
        state = self.engine.poll()
        self.assertTrue(state['done'])
        self.assertEqual(state['clock'], 1.0)
        self.assertFalse(padded.exists())
        self.assertTrue(self.path.exists())

    def test_startup_pause_does_not_advance_mouth_clock(self):
        self.startup_engine()
        self.play()
        self.position = 200000000
        self.engine.command({'type':'pause','token':1,'paused':True})
        self.seconds = 20
        self.assertEqual(self.engine.poll()['clock'], 0)
        self.assertFalse(self.engine.ready)
        self.engine.command({'type':'pause','token':1,'paused':False})
        self.position = 800000000
        self.assertAlmostEqual(self.engine.poll()['clock'], .3)
        self.assertTrue(self.engine.ready)

    def test_startup_duration_is_bounded(self):
        for seconds in (-1, 3, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                GstAudioEngine(GST, 'test', startup_silence_seconds=seconds)


if __name__ == '__main__':
    unittest.main()
