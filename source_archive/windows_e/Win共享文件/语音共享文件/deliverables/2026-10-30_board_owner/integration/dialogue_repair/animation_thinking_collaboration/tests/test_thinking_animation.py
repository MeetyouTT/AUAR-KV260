"""Actual formal FSM/stream/mailbox, synthetic RAM samples, no GL or devices."""
import ctypes
import importlib.util
from pathlib import Path
from types import SimpleNamespace as S
import unittest
from unittest.mock import patch

from tools import native_yuki as native
from tools.formal_native_yuki import StrictLocalPortrait
from tools.formal_yuki import create_native_core, native_controller_type, paired_recording_type

HERE = Path(__file__).resolve().parents[1]


class Output:
    def __init__(self):
        self.active = self.paused = False
        self.duration = 0.
        self.last_time = 0.
        self.frames_queued = 0
        self.stop()

    def stop(self):
        self.active = self.paused = False
        self.snapshot = dict(ready=False, audible=False, clock=0., done=False,
                             error='', track=None, answer_clock=0., device_state='IDLE_READY')

    def read(self):
        return dict(self.snapshot)

    @property
    def ready(self):
        return self.snapshot['ready']

    def position(self):
        return self.snapshot['clock']

    def begin_stream(self):
        self.stop()
        self.active = True

    def append_pcm(self, pcm, start_sample):
        self.frames_queued += len(pcm)//2

    def end_stream(self):
        pass

    def pause(self, value):
        self.paused = value

    def finished(self):
        if self.active and self.snapshot['done']:
            self.active = False
            return True
        return False

    def sink(self, *, audible=False, track=None, ready=True, at=.06, done=False):
        self.snapshot.update(ready=ready, audible=audible, track=track, clock=at,
            answer_clock=at if track=='answer' else 0., done=done,
            answer_started_at=10. if track=='answer' and audible else None)


def controller():
    output = Output()
    core = create_native_core()
    control = native_controller_type()(core, S(), output, clock=lambda:10.)
    box = StrictLocalPortrait(output, clock=lambda:10.)
    box.ready = True
    box._drawn = True  # Simulated already-validated GL readiness; no widget.
    control.portrait_offload = box
    return control, core, output, box


class MailboxTests(unittest.TestCase):
    def setUp(self):
        self.control, self.core, self.output, self.box = controller()

    def offer(self, *, track='answer', sample=1440, gain=.9, level=.8, waiting=False):
        meta = self.box.offer(self.core, 1., gain, level, sample, track,
                              waiting_for_answer=waiting)
        return meta, self.box.consume()

    def assert_closed(self, value):
        self.assertEqual(value.expression & ~native.EXPRESSION_MASK, native.EYES_THINKING_CLOSED)
        self.assertEqual((value.playing, value.gain, value.level), (0, 0., 0.))

    def test_asr_wait_closes_with_inactive_output_and_idle_fsm(self):
        _, value = self.offer(waiting=True)
        self.assertEqual(self.core.fsm.state.label, 'IDLE')
        self.assert_closed(value)

    def test_active_without_first_audible_answer_is_closed(self):
        self.output.begin_stream()
        self.output.sink(ready=True)
        _, value = self.offer()
        self.assert_closed(value)
        self.assertEqual(value.track, 0)

    def test_ready_false_never_speaks_even_with_audible_flag(self):
        self.output.begin_stream()
        self.output.sink(audible=True, track='answer', ready=False)
        self.assert_closed(self.offer()[1])

    def test_actual_answer_opens_and_forwards_audio_envelope(self):
        self.output.begin_stream()
        self.output.sink(audible=True, track='answer')
        meta, value = self.offer(waiting=True)
        self.assertTrue(meta['answer_audible'])
        self.assertEqual(value.expression & ~native.EXPRESSION_MASK, native.EYES_ANSWER_OPEN)
        self.assertEqual(value.playing, 1)
        self.assertGreater(value.gain*value.level, 0.)
        self.assertEqual((value.audio_sample, value.sample_rate, value.track), (1440, 24000, 1))

    def test_feedback_is_not_an_answer(self):
        self.output.begin_stream()
        self.output.sink(audible=True, track='feedback')
        _, value = self.offer(track='feedback')
        self.assert_closed(value)
        self.assertEqual(value.track, 2)

    def test_ready_remains_true_during_pcm_gap_but_mouth_closes(self):
        self.output.begin_stream()
        self.output.sink(audible=True, track='answer')
        self.offer()
        self.output.sink(audible=False, track=None)
        self.assert_closed(self.offer()[1])

    def test_paused_sink_snapshot_cannot_keep_mouth_open(self):
        self.output.begin_stream()
        self.output.sink(audible=True, track='answer')
        self.output.paused = True
        _, value = self.offer()
        self.assert_closed(value)
        self.assertEqual(value.paused, 1)

    def test_error_or_done_closes_even_with_stale_audible_flag(self):
        for update in ({'done':True}, {'error':'synthetic_failure'}):
            with self.subTest(update=update):
                self.output.begin_stream()
                self.output.sink(audible=True, track='answer')
                self.output.snapshot.update(update)
                self.assert_closed(self.offer()[1])

    def test_snapshot_track_mismatch_never_opens(self):
        self.output.begin_stream()
        self.output.sink(audible=True, track='answer')
        self.assert_closed(self.offer(track='feedback')[1])

    def test_idle_and_listening_use_authored_eyes(self):
        for event in (None, 'listen'):
            with self.subTest(event=event):
                if event:self.control.event(event)
                _, value = self.offer(track='none')
                self.assertEqual(value.expression & ~native.EXPRESSION_MASK, native.EYES_AUTHORED)
                self.assertEqual(value.playing, 0)

    def test_expression_and_pose_are_preserved_under_eye_policy(self):
        self.box.set_pose(1)
        for name, index in self.box.FACE.items():
            with self.subTest(name=name):
                self.box.set_expression(name)
                _, value = self.offer(waiting=True)
                self.assertEqual(value.expression & native.EXPRESSION_MASK, index)
                self.assertEqual(value.pose, 1)
                self.assert_closed(value)

    def test_cancel_supersedes_pending_and_rejects_old_generation(self):
        self.output.begin_stream()
        self.output.sink(audible=True, track='answer')
        self.offer()
        old_generation = self.core.talk_gen
        self.control.cancel()
        reset = self.box.consume()
        self.assertEqual((reset.playing, reset.level), (0, 0.))
        self.core.talk_gen = old_generation
        meta, value = self.offer()
        self.assertTrue(meta['_portrait_wait'])
        self.assertIsNone(value)

    def test_latest_one_mailbox_stays_bounded(self):
        for sample in range(1000):
            self.box.offer(self.core, 1., 1., 1., sample, 'none', waiting_for_answer=True)
        self.assertEqual(self.box.consume().audio_sample, 999)
        self.assertIsNone(self.box.consume())
        self.assertEqual(self.box.dropped, 999)
        self.assertEqual(self.box.target_fps, 16)

    def test_invalid_numeric_inputs_are_rejected(self):
        for args in ({'sample':-1}, {'level':float('nan')}, {'waiting':1}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.offer(**args)


class StreamIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.control, self.core, self.output, self.box = controller()
        self.owner = dict(request_id='synthetic-test', capture_id='synthetic-capture')
        self.control.channel_event(dict(kind='start', thinking_mode='chat'), b'', self.owner, {}, 10.)

    def tick(self):
        meta = self.control.tick()
        return meta, self.box.consume()

    def answer(self):
        # Fixed public synthetic PCM, entirely in RAM. No microphone or model.
        pcm = b'\x10\x27' * 2400
        self.control.channel_event(dict(kind='audio', start_sample=0), pcm, self.owner, {}, 10.)

    def test_text_and_tts_completion_do_not_open_eyes(self):
        self.control.channel_event(dict(kind='text', text='公开测试回答'), b'', self.owner, {}, 10.)
        self.answer()
        self.control.channel_event(dict(kind='end'), b'', self.owner, {}, 10.)
        meta, value = self.tick()
        self.assertEqual(self.control.phase, 'THINKING')
        self.assertEqual(self.core.fsm.state.label, 'THINKING')
        self.assertEqual(value.expression & ~native.EXPRESSION_MASK, native.EYES_THINKING_CLOSED)
        self.assertFalse(meta['answer_audible'])

    def test_sink_start_gap_resume_and_completion_follow_actual_intervals(self):
        self.answer()
        self.output.sink(audible=True, track='answer')
        meta, speaking = self.tick()
        self.assertEqual(self.control.phase, 'SPEAKING')
        self.assertEqual(speaking.expression & ~native.EXPRESSION_MASK, native.EYES_ANSWER_OPEN)
        self.assertGreater(speaking.level, 0.)
        self.output.sink(audible=False, at=.07)
        _, gap = self.tick()
        self.assertEqual((gap.playing, gap.level), (0, 0.))
        self.assertEqual(gap.expression & ~native.EXPRESSION_MASK, native.EYES_THINKING_CLOSED)
        self.output.sink(audible=True, track='answer', at=.08)
        self.assertEqual(self.tick()[1].playing, 1)
        self.control.channel_complete(self.owner, dict(complete=True))
        self.output.sink(done=True, at=.10)
        meta, done = self.tick()
        self.assertEqual(self.control.phase, 'IDLE')
        self.assertEqual((done.playing, done.gain, done.level), (0, 0., 0.))
        self.assertEqual(done.expression & ~native.EXPRESSION_MASK, native.EYES_AUTHORED)
        self.assertIsNotNone(self.control.take_completion())

    def test_feedback_fsm_speaking_does_not_open_answer_mouth(self):
        self.output.sink(audible=True, track='feedback')
        _, value = self.tick()
        self.assertEqual(self.control.phase, 'THINKING_FEEDBACK')
        self.assertTrue(self.core.fsm.state.label.startswith('SPEAKING'))
        self.assertEqual((value.playing, value.level), (0, 0.))
        self.assertEqual(value.expression & ~native.EXPRESSION_MASK, native.EYES_THINKING_CLOSED)

    def test_pause_resume_and_cancel_leave_no_stale_mouth(self):
        self.answer()
        self.output.sink(audible=True, track='answer')
        self.tick()
        self.control.toggle_pause()
        _, paused = self.tick()
        self.assertEqual((paused.playing, paused.level), (0, 0.))
        self.control.toggle_pause()
        self.assertEqual(self.tick()[1].playing, 1)
        generation = self.core.talk_gen
        self.control.cancel()
        self.assertFalse(self.control.transcription_waiting)
        self.assertEqual(self.box.consume().playing, 0)
        self.answer()  # A delayed old channel callback is ignored after cancel.
        self.assertIsNone(self.control.stream)
        self.assertNotEqual(self.core.talk_gen, generation)
        self.assertEqual(self.tick()[1].playing, 0)

    def test_not_ready_native_has_no_png_fallback(self):
        reset = self.box.consume()  # Pending safe reset from begin_dialogue.
        self.assertEqual(reset.playing, 0)
        self.box.ready = False
        meta, value = self.tick()
        self.assertIsNone(value)
        self.assertIsNone(meta)
        self.assertEqual(self.box.target_fps, 16)


class RecordingWaitTests(unittest.TestCase):
    def setUp(self):
        self.control, self.core, self.output, self.box = controller()
        class ExistingRecording:
            def __init__(self, controller):
                self.controller = controller
                self.transcription = dict(state='DISABLED')
                self.next_state = None
                self.monitor_enabled = True
            def _queue_transcription(self):
                self.transcription.update(state='TRANSCRIBING', request_id='synthetic')
                return 'queued'
            def _poll_transcription(self):
                if self.next_state:self.transcription['state'] = self.next_state
        self.pair = S(require_ready=lambda:None)
        self.recording = paired_recording_type(ExistingRecording, self.pair)(self.control)

    def test_queue_closes_before_asr_and_does_not_change_fsm_or_generation(self):
        before = (self.core.fsm.state.label, self.core.talk_gen)
        self.assertEqual(self.recording._queue_transcription(), 'queued')
        self.assertTrue(self.control.transcription_waiting)
        self.assertEqual((self.core.fsm.state.label, self.core.talk_gen), before)
        self.control.tick()
        self.assertEqual(self.box.consume().expression & ~native.EXPRESSION_MASK, native.EYES_THINKING_CLOSED)

    def test_job_state_reset_and_error_release_wait(self):
        for state in ('TRANSCRIBING', 'GENERATING', 'PLAYING', 'ANSWERED', 'ERROR', 'CANCELLED', 'EMPTY'):
            with self.subTest(state=state):
                self.recording.next_state = state
                self.recording._poll_transcription()
                self.assertEqual(self.control.transcription_waiting, state in ('TRANSCRIBING','GENERATING','PLAYING'))

    def test_pause_preference_is_kept_and_no_capture_method_is_called(self):
        self.assertFalse(self.recording.monitor_enabled)
        self.assertEqual(self.recording.monitor_state, 'PAUSED')
        self.assertEqual(self.recording.monitor_reason, 'EXPLICIT_START_REQUIRED')


class BinaryContractTests(unittest.TestCase):
    def test_ctypes_struct_size_and_offsets_equal_v16(self):
        spec = importlib.util.spec_from_file_location('v16_native_before', HERE/'before/aura/tools/native_yuki.py')
        before = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(before)
        for name in ('Control', 'Stats'):
            with self.subTest(name=name):
                old, new = getattr(before,name), getattr(native,name)
                self.assertEqual(ctypes.sizeof(old), ctypes.sizeof(new))
                self.assertEqual([(key,getattr(old,key).offset) for key,_ in old._fields_],
                                 [(key,getattr(new,key).offset) for key,_ in new._fields_])

    def test_old_library_is_rejected_before_native_instance_creation(self):
        with patch.object(native.C, 'CDLL', return_value=S()), self.assertRaisesRegex(RuntimeError,'lacks dialogue'):
            native.Native('unused', 'unused', 'unused', 'unused')

    def test_library_without_feature_is_rejected_before_creation(self):
        class Function:
            def __call__(self):return 0
        with patch.object(native.C, 'CDLL', return_value=S(yuki_control_features=Function())), \
                self.assertRaisesRegex(RuntimeError,'incompatible'):
            native.Native('unused', 'unused', 'unused', 'unused')


if __name__ == '__main__':
    unittest.main()
