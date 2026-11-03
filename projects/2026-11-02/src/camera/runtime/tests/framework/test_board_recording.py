"""Local recording and cached playback share the same controller command owner."""
import unittest
from types import SimpleNamespace
from board.runtime.audio.capture import CapturedAudio, FORMAT
from host.model_service.protocol import AudioRef
from tools.board_recording import RecordingController
from tools.board_avatar_gtk import BoardAvatarStage


class Controller:
    def __init__(self):
        self.last_error = ''
        self.state = {'phase':'IDLE','playing':False,'paused':False,
                      'audio_output_state':'NULL','pending_job':None}
        self.submitted = []

    def public(self):return dict(self.state)
    def tick(self):return None
    def submit(self,*args,**kwargs):
        self.submitted.append(args)
        self.state['phase'] = 'VOICE_PREPARING'
        return 'voice-job'
    def cancel(self):self.state.update(phase='IDLE',playing=False,paused=False,pending_job=None)
    def event(self,name):self.cancel()
    def toggle_pause(self):pass


class Capture:
    def __init__(self,*args,**kwargs):
        self.state = 'IDLE'
        self.error = ''
        self.closed = False
        self.counter = 0

    def start(self):
        self.counter += 1
        self.state = 'RECORDING'
        return 'capture-'+str(self.counter)

    def snapshot(self):
        return {'state':self.state,'sample_count':3200,'error':self.error}

    def stop(self):self.state = 'READY'
    def take(self):
        if self.state != 'READY':raise RuntimeError('No completed audio')
        self.state = 'IDLE'
        return CapturedAudio('capture-'+str(self.counter),AudioRef(self.counter,0,3200,FORMAT),b'\x01\x00'*3200,100,300)
    def cancel(self):self.state = 'CANCELLED'
    def close(self):self.closed = True


class RecordingTests(unittest.TestCase):
    def setUp(self):
        self.inner = Controller()
        self.owner = RecordingController(self.inner,capture_factory=Capture)
        self.addCleanup(self.owner.close)

    def test_recording_rejects_cached_playback_and_pause(self):
        self.owner.record_start()
        with self.assertRaisesRegex(ValueError,'停止录音'):self.owner.submit('cached')
        with self.assertRaises(ValueError):self.owner.toggle_pause()
        self.assertFalse(self.inner.submitted)

    def test_playback_preparation_and_unacknowledged_stop_reject_recording(self):
        for fields in ({'phase':'VOICE_PREPARING'},{'playing':True},{'paused':True},
                       {'audio_output_state':None},{'audio_output_state':'STARTING'},{'pending_job':'pending'}):
            previous = dict(self.inner.state)
            self.inner.state.update(fields)
            with self.assertRaises(ValueError):self.owner.record_start()
            self.assertIsNone(self.owner.capture)
            self.inner.state = previous

    def test_stop_returns_metadata_and_allows_cached_playback(self):
        self.owner.record_start()
        result = self.owner.record_stop()
        self.assertEqual(result['sample_count'],3200)
        self.assertEqual(self.owner.public()['local_recording']['state'],'READY')
        self.assertEqual(self.owner.submit('cached'),'voice-job')

    def test_natural_completion_collected_without_blocking_or_pcm_in_status(self):
        self.owner.record_start()
        self.owner.capture.state = 'READY'
        self.owner.tick()
        local = self.owner.public()['local_recording']
        self.assertEqual(local['state'],'READY')
        self.assertEqual(local['result']['pcm_bytes'],6400)
        self.assertNotIn('pcm',local['result'])
        self.assertFalse(local['can_stop'])

    def test_cancel_clears_old_result_and_rejects_stale_capture_id(self):
        self.owner.record_start()
        self.owner.record_stop()
        self.owner.cancel()
        with self.assertRaises(ValueError):self.owner.take_recording('capture-1')
        self.owner.record_start()
        self.owner.record_stop()
        with self.assertRaises(ValueError):self.owner.take_recording('capture-1')
        self.assertEqual(self.owner.take_recording('capture-2').capture_id,'capture-2')
        with self.assertRaises(ValueError):self.owner.take_recording('capture-2')

    def test_capture_failure_is_visible_and_not_publishable(self):
        self.owner.record_start()
        self.owner.capture.state,self.owner.capture.error = 'ERROR','Device unplugged'
        self.assertEqual(self.owner.public()['local_recording']['error'],'Device unplugged')
        with self.assertRaisesRegex(ValueError,'Device unplugged'):self.owner.record_stop()

    def test_shutdown_cancels_capture_and_closes_it(self):
        self.owner.record_start()
        capture = self.owner.capture
        self.owner.close()
        self.assertTrue(capture.closed)
        self.assertFalse(self.owner.public()['local_recording']['can_start'])


class RoutingTests(unittest.TestCase):
    def stage(self, *, remote=False, remote_recording=False, local_recording=False):
        stage = BoardAvatarStage.__new__(BoardAvatarStage)
        self.calls = []
        stage.controller = SimpleNamespace(
            public=lambda:{'phase':'IDLE','avatar_command_pending':0,
                           'local_recording':{'can_stop':local_recording,'state':'RECORDING' if local_recording else 'IDLE'}},
            record_start=lambda:self.calls.append('local-start') or 'local-start',
            record_stop=lambda:self.calls.append('local-stop') or 'local-stop')
        modules = {'audio':{'state':'RECORDING' if remote_recording else 'READY'}} if remote else {}
        stage.services = SimpleNamespace(read=lambda:{'snapshot':{'modules':modules,
            'capabilities':{'record_start':remote and not remote_recording,'record_stop':remote_recording}}},
            submit=lambda action,params:self.calls.append(action) or {'accepted':True})
        return stage

    def test_camera_only_service_uses_local_record_toggle(self):
        stage = self.stage()
        self.assertTrue(stage.command({'type':'record_toggle'})['queued'])
        self.assertEqual(self.calls,['local-start'])

    def test_remote_recording_stop_keeps_its_existing_owner(self):
        stage = self.stage(remote=True,remote_recording=True)
        self.assertTrue(stage.command({'type':'record_toggle'})['accepted'])
        self.assertEqual(self.calls,['record_stop'])

    def test_active_local_capture_blocks_remote_image_question(self):
        stage = self.stage(local_recording=True)
        with self.assertRaisesRegex(ValueError,'停止录音'):
            stage.command({'type':'service_action','action':'ask_frame'})
