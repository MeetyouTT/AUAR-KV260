"""ASR boundary and cancellation tests; test engines are not speech evidence."""
import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from board.runtime.audio.transcription import DEFAULTS, TranscriptionJobs, TranscriptionStore, recognize
from common.asr_wire import context, encode_context, response
from tests.framework.test_board_recording import Controller, Capture
from tools.board_recording import RecordingController
from tools.asr_server import AsrServer

CONFIG=dict(DEFAULTS,enabled=True,timeout_ms=1000)


def result(meta,text='测试文字'):
    return {'context':dict(meta),'source_kind':'actual','text':text,
            'model_id':'UNIT_TEST_ONLY','recognition_ms':12}


def wait_for(callback):
    deadline=time.monotonic()+3
    while time.monotonic()<deadline:
        value=callback()
        if value:return value
        time.sleep(.005)
    raise AssertionError('Background operation did not complete')


class QueueTests(unittest.TestCase):
    def owner(self,transport,config=CONFIG):
        jobs=TranscriptionJobs(config,'test-boot',transport=transport)
        owner=RecordingController(Controller(),capture_factory=Capture,transcriber=jobs)
        self.addCleanup(owner.close)
        return owner,jobs

    def finished(self,owner):
        def ready():
            value=owner.public()['local_transcription']
            return value if value['state'] in ('READY','EMPTY','ERROR') else None
        return wait_for(ready)

    def test_stop_submits_once_and_displays_real_transport_result(self):
        calls=[]
        def transport(config,meta,pcm,timeout):
            calls.append((meta,pcm));return result(meta)
        owner,jobs=self.owner(transport)
        owner.record_start();owner.record_stop()
        self.assertEqual(self.finished(owner)['text'],'测试文字')
        for _ in range(10):owner.tick();owner.public()
        self.assertEqual(len(calls),1)
        context(calls[0][0],calls[0][1])
        self.assertNotIn('pcm',owner.public()['local_recording']['result'])

    def test_auto_completion_also_transcribes_without_another_stop(self):
        owner,jobs=self.owner(lambda c,m,p,t:result(m))
        owner.record_start();owner.capture.state='READY'
        self.assertEqual(self.finished(owner)['state'],'READY')

    def test_cancel_discards_inflight_result(self):
        entered,release=threading.Event(),threading.Event()
        def transport(c,m,p,t):
            entered.set();release.wait(2);return result(m,'旧录音')
        owner,jobs=self.owner(transport)
        self.addCleanup(release.set)
        owner.record_start();owner.record_stop()
        self.assertTrue(entered.wait(1));owner.cancel();release.set()
        wait_for(lambda:not jobs.public()['pending'])
        self.assertEqual(owner.public()['local_transcription']['state'],'CANCELLED')
        self.assertIsNone(jobs.poll())

    def test_re_recording_replaces_waiting_audio_without_old_text(self):
        entered,release=threading.Event(),threading.Event()
        calls=[]
        def transport(c,m,p,t):
            calls.append(m['capture_id'])
            if len(calls)==1:entered.set();release.wait(2)
            return result(m,m['capture_id'])
        owner,jobs=self.owner(transport)
        self.addCleanup(release.set)
        owner.record_start();owner.record_stop();self.assertTrue(entered.wait(1))
        owner.record_start();owner.record_stop()
        owner.record_start();owner.record_stop();release.set()
        self.assertEqual(self.finished(owner)['text'],'capture-3')
        self.assertEqual(calls,['capture-1','capture-3'])

    def test_disabled_keeps_audio_and_configuring_submits_existing_clip(self):
        owner,jobs=self.owner(lambda c,m,p,t:result(m),DEFAULTS)
        owner.record_start();owner.record_stop()
        state=owner.public()
        self.assertEqual(state['local_transcription']['state'],'DISABLED')
        self.assertEqual(state['local_recording']['result']['sample_count'],3200)
        owner.configure_transcription(CONFIG)
        self.assertEqual(self.finished(owner)['state'],'READY')

    def test_empty_text_is_not_a_network_failure(self):
        owner,jobs=self.owner(lambda c,m,p,t:result(m,' '))
        owner.record_start();owner.record_stop()
        self.assertEqual(self.finished(owner)['state'],'EMPTY')

    def test_wrong_request_or_fixture_results_are_errors(self):
        for mutate in (lambda r:r['context'].update(request_id='another'),
                       lambda r:r.update(source_kind='fixture')):
            def transport(c,m,p,t):
                value=result(m);mutate(value);return value
            owner,jobs=self.owner(transport)
            owner.record_start();owner.record_stop()
            value=self.finished(owner)
            self.assertEqual(value['state'],'ERROR');self.assertEqual(value['text'],'')

    def test_expired_response_is_not_published_as_text(self):
        clock=[0]
        def transport(c,m,p,t):clock[0]=2;return result(m)
        jobs=TranscriptionJobs(CONFIG,'test-boot',transport=transport,clock=lambda:clock[0])
        self.addCleanup(jobs.close)
        capture=Capture();capture.start();capture.stop();jobs.submit(capture.take())
        value=wait_for(jobs.poll)
        self.assertIn('expired',value['error']);self.assertEqual(value['text'],'')

    def test_unreachable_service_is_visible_and_can_record_again(self):
        def fail(*args):raise ConnectionRefusedError('service unavailable')
        owner,jobs=self.owner(fail)
        owner.record_start();owner.record_stop()
        self.assertIn('service unavailable',self.finished(owner)['error'])
        owner.record_start()
        self.assertEqual(owner.public()['local_transcription']['text'],'')


class BoundaryTests(unittest.TestCase):
    def test_configuration_is_persisted_and_invalid_changes_leave_previous(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'asr.json';store=TranscriptionStore(path)
            self.assertFalse(store.read()['enabled'])
            store.update({'host':'192.168.1.5','enabled':True})
            self.assertEqual(path.stat().st_mode&0o777,0o600)
            for values in ({'host':'not-an-ip'},{'host':123},{'port':True},{'timeout_ms':1}):
                with self.assertRaises(ValueError):store.update(values)
            self.assertEqual(store.read()['host'],'192.168.1.5')

    def test_all_recording_ownership_fields_are_checked(self):
        meta={'protocol':'aura-asr-1','board_boot_id':'boot','session_id':'session','request_id':'request',
              'generation':1,'capture_id':'capture','sample_count':3200,
              'pcm_sha256':hashlib.sha256(b'\x00'*6400).hexdigest(),'budget_ms':1000}
        for key in meta:
            value=result(meta);value['context'][key]='wrong'
            with self.assertRaises(ValueError):response(value,meta)
        with self.assertRaises(ValueError):context(meta,b'\x01'*6400)


class HttpTests(unittest.TestCase):
    def setUp(self):
        class TestEngine:
            model_id='UNIT_TEST_ONLY';probe_text='unit fixture'
            def transcribe(self,pcm):return '单元测试文本'
        self.server=AsrServer(('127.0.0.1',0),TestEngine())
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.02},daemon=True)
        self.thread.start()
        self.addCleanup(self.close)
        self.config=dict(CONFIG,port=self.server.server_port)
        self.pcm=b'\x01\x00'*3200
        self.meta={'protocol':'aura-asr-1','board_boot_id':'boot','session_id':'session','request_id':'request',
                   'generation':1,'capture_id':'capture','sample_count':3200,
                   'pcm_sha256':hashlib.sha256(self.pcm).hexdigest(),'budget_ms':1000}

    def close(self):
        self.server.shutdown();self.server.server_close();self.thread.join(1)

    def test_http_pcm_round_trip_and_busy_failure(self):
        self.assertEqual(recognize(self.config,self.meta,self.pcm,1)['text'],'单元测试文本')
        self.server.inference.acquire()
        try:
            with self.assertRaisesRegex(RuntimeError,'503'):recognize(self.config,self.meta,self.pcm,1)
        finally:self.server.inference.release()

    def test_corrupted_pcm_and_browser_origin_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'400'):recognize(self.config,self.meta,b'\x00'*6400,1)
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=1)
        try:
            conn.request('POST','/v1/asr/transcribe',body=self.pcm,
                         headers={'Origin':'http://example.invalid','Content-Type':'application/octet-stream',
                                  'X-Aura-Asr':encode_context(self.meta)})
            self.assertEqual(conn.getresponse().status,403)
        finally:conn.close()

    def test_total_client_deadline_does_not_block_audio_owner(self):
        release=threading.Event()
        self.addCleanup(release.set)
        def slow(pcm):release.wait(2);return 'too late'
        self.server.engine.transcribe=slow
        start=time.monotonic()
        with self.assertRaises(Exception):recognize(self.config,self.meta,self.pcm,.1)
        self.assertLess(time.monotonic()-start,.7)


if __name__=='__main__':unittest.main()
