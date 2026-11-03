"""Fixture protocol/cancellation checks; not evidence of actual speech or models."""
import hashlib
import io
import math
from pathlib import Path
import tempfile
import threading
import struct
import time
import unittest
from unittest.mock import patch
import wave
from common.voice_wire import PROTOCOL,REVISION,voice_reply,wav_payload
from board.runtime.audio.conversation import ConversationJobs
from board.runtime.audio.transcription import TranscriptionJobs
from tools.asr_server import AsrServer
from tools.board_model_host import ModelHandler
from tools.board_recording import RecordingController
from tools.selected_voice_service import SpeechJobs
from tests.framework.test_transcription import CONFIG,wait_for,result
from tests.framework.test_board_recording import Capture,Controller

def voice():
    stream=io.BytesIO()
    with wave.open(stream,'wb') as audio:
        audio.setparams((1,2,24000,0,'NONE','not compressed'))
        audio.writeframes(b''.join(struct.pack('<h',int(12000*math.sin(2*math.pi*220*i/24000))) for i in range(2400)))
    raw=stream.getvalue()
    meta={'protocol':PROTOCOL,'revision':REVISION,'engine':'omnivoice','num_step':16,'source_kind':'actual',
          'reply_text':'嗯，我记住了！','emotion':'friendly','sha256':hashlib.sha256(raw).hexdigest(),
          'bytes':len(raw),'duration_seconds':.1}
    return meta,raw

class ConversationTests(unittest.TestCase):
    def test_cached_worker_supports_older_board_synth_without_normalizer(self):
        from tools.selected_voice_service import VoiceWorker
        class LegacySynth:
            def __init__(self,*args,**kwargs):pass
        with tempfile.TemporaryDirectory() as directory, patch('tools.selected_voice_service.SelectedVoiceSynthesizer',LegacySynth):
            worker=VoiceWorker(directory,cached_only=True)
            self.assertEqual(worker.normalize_text('  你好  '),'你好')
            worker.warmup();self.assertTrue(worker.ready)

    def test_metadata_steps_hash_and_format_are_enforced(self):
        meta,raw=voice();wav_payload(meta,raw)
        with self.assertRaises(ValueError):voice_reply(dict(meta,num_step=32))
        with self.assertRaises(ValueError):voice_reply(dict(meta,source_kind='fixture'))
        with self.assertRaises(ValueError):wav_payload(meta,raw[:-2]+b'aa')

    def test_cancelled_recording_never_imports_its_voice(self):
        entered,release=threading.Event(),threading.Event()
        self.addCleanup(release.set)
        def transport(config,meta,pcm,timeout):
            entered.set();release.wait(2)
            return dict(result(meta),voice_reply=voice()[0])
        jobs=TranscriptionJobs(CONFIG,'test-boot',transport=transport,include_voice=True)
        self.addCleanup(jobs.close)
        controller=Controller();controller.submit_generated=lambda *a,**kw:controller.submitted.append(a)
        owner=RecordingController(controller,capture_factory=Capture,transcriber=jobs)
        owner.record_start();owner.record_stop();self.assertTrue(entered.wait(1))
        owner.cancel();release.set();time.sleep(.05);owner.tick()
        self.assertEqual(controller.submitted,[])
        self.assertEqual(owner.public()['local_transcription']['state'],'CANCELLED')

    def test_asr_only_transport_does_not_import_voice_extensions(self):
        jobs=TranscriptionJobs(CONFIG,'test-boot',transport=lambda c,m,p,t:dict(result(m),voice_reply=voice()[0]))
        self.addCleanup(jobs.close)
        capture=Capture();capture.start();capture.stop();jobs.submit(capture.take())
        self.assertNotIn('voice_reply',wait_for(jobs.poll))

    def test_full_http_roundtrip_downloads_and_imports_validated_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);meta,raw=voice()
            class Engine:
                model_id='TEST_ONLY';probe_text='test'
                def transcribe(self,pcm):return '测试问句'
            class Models:
                lock=threading.Lock()
                def __init__(self):
                    self.root=root/'host';(self.root/'audio').mkdir(parents=True)
                    (self.root/'audio'/(meta['sha256']+'.wav')).write_bytes(raw)
                def answer(self,owner,text):return meta
            server=AsrServer(('127.0.0.1',0),Engine(),handler=ModelHandler);server.models=Models()
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            jobs=ConversationJobs(dict(CONFIG,host='127.0.0.1',port=server.server_port), 'test-boot',root/'board/cache')
            try:
                capture=Capture();capture.start();capture.stop();jobs.submit(capture.take())
                answer=wait_for(jobs.poll)
                self.assertEqual(answer['text'],'测试问句');self.assertFalse(answer['error'])
                self.assertEqual(Path(answer['voice_reply']['path']).read_bytes(),raw)
                speech=SpeechJobs.__new__(SpeechJobs);speech.root=root/'board';speech.jobs={};speech.lock=threading.Lock()
                imported=speech.import_generated(answer['voice_reply'])
                self.assertEqual(imported['status'],'COMPLETE')
                self.assertEqual(imported['text'],meta['reply_text'])
                self.assertEqual(imported['result']['sha256'],meta['sha256'])
                bad=dict(answer['voice_reply'],path=str(root/'elsewhere.wav'))
                with self.assertRaises(ValueError):speech.import_generated(bad)
            finally:
                jobs.close();server.shutdown();server.server_close();thread.join(1)
