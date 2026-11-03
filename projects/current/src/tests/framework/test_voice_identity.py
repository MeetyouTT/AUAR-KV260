"""Synthetic faces/ASR/TTS only; exercises real SQLite and local HTTP plumbing."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
import wave

from board.identity.live import IdentityService
from board.identity.store import IdentityStore
from board.identity.voice_enrollment import VoiceEnrollment
from board.vision.ui_camera_service import CameraState
from board.interaction.ui_contract import identity_completion, validate_snapshot
from board.runtime.audio.voice_channel import VoiceChannel
from board.runtime.audio.channel_jobs import ChannelConversationJobs
from common.voice_text import text_request
from tools.asr_server import AsrServer
from tools.board_model_host import ModelHandler
from tools.voice_channel_source import channel_frames
from common.voice_channel import ChannelState, read_frame
import io


PCM = b'\x01\x00'*3200


def owner():
    return {'protocol': 'aura-asr-1', 'board_boot_id': 'test-boot', 'session_id': 'test-session',
            'request_id': uuid.uuid4().hex, 'generation': 1, 'capture_id': 'test-capture',
            'sample_count': 3200, 'pcm_sha256': hashlib.sha256(PCM).hexdigest(), 'budget_ms': 5000}


class Face:
    def __init__(self, signature='one', vector=(1., 0., 0., 0.)):
        self.sample_signature, self.vector = signature, vector

    def extract(self, *_):
        return self.vector, ''


class Harness:
    def __init__(self, folder):
        self.now, self.fid, self.track_generation = 1000, 0, 1
        self.state = CameraState('test-boot', 'camera-service', clock=lambda: self.now)
        self.store = IdentityStore(Path(folder)/'private.sqlite3', 'fixture-model', 4, .85, .1,
                                   allow_cross_thread=True)
        self.service = IdentityService(self.store, Face, self.state.identity_target, lock=self.state.lock,
                                      clock=lambda: self.now, enrollment_target=self.state.identity_enrollment_target)
        self.service.ready = True
        self.state.identity = self.service
        self.commands, self.results = [], []
        self.pump = True
        self.frame()
        self.infer()

    def frame(self, *, people=1, generation=None):
        if generation is not None:self.track_generation = generation
        self.fid += 1
        self.state.captured(self.now)
        self.observation = {'target_id': 1, 'tracks': [
            {'track_id': i+1, 'generation': self.track_generation, 'box': (i*150, 0, 100, 200),
             'visible': True, 'confirmed': True} for i in range(people)]}
        self.state.observed(self.fid, self.now, self.observation, 1.)

    def infer(self, signature=None, vector=(1., 0., 0., 0.)):
        self.service.offer(None, self.fid, self.now, self.observation, self.state.camera_epoch)
        packet, self.service.pending = self.service.pending, None
        if packet:self.service.process(packet, Face(signature or 'crop-'+str(self.fid), vector))

    def submit(self, action, params):
        snapshot = self.state.snapshot()
        cid = uuid.uuid4().hex
        command = {'protocol_version': 'aura-ui-1', 'board_boot_id': 'test-boot',
            'service_epoch': 'camera-service', 'command_id': cid, 'ui_epoch': 'test-ui', 'ui_generation': 0,
            'context': snapshot['context'], 'snapshot_sequence': snapshot['sequence'],
            'issued_mono_ms': self.now, 'deadline_mono_ms': self.now+2500, 'action': action, 'params': params}
        self.commands.append(copy.deepcopy(command))
        ack = self.state.command(command)
        self.results.append(dict(ack, action=action))
        return {'ok': True, 'queued': True, 'command_id': cid}

    def read(self):
        return {'snapshot': self.state.snapshot(), 'results': copy.deepcopy(self.results)}

    def sleep(self, _):
        self.now += 500
        self.frame()
        if self.pump:self.infer()

    def params(self):
        return {'target': self.state.identity_target(), 'display_name': '测试访客', 'confirmed': True}

    def close(self):
        self.service.close()


class MultiSampleTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.h = Harness(self.folder.name)
        self.addCleanup(self.h.close)

    def begin(self):
        return self.h.submit('identity_collect', self.h.params())['command_id']

    def test_acceptance_is_not_commit_and_five_new_crops_commit_once(self):
        cid = self.begin()
        self.assertEqual(self.h.store.revision, 0)
        self.assertEqual(self.h.service.last_operation['state'], 'COLLECTING')
        self.assertEqual(identity_completion(self.h.results[-1], self.h.read()['snapshot']['modules']['identity']), '')
        for _ in range(4):self.h.sleep(.1)
        self.assertEqual(self.h.store.people(), [])
        self.h.sleep(.1)
        identity = self.h.read()['snapshot']['modules']['identity']
        self.assertEqual(identity_completion(self.h.results[-1], identity), '已登记“测试访客”')
        self.assertEqual(identity['last_operation']['command_id'], cid)
        self.assertEqual(self.h.store.revision, 1)
        self.h.sleep(.1)
        self.assertEqual(self.h.store.revision, 1)

    def test_repeated_frame_crop_and_too_close_samples_are_not_counted(self):
        self.begin()
        self.h.infer()
        self.assertEqual(len(self.h.service.enrollment['vectors']), 0)
        for _ in range(5):
            self.h.now += 500;self.h.frame();self.h.infer(signature='identical')
        self.assertEqual(len(self.h.service.enrollment['vectors']), 1)
        self.h.frame();self.h.infer()
        self.assertEqual(len(self.h.service.enrollment['vectors']), 2)
        self.h.now += 1;self.h.frame();self.h.infer()
        self.assertEqual(len(self.h.service.enrollment['vectors']), 2)

    def test_other_person_generation_camera_and_database_change_abort(self):
        for mutation in ('people', 'generation', 'camera', 'database'):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as folder:
                    h = Harness(folder)
                    try:
                        h.submit('identity_collect', h.params())
                        if mutation == 'people':h.frame(people=2)
                        elif mutation == 'generation':h.frame(generation=2)
                        elif mutation == 'camera':h.state.camera_epoch = 'other-camera'
                        else:h.store.enroll('existing', '其他人', (0, 1, 0, 0), consent=True)
                        h.read()
                        self.assertIsNone(h.service.enrollment)
                        self.assertEqual(h.service.last_operation['state'], 'FAILED')
                        self.assertNotIn('测试访客', [p['display_name'] for p in h.store.people()])
                    finally:h.close()

    def test_inconsistent_features_abort_before_persistence(self):
        self.begin();self.h.sleep(.1)
        self.h.now += 500;self.h.frame();self.h.infer(vector=(0, 1, 0, 0))
        self.assertEqual(self.h.service.last_operation['state'], 'FAILED')
        self.assertEqual(self.h.store.revision, 0)

    def test_cancel_drops_samples_and_late_samples_do_not_commit(self):
        cid = self.begin();self.h.sleep(.1)
        self.h.submit('identity_cancel', {'enrollment_id': cid})
        for _ in range(7):self.h.sleep(.1)
        self.assertEqual(self.h.service.last_operation['state'], 'CANCELLED')
        self.assertEqual(self.h.store.revision, 0)

    def test_cancel_before_delayed_start_prevents_start(self):
        cid = 'delayed-start'
        self.h.service.cancel_enrollment({'enrollment_id': cid})
        with self.assertRaises(ValueError):self.h.service.begin_enrollment(self.h.params(), cid)
        self.assertIsNone(self.h.service.enrollment)

    def test_old_cancel_cannot_cancel_new_enrollment(self):
        self.begin()
        self.h.service.cancel_enrollment({'enrollment_id': 'older'})
        self.assertIsNotNone(self.h.service.enrollment)

    def test_timeout_and_sqlite_failure_never_report_commit(self):
        self.begin()
        self.h.now += 15000;self.h.frame();self.h.read()
        self.assertEqual(self.h.service.last_operation['state'], 'FAILED')
        self.h.infer();self.begin()
        with patch.object(self.h.store, 'enroll', side_effect=sqlite3.OperationalError('fixture disk full')):
            for _ in range(5):self.h.sleep(.1)
        self.assertEqual(self.h.store.revision, 0)
        self.assertEqual(self.h.service.last_operation['state'], 'FAILED')

    def test_duplicate_command_is_idempotent_and_parallel_start_rejected(self):
        self.begin()
        command = self.h.commands[-1]
        self.assertTrue(self.h.state.command(command)['accepted'])
        self.h.submit('identity_collect', self.h.params())
        self.assertFalse(self.h.results[-1]['accepted'])
        self.assertEqual(self.h.store.revision, 0)

    def test_no_raw_photos_or_embedding_arrays_written(self):
        self.begin()
        for _ in range(5):self.h.sleep(.1)
        self.assertEqual([p.name for p in Path(self.folder.name).iterdir()], ['private.sqlite3'])
        validate_snapshot(self.h.state.snapshot(), 'test-boot', self.h.now)


class VoiceEnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.h = Harness(self.folder.name)
        self.addCleanup(self.h.close)
        self.voice = VoiceEnrollment(self.h, clock=lambda: self.h.now/1000, sleep=self.h.sleep)

    def ask(self):
        self.assertIn('怎么称呼', self.voice.handle('记住我是谁'))
        self.assertIn('确认登记', self.voice.handle('我叫小明'))

    def test_full_conversation_drives_camera_and_only_speaks_success_after_commit(self):
        self.ask()
        self.assertEqual(self.h.store.people(), [])
        reply = self.voice.handle('确认登记')
        self.assertIn('记住了，你是小明', reply)
        self.assertEqual(self.h.store.people()[0]['display_name'], '小明')
        self.assertEqual(self.voice.phase, 'IDLE')

    def test_name_in_initial_instruction_still_requires_confirmation(self):
        self.assertIn('确认登记', self.voice.handle('请记住我，我叫小明。'))
        self.assertEqual(self.voice.name, '小明')
        self.assertEqual(self.h.commands, [])

    def test_ordinary_names_mentions_negations_and_quotes_do_not_start(self):
        for text in ('我叫小明', '不要记住我', '他说记住我是谁', '怎么实现记住我是谁', '记住我是谁这个功能'):
            self.assertIsNone(self.voice.handle(text))
        self.assertEqual(self.voice.phase, 'IDLE')
        self.assertEqual(self.h.commands, [])

    def test_unrecognized_name_and_confirmation_do_not_write(self):
        self.voice.handle('记住我是谁')
        self.assertIn('请说', self.voice.handle('今天天气怎么样？'))
        self.voice.handle('我叫小明')
        self.assertIn('确认登记', self.voice.handle('我在问你问题'))
        self.assertEqual(self.h.commands, [])

    def test_can_correct_asr_name_before_confirmation(self):
        self.ask()
        self.assertIn('小林', self.voice.handle('我叫小林'))
        self.assertIn('小林', self.voice.handle('确认登记'))

    def test_negative_and_timeout_abandon_dialogue_without_writing(self):
        self.assertIn('没有正在进行', self.voice.handle('取消登记'))
        self.ask()
        self.assertIn('取消', self.voice.handle('不同意'))
        self.assertEqual(self.h.store.revision, 0)
        self.ask()
        self.h.now += 60001;self.h.frame();self.h.infer()
        self.assertIn('超时', self.voice.handle('确认登记'))
        self.assertEqual(self.h.store.revision, 0)

    def test_multiple_people_or_changed_track_abort(self):
        self.h.frame(people=2)
        self.assertIn('单独', self.voice.handle('记住我是谁'))
        self.h.frame();self.h.infer();self.ask()
        self.h.frame(generation=2);self.h.infer()
        self.assertIn('人物已经变化', self.voice.handle('确认登记'))
        self.assertEqual(self.h.store.revision, 0)

    def test_camera_service_unavailable_returns_factual_reply(self):
        self.h.service.ready = False
        self.assertIn('尚未就绪', self.voice.handle('记住我是谁'))

    def test_accepted_request_without_samples_never_speaks_success(self):
        self.ask();self.h.pump = False
        reply = self.voice.handle('确认登记')
        self.assertNotIn('记住了', reply)
        self.assertEqual(self.h.store.revision, 0)

    def test_write_failure_returns_failure_voice(self):
        self.ask()
        with patch.object(self.h.store, 'enroll', side_effect=sqlite3.OperationalError('fixture write failed')):
            reply = self.voice.handle('确认登记')
        self.assertIn('未保存', reply)
        self.assertNotIn('记住了', reply)

    def test_cancelled_recording_cannot_launch_a_new_enrollment(self):
        self.ask()
        with self.assertRaises(InterruptedError):self.voice.handle('确认登记', is_current=lambda: False)
        self.assertEqual(self.h.commands, [])

    def test_cancellation_during_collection_invalidates_late_work(self):
        self.ask()
        def stopped(_):
            self.h.sleep(.1)
            self.voice.reset()
        self.voice.sleep = stopped
        with self.assertRaises(InterruptedError):self.voice.handle('确认登记')
        self.assertEqual(self.h.store.revision, 0)
        self.assertEqual(self.h.service.last_operation['state'], 'CANCELLED')


class TextChannelTests(unittest.TestCase):
    @staticmethod
    def models(folder):
        class Voice:
            def generate(self, text):
                path = folder/'fixture.wav'
                with wave.open(str(path), 'wb') as out:
                    out.setparams((1, 2, 24000, 0, 'NONE', 'fixture'))
                    out.writeframes(b'\x01\x00'*2400)
                return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        class Models:
            histories = {}
        value = Models();value.voice = Voice();value.lock = threading.Lock()
        return value

    def test_invalid_text_context_and_unbounded_feedback_are_rejected(self):
        value = {'context': owner(), 'text': '确认登记', 'reply_text': '采样未完成。'}
        text_request(value)
        for bad in (dict(value, extra=True), dict(value, reply_text='a'*241),
                    dict(value, text='\x00'), dict(value, context={})):
            with self.assertRaises(ValueError):text_request(bad)

    def test_fixed_result_uses_tts_and_does_not_invoke_llm(self):
        with tempfile.TemporaryDirectory() as folder:
            meta = owner();models = self.models(Path(folder))
            def forbidden(*args, **kwargs):raise AssertionError('LLM must not invent an enrollment result')
            state = ChannelState(meta)
            for frame in channel_frames(models, meta, '确认登记', 5, model='unchanged-model', host='unused',
                                        stream_factory=forbidden, fixed_reply='登记未完成，请重试。'):
                state.accept(*read_frame(io.BytesIO(frame)))
            self.assertTrue(state.ended)
            self.assertEqual(state.text, '登记未完成，请重试。')
            self.assertEqual(state.samples, 2400)

    def test_real_http_text_endpoint_streams_feedback_without_asr_or_llm(self):
        with tempfile.TemporaryDirectory() as folder:
            class Engine:
                def transcribe(self, _):raise AssertionError('Second phase must not repeat ASR')
            server = AsrServer(('127.0.0.1', 0), Engine(), handler=ModelHandler)
            server.models = self.models(Path(folder))
            thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
            self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
            channel = VoiceChannel('127.0.0.1', server.server_port)
            self.addCleanup(channel.close)
            seen = []
            result = channel.exchange(owner(), PCM, lambda h,p: seen.append(h),
                text_request={'text': '确认登记', 'reply_text': '登记尚未完成。'})
            self.assertEqual(result['reply_text'], '登记尚未完成。')
            self.assertEqual(seen[0]['reply_source'], 'board_identity_result')

    def test_streaming_jobs_asr_voice_camera_sqlite_and_feedback_work_together(self):
        with tempfile.TemporaryDirectory() as folder:
            class Engine:
                model_id = 'SYNTHETIC_ASR_FIXTURE'
                def __init__(self):self.calls = 0
                def transcribe(self, _):
                    text = ['记住我是谁', '我叫小明', '确认登记', '今天天气怎么样'][self.calls]
                    self.calls += 1
                    return text
            engine = Engine()
            server = AsrServer(('127.0.0.1', 0), engine, handler=ModelHandler)
            server.models = self.models(Path(folder))
            thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
            self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
            h = Harness(folder);self.addCleanup(h.close)
            workflow = VoiceEnrollment(h, clock=lambda: h.now/1000, sleep=h.sleep)
            config = {'enabled': True, 'host': '127.0.0.1', 'port': server.server_port, 'timeout_ms': 5000}
            llm_calls = []
            class Stream:
                def __init__(self, *args, **kwargs):llm_calls.append(args[3])
                def __iter__(self):
                    yield 'text', '这是普通对话回复。'
                    yield 'complete', {'reply_text': '这是普通对话回复。', 'emotion': 'neutral', 'avatar_action': ''}
                def cancel(self):pass
            original = channel_frames
            def frames(*args, **kwargs):return original(*args, **kwargs, stream_factory=Stream)
            with patch('board.runtime.audio.channel_jobs.feedback_cache', return_value={'thinking': {'path': 'unused'}}), \
                 patch('tools.voice_channel_source.channel_frames', frames):
                jobs = ChannelConversationJobs(config, 'test-boot', Path(folder)/'cache', identity_workflow=workflow)
                self.addCleanup(jobs.close)
                replies = []
                for i in range(4):
                    meta = jobs.submit(SimpleNamespace(capture_id='capture-'+str(i), pcm=PCM,
                                                      audio=SimpleNamespace(sample_count=3200)))
                    end = time.monotonic()+5
                    complete = None
                    while time.monotonic() < end:
                        result = jobs.poll()
                        if result and result.get('error'):self.fail(result['error'])
                        if result and result.get('network_complete'):
                            self.assertEqual(result['context'], meta)
                            complete = result['network_complete'];break
                        time.sleep(.005)
                    self.assertIsNotNone(complete)
                    replies.append(complete['reply_text'])
                self.assertIn('怎么称呼', replies[0])
                self.assertIn('确认登记', replies[1])
                self.assertIn('记住了，你是小明', replies[2])
                self.assertEqual(replies[3], '这是普通对话回复。')
                self.assertEqual(h.store.people()[0]['display_name'], '小明')
                self.assertEqual(engine.calls, 4)  # Exactly one ASR per turn.
                self.assertEqual(llm_calls, ['今天天气怎么样'])

    def test_older_pc_host_reports_upgrade_needed_without_starting_enrollment(self):
        with tempfile.TemporaryDirectory() as folder:
            class Older(ModelHandler):
                def do_GET(self):self.send(200, {'ready': True})
            server = AsrServer(('127.0.0.1', 0), object(), handler=Older)
            thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
            self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
            h = Harness(folder);self.addCleanup(h.close)
            config = {'enabled': True, 'host': '127.0.0.1', 'port': server.server_port, 'timeout_ms': 5000}
            jobs = ChannelConversationJobs(config, 'test-boot', Path(folder)/'cache',
                                           identity_workflow=VoiceEnrollment(h))
            self.addCleanup(jobs.close)
            deadline = time.monotonic()+2
            while not jobs.public()['feedback_error'] and time.monotonic() < deadline:time.sleep(.01)
            self.assertIn('needs the voice-identity', jobs.public()['feedback_error'])
            self.assertEqual(h.commands, [])


if __name__ == '__main__':
    unittest.main()
