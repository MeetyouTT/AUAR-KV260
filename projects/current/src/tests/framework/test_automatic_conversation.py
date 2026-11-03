"""Hands-free turn boundaries, playback/ACK ordering, and stop ownership."""
import io
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
import numpy as np

from board.runtime.audio.automatic_capture import SpeechEndpoint, AutomaticMcp01Capture
from board.runtime.audio.capture import CapturedAudio, FORMAT
from host.model_service.protocol import AudioRef
from tools.board_recording import RecordingController
from tools.board_avatar_gtk import BoardAvatarStage


def frames(count, loud=False):
    values=(np.sin(np.arange(count*320)*2*np.pi*220/16000)*5000).astype('<i2') if loud else np.zeros(count*320,dtype='<i2')
    return values.tobytes()


class EndpointTests(unittest.TestCase):
    def test_long_idle_does_not_submit_or_accumulate_pcm(self):
        endpoint=SpeechEndpoint()
        for _ in range(3000):self.assertIsNone(endpoint.feed(frames(1)))
        self.assertFalse(endpoint.active)
        self.assertLessEqual(len(endpoint.ring),19)
        self.assertLess(len(endpoint.pending),640)

    def test_short_noise_is_not_a_turn(self):
        endpoint=SpeechEndpoint()
        for raw in (frames(30),frames(5,True),frames(60)):
            self.assertIsNone(endpoint.feed(raw))
        self.assertFalse(endpoint.active)

    def test_pre_roll_preserves_exact_pcm_and_short_pause_is_not_endpoint(self):
        endpoint=SpeechEndpoint()
        source=frames(50)+frames(30,True)+frames(15)+frames(20,True)+frames(35)
        result=None
        for pos in range(0,len(source),127):
            value=endpoint.feed(source[pos:pos+127])
            if value is not None:result=value;break
        self.assertIsNotNone(result)
        self.assertEqual(endpoint.start_sample,40*320)
        self.assertEqual(result,source[40*640:])
        self.assertFalse(endpoint.active)

    def test_long_speech_is_bounded_by_existing_asr_limit(self):
        endpoint=SpeechEndpoint(max_seconds=2)
        result=endpoint.feed(frames(120,True))
        self.assertIsNotNone(result)
        self.assertLessEqual(len(result),2*16000*2)


class FakeCapture:
    def __init__(self,*args,**kwargs):self.state='IDLE';self.counter=0;self.closed=False
    def start(self):self.counter+=1;self.state='RECORDING';return 'cap-'+str(self.counter)
    def snapshot(self):return {'state':self.state,'error':'','sample_count':16000,'speech_active':False}
    def take(self):
        assert self.state=='READY';self.state='IDLE'
        return CapturedAudio('cap-'+str(self.counter),AudioRef(1,0,16000,FORMAT),b'\x01\x00'*16000,100,1100)
    def cancel(self):self.state='CANCELLED'
    def close(self):self.cancel();self.closed=True


class FakeTranscriber:
    feedback_assets={}
    def __init__(self):self.pending=False;self.last_ack=None;self.submitted=[];self.cancelled=0;self.ack_calls=[]
    def enabled(self):return True
    def public(self):return {'enabled':True,'streaming':True,'feedback_ready':True,'pending':self.pending,'last_playback_ack':self.last_ack}
    def cancel(self):self.cancelled+=1;self.pending=False
    def submit(self,clip):
        self.pending=True;self.submitted.append(clip)
        return {'request_id':'req-'+str(len(self.submitted))}
    def poll(self):return None
    def acknowledge(self,owner,value):self.ack_calls.append(owner)
    def close(self):self.cancel()


class FakeController:
    def __init__(self):
        self.last_error='';self.completions=[]
        self.state={'phase':'IDLE','playing':False,'paused':False,'pending_job':None,'audio_output_state':'IDLE_READY'}
    def public(self):return dict(self.state)
    def tick(self):return None
    def take_completion(self):return self.completions.pop(0) if self.completions else None
    def cancel(self):self.state.update(phase='IDLE',playing=False,paused=False,pending_job=None)


class AutomaticOwnerTests(unittest.TestCase):
    def setUp(self):
        self.now=[10.];self.tx=FakeTranscriber();self.inner=FakeController()
        self.owner=RecordingController(self.inner,capture_factory=FakeCapture,auto_capture_factory=FakeCapture,
                                       transcriber=self.tx,clock=lambda:self.now[0])
        self.addCleanup(self.owner.close)
    def submitted(self):
        self.owner.conversation_start();self.owner.capture.state='READY';self.owner.tick()
        self.assertEqual(len(self.tx.submitted),1)
        return dict(request_id='req-1',capture_id='cap-1')
    def complete(self,owner):
        self.inner.completions.append((owner,{}));self.tx.pending=False;self.owner.tick()
    def test_silent_listening_never_calls_asr(self):
        self.owner.conversation_start()
        for _ in range(20):self.owner.tick()
        self.assertEqual(self.tx.submitted,[])
    def test_no_rearm_during_inference_or_playback(self):
        self.submitted();self.inner.state.update(phase='SPEAKING',playing=True)
        self.now[0]+=30;self.owner.tick()
        self.assertEqual(self.owner.capture.counter,1)
        self.assertTrue(self.owner.auto_enabled)
    def test_playback_ack_and_tail_guard_are_both_required_for_next_turn(self):
        owner=self.submitted();self.complete(owner)
        self.tx.last_ack=dict(request_id='old',committed=True)
        self.now[0]+=.4;self.owner.tick();self.assertEqual(self.owner.capture.counter,1)
        self.tx.last_ack=dict(request_id='req-1',committed=True)
        self.owner.tick();self.assertEqual(self.owner.capture.counter,1)
        self.now[0]+=.2;self.owner.tick()
        self.assertEqual(self.owner.capture.counter,2)
        self.assertEqual(self.owner.auto_turns,1)
    def test_failed_ack_stops_automatic_mode(self):
        owner=self.submitted();self.complete(owner)
        self.tx.last_ack=dict(request_id='req-1',committed=False)
        self.owner.tick();self.assertFalse(self.owner.auto_enabled)
        self.assertEqual(self.owner.public()['automatic_conversation']['state'],'ERROR')
    def test_ack_timeout_is_visible_and_does_not_loop(self):
        owner=self.submitted();self.complete(owner)
        self.now[0]+=8;self.owner.tick()
        self.assertFalse(self.owner.auto_enabled);self.assertIn('超时',self.owner.auto_error)
    def test_stop_rejects_late_completion_and_never_rearms(self):
        owner=self.submitted();self.owner.conversation_stop();self.complete(owner)
        self.now[0]+=30;self.owner.tick()
        self.assertFalse(self.owner.auto_enabled);self.assertEqual(self.tx.ack_calls,[])
        self.assertEqual(self.owner.capture.counter,1)
    def test_manual_capture_and_demos_are_blocked_while_session_is_enabled(self):
        self.owner.conversation_start()
        with self.assertRaises(ValueError):self.owner.record_start()
        with self.assertRaises(ValueError):self.owner.record_stop()
        with self.assertRaises(ValueError):self.owner.submit('demo')


class AutomaticRoutingTests(unittest.TestCase):
    def test_main_button_can_stop_during_playback(self):
        stage=BoardAvatarStage.__new__(BoardAvatarStage);stage.config={'automatic_turns':True}
        calls=[]
        stage.controller=SimpleNamespace(public=lambda:{'phase':'SPEAKING','automatic_conversation':{'enabled':True}},
            conversation_stop=lambda:calls.append('stop') or 'stop-id')
        self.assertTrue(stage.command({'type':'record_toggle'})['queued']);self.assertEqual(calls,['stop'])


@unittest.skipIf(sys.platform=='win32','Actual capture ownership uses Linux flock')
class AutomaticCaptureLifecycleTests(unittest.TestCase):
    def test_endpoint_stops_process_and_preserves_bounded_clip(self):
        class Process:
            def __init__(self):self.stdout=io.BytesIO(frames(50)+frames(30,True)+frames(35));self.returncode=None
            def poll(self):return self.returncode
            def send_signal(self,signum):self.returncode=0
            def wait(self,timeout=None):self.returncode=0;return 0
            def kill(self):self.returncode=-9
        with tempfile.TemporaryDirectory() as temp:
            calls=[]
            def factory(args,**kwargs):calls.append(args);return Process()
            capture=AutomaticMcp01Capture(lambda:False,process_factory=factory,lock_path=Path(temp)/'capture.lock')
            try:
                capture.start();capture._thread.join(3)
                self.assertFalse(capture._thread.is_alive())
                self.assertEqual(capture.snapshot()['state'],'READY')
                self.assertNotIn('--samples',calls[0])
                clip=capture.take();self.assertEqual(clip.pcm,frames(50)[40*640:]+frames(30,True)+frames(35))
                self.assertIsNone(capture._process)
            finally:capture.close()


if __name__=='__main__':unittest.main()
