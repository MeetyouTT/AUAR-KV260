"""Bounded transport, owner isolation, cancellation, and untouched PCM."""
import socket
import threading
import time
import unittest
from unittest.mock import patch
import numpy as np
from common.frontend_wire import PROTOCOL,send,receive
from board.runtime.audio.remote_frontend import RemoteSpeechGate,health
from board.runtime.audio.automatic_capture import SpeechEndpoint
from tools.audio_frontend_host import FrontendServer


class FakePipeline:
    def __init__(self):self.seen=[];self.count=0;self.resets=0
    def reset(self):self.count=0;self.resets+=1
    def process(self,pcm):
        self.seen.append(pcm);self.count+=320
        return pcm[:2]!=b'\0\0',self.count


class RemoteFrontendTests(unittest.TestCase):
    def server(self,pipelines=None):
        values=pipelines or [FakePipeline(),FakePipeline()]
        server=FrontendServer(('127.0.0.1',0),values)
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        return {'enabled':True,'host':'127.0.0.1','port':server.server_address[1],'timeout_ms':150},values

    def test_actual_transport_keeps_pcm_and_server_resets_between_owners(self):
        config,pipelines=self.server()
        with self.subTest('health'):self.assertTrue(health(config)['ready'])
        gate=RemoteSpeechGate(config);self.addCleanup(gate.close)
        frame=np.arange(320,dtype=np.float32)/32768
        self.assertTrue(gate(frame+.001))
        expected=np.rint((frame+.001)*32768).astype('<i2').tobytes()
        self.assertEqual(pipelines[0].seen[0],expected)
        gate.close();second=RemoteSpeechGate(config);self.addCleanup(second.close)
        self.assertFalse(second(np.zeros(320,dtype=np.float32)))
        self.assertEqual(second.processed_samples,320)
        self.assertNotEqual(gate.stream_id,second.stream_id)

    def test_no_queue_when_both_pipelines_are_owned(self):
        config,_=self.server();gates=[RemoteSpeechGate(config) for _ in range(3)]
        for gate in gates:self.addCleanup(gate.close)
        for gate in gates[:2]:gate(np.zeros(320,dtype=np.float32))
        with self.assertRaises((ConnectionError,OSError,ValueError)):gates[2](np.zeros(320,dtype=np.float32))
        self.assertTrue(gates[2].closed)

    def test_speech_slice_includes_preroll_without_altering_raw_samples(self):
        config,_=self.server();gate=RemoteSpeechGate(config);self.addCleanup(gate.close)
        endpoint=SpeechEndpoint(frame_classifier=gate,pre_roll_ms=500)
        chunks=[];result=None
        for index in range(110):
            raw=(b'\xe8\x03'*320 if 35<=index<65 else b'\0\0'*320)
            chunks.append(raw);result=endpoint.feed(raw)
            if result is not None:break
        self.assertIsNotNone(result)
        self.assertEqual(result,b''.join(chunks)[-len(result):])
        self.assertLessEqual(endpoint.start_sample,35*320)

    def test_close_interrupts_pending_reply_and_rejects_late_result(self):
        config,_=self.server();gate=RemoteSpeechGate(config)
        entered=threading.Event();release=threading.Event();errors=[]
        original=receive
        def delayed(conn,timeout):
            result=original(conn,timeout)
            if result[0].get('kind')=='decision':entered.set();release.wait(1)
            return result
        def run():
            try:gate(np.zeros(320,dtype=np.float32))
            except Exception as exc:errors.append(type(exc).__name__)
        with patch('board.runtime.audio.remote_frontend.receive',delayed):
            thread=threading.Thread(target=run);thread.start()
            self.assertTrue(entered.wait(1));gate.close();release.set();thread.join(1)
        self.assertFalse(thread.is_alive());self.assertTrue(errors)

    def test_wrong_stream_reply_cannot_be_used_for_speech(self):
        config,_=self.server();gate=RemoteSpeechGate(config);self.addCleanup(gate.close)
        original=receive
        def wrong(conn,timeout):
            meta,pcm=original(conn,timeout)
            if meta.get('kind')=='decision':meta['stream_id']='0'*32
            return meta,pcm
        with patch('board.runtime.audio.remote_frontend.receive',wrong):
            with self.assertRaises(ValueError):gate(np.zeros(320,dtype=np.float32))

    def test_dropped_connection_is_not_energy_fallback(self):
        config,_=self.server();gate=RemoteSpeechGate(config);self.addCleanup(gate.close)
        original=receive
        def fail(conn,timeout):
            meta,pcm=original(conn,timeout)
            if meta.get('kind')=='decision':raise TimeoutError('injected')
            return meta,pcm
        with patch('board.runtime.audio.remote_frontend.receive',fail):
            with self.assertRaises(TimeoutError):gate(np.ones(320,dtype=np.float32)*.2)
        self.assertTrue(gate.closed);self.assertEqual(gate.public()['error'],'TimeoutError')

    def test_oversized_length_rejected_before_receiving_body(self):
        import struct
        a,b=socket.socketpair();self.addCleanup(a.close);self.addCleanup(b.close)
        a.sendall(struct.pack('!II',999999,0))
        with self.assertRaises(ValueError):receive(b,.1)

    def test_sequence_replay_closes_stream(self):
        config,_=self.server()
        with socket.create_connection((config['host'],config['port'])) as c:
            base={'protocol':PROTOCOL,'stream_id':'a'*32}
            send(c,dict(base,kind='open',sequence=0));receive(c,.2)
            send(c,dict(base,kind='frame',sequence=1),bytes(640));receive(c,.2)
            send(c,dict(base,kind='frame',sequence=1),bytes(640))
            with self.assertRaises(ConnectionError):receive(c,.2)


if __name__=='__main__':unittest.main()
