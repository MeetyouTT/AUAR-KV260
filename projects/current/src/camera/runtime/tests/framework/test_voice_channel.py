"""Transport/pipeline tests. Synthetic fixtures are not acoustic acceptance."""
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch
import wave

from common.voice_channel import ChannelWriter, ChannelState, encode_frame, read_frame, MAX_HEADER
from tools.dialogue_stream import ReplyDecoder
from tools.voice_channel_source import channel_frames, ClauseBuffer
from board.runtime.audio.voice_channel import VoiceChannel
from tools.asr_server import AsrServer
from tools.board_model_host import ModelHandler
from tools.dialogue_host_ollama import chat_body, fast_system_prompt


PCM = b'\x01\x00' * 3200


def owner(request='test-turn', generation=1):
    return {'protocol':'aura-asr-1','board_boot_id':'test-boot','session_id':'test-session',
            'request_id':request,'generation':generation,'capture_id':'test-capture',
            'sample_count':3200,'pcm_sha256':hashlib.sha256(PCM).hexdigest(),'budget_ms':5000}


def start(writer):
    return writer.frame('start', context=writer.state.owner, sample_rate=24000, channels=1, sample_width=2)


class VoiceChannelTests(unittest.TestCase):
    def test_json_stream_handles_every_character_boundary_and_unicode_escape(self):
        original = {'reply_text':'今天辛苦啦，我陪你聊聊。🐳', 'emotion':'friendly', 'avatar_action':''}
        raw = json.dumps(original, ensure_ascii=True)
        for width in (1, 2, 5, 17):
            decoder = ReplyDecoder()
            received = ''.join(decoder.feed(raw[i:i+width]) for i in range(0, len(raw), width))
            self.assertEqual(received, original['reply_text'])
            self.assertEqual(decoder.finish(), original)

    def test_incomplete_duplicate_or_control_character_reply_is_rejected(self):
        for text in ('{"reply_text":"你好', '{"reply_text":"a","reply_text":"b"}',
                     '{"reply_text":"你好\\n再见"}'):
            decoder = ReplyDecoder()
            with self.assertRaises(ValueError):
                decoder.feed(text)
                decoder.finish()

    def test_fast_body_keeps_existing_model_settings_and_history(self):
        history = [{'role':'user','content':'叫我小林'}]
        body = chat_body('same-27b', fast_system_prompt(), '我叫什么', history, fast=True)
        self.assertEqual(body['model'], 'same-27b')
        self.assertEqual(body['messages'][1], history[0])
        self.assertEqual(body['options'], {'temperature':0.6, 'num_predict':120, 'num_ctx':2048})
        self.assertFalse(body['stream'])
        self.assertFalse(body['think'])

    def test_clause_waits_for_meaningful_phrase_and_preserves_text(self):
        buffer = ClauseBuffer()
        self.assertEqual(buffer.feed('嗯，'), [])
        first = buffer.feed('今天辛苦啦，我陪你聊聊。还有')
        self.assertTrue(first)
        self.assertEqual(''.join(first + buffer.finish()), '嗯，今天辛苦啦，我陪你聊聊。还有')

    def test_frame_fragmentation_and_ownership_hash_sequence(self):
        writer = ChannelWriter(owner())
        first = start(writer)
        pcm = b'\x11\x00' * 480
        packet = writer.frame('audio', pcm, start_sample=0, sha256=hashlib.sha256(pcm).hexdigest())
        class Fragmented(io.BytesIO):
            def read(self, count=-1): return super().read(min(count, 3))
        state = ChannelState(owner())
        state.accept(*read_frame(Fragmented(first)))
        header, raw = read_frame(Fragmented(packet))
        for field, bad in [('generation',2), ('request_id','other'), ('seq',5), ('sha256','0'*64), ('start_sample',1)]:
            with self.assertRaises(ValueError): state.accept(dict(header, **{field:bad}), raw)
        state.accept(header, raw)
        with self.assertRaises(ValueError): state.accept(header, raw)

    def test_truncated_and_oversized_frame_rejected_before_allocation(self):
        with self.assertRaises(ValueError): read_frame(io.BytesIO(struct.pack('!II', MAX_HEADER+1, 0)))
        with self.assertRaises(EOFError): read_frame(io.BytesIO(start(ChannelWriter(owner()))[:-1]))

    def fixture_models(self, folder):
        class Models:
            histories = {}
            lock = threading.Lock()
        class Voice:
            def __init__(self): self.calls=[]
            def generate(self, text):
                self.calls.append(text)
                path = folder / ('voice%d.wav' % len(self.calls))
                with wave.open(str(path), 'wb') as audio:
                    audio.setparams((1,2,24000,0,'NONE','not compressed'))
                    audio.writeframes(b'\x01\x00' * 2400)
                return {'path':str(path), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        models = Models()
        models.voice = Voice()
        return models

    @staticmethod
    def fake_stream(*args):
        class Stream:
            def __iter__(self):
                yield 'text', '今天辛苦啦，我陪你聊聊。'
                yield 'complete', {'reply_text':'今天辛苦啦，我陪你聊聊。','emotion':'friendly','avatar_action':''}
            def cancel(self): pass
        return Stream()

    def test_audio_starts_before_full_llm_reply_and_text_is_not_lost(self):
        with tempfile.TemporaryDirectory() as directory:
            models = self.fixture_models(Path(directory))
            first_tts = threading.Event()
            completed = threading.Event()
            generate = models.voice.generate
            def tts(text):
                self.assertFalse(completed.is_set())
                first_tts.set()
                return generate(text)
            models.voice.generate = tts
            class Stream:
                def __iter__(self):
                    yield 'text', '今天辛苦啦，我陪你聊聊。'
                    if not first_tts.wait(2): raise RuntimeError('Pipeline did not start TTS')
                    completed.set()
                    yield 'complete', {'reply_text':'今天辛苦啦，我陪你聊聊。','emotion':'friendly','avatar_action':''}
                def cancel(self): pass
            packets = list(channel_frames(models, owner(), '测试', 4, model='fixture', host='fixture',
                                          stream_factory=lambda *a:Stream()))
            state = ChannelState(owner())
            kinds = []
            for packet in packets:
                header, pcm = read_frame(io.BytesIO(packet))
                state.accept(header, pcm)
                kinds.append(header['kind'])
            self.assertEqual(kinds[-1], 'end')
            self.assertGreater(state.samples, 0)
            self.assertEqual(state.text, '今天辛苦啦，我陪你聊聊。')
            self.assertEqual(models.histories, {})  # No fake claim of completed playback.

    def test_two_http_turns_reuse_connection_and_stale_callback_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            models = self.fixture_models(Path(directory))
            class Engine:
                model_id='TEST_ONLY'
                def transcribe(self, pcm): return '测试'
            class Server(AsrServer):
                accepted=0
                def get_request(self):
                    self.accepted += 1
                    return super().get_request()
            server=Server(('127.0.0.1',0),Engine(),handler=ModelHandler)
            server.models=models
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            original=channel_frames
            def source(*a,**kw): return original(*a,**kw,stream_factory=self.fake_stream)
            channel=VoiceChannel('127.0.0.1',server.server_port)
            with patch('tools.voice_channel_source.channel_frames',source):
                thread.start()
                try:
                    for index in range(2):
                        received=[]
                        result=channel.exchange(owner('turn%d'%index,index),PCM,lambda h,p:received.append((h,p)))
                        self.assertTrue(result['network_complete'])
                        self.assertFalse(result['playback_verified'])
                        self.assertTrue(any(p for h,p in received if h['kind']=='audio'))
                    self.assertEqual(server.accepted,1)
                    delivered=[]
                    def cancel_on_start(header, payload):
                        delivered.append(header['kind'])
                        channel.cancel()
                    with self.assertRaises((InterruptedError, OSError, EOFError)):
                        channel.exchange(owner('cancel',3),PCM,cancel_on_start)
                    self.assertEqual(delivered,['start'])
                    received=[]
                    with self.assertRaises(InterruptedError):
                        channel.exchange(owner('stale',4),PCM,lambda h,p:received.append(h),is_current=lambda:False)
                    self.assertEqual(received,[])
                finally:
                    channel.close();server.shutdown();server.server_close();thread.join(2)


if __name__=='__main__': unittest.main()
