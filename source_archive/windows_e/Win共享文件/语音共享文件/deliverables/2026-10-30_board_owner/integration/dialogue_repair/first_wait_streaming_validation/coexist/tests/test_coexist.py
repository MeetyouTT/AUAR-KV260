"""Only synthetic PCM, real local socketpair, fake OnlineRecognizer; no models."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import struct
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('public_coexist_candidate', ROOT/'probe_coexist.py')
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
RAW = struct.pack('<h', 1000)*320


class TransportTests(unittest.TestCase):
    def setup_sink(self):
        parent, peer = socket.socketpair(); parent.settimeout(1.); peer.settimeout(1.)
        sink = probe.AsyncCtcSink(parent)
        self.addCleanup(peer.close); self.addCleanup(sink.close)
        return sink, peer
    def test_nonblocking_credit_includes_kernel_and_unsent_data(self):
        sink, peer = self.setup_sink()
        #Peer never reads/ACKs; no decoding or socket drain is needed by offer.
        for _ in range(50): sink.offer(RAW)
        self.assertEqual(sink.public()['peak_samples'], 16000)
        self.assertEqual(sink.public()['outstanding_samples'], 16000)
        with self.assertRaisesRegex(probe.Refused, 'ctc_backlog_overflow'): sink.offer(RAW)
        self.assertEqual(sink.public()['error'], 'ctc_backlog_overflow')
        with self.assertRaises(probe.Refused): sink.finish(timeout=.01)
    def test_wrong_packet_sizes_and_mutable_objects_are_refused(self):
        sink, _ = self.setup_sink()
        for bad in (b'', b'1', b'\0'*1280, bytearray(RAW)):
            with self.subTest(length=len(bad)), self.assertRaises(probe.Refused): sink.offer(bad)
        self.assertEqual(sink.public()['sent_samples'], 0)
    def test_final_requires_every_original_byte_and_ack_before_result(self):
        sink, peer = self.setup_sink(); seen = []
        def worker():
            for seq in (1,2):
                kind, sequence, raw = probe.receive(peer)
                seen.append(raw)
                self.assertEqual((kind, sequence), (probe.DATA, seq))
                probe.send(peer, probe.ACK, seq, struct.pack('!I', 320))
            kind, seq, raw = probe.receive(peer)
            self.assertEqual(kind, probe.END)
            self.assertEqual(json.loads(raw), dict(samples=640, sha256=hashlib.sha256(RAW*2).hexdigest()))
            probe.send(peer, probe.RESULT, seq, b'{"public_result_chars":4}')
        thread = threading.Thread(target=worker); thread.start()
        sink.offer(RAW); sink.offer(RAW)
        self.assertEqual(sink.finish(1.), {'public_result_chars':4})
        thread.join(1.); self.assertFalse(thread.is_alive())
        self.assertEqual(seen, [RAW,RAW]); self.assertEqual(sink.public()['outstanding_samples'], 0)
    def test_out_of_order_ack_cannot_release_credit_or_publish_result(self):
        sink, peer = self.setup_sink(); sink.offer(RAW)
        probe.send(peer, probe.ACK, 9, struct.pack('!I', 320))
        self.assertTrue(sink.done.wait(1.))
        self.assertEqual(sink.public()['error'], 'ctc_receive_failed')
        self.assertEqual(sink.public()['outstanding_samples'], 320)
    def test_premature_final_is_rejected(self):
        sink, peer = self.setup_sink(); sink.offer(RAW)
        probe.send(peer, probe.RESULT, 2, b'{"public_result_chars":5}')
        self.assertTrue(sink.done.wait(1.))
        self.assertIsNone(sink.result)
    def test_close_reaps_only_own_io_threads_without_fabricating_failure(self):
        sink, peer = self.setup_sink()
        self.assertTrue(sink.close())
        self.assertEqual(sink.public()['error'], '')
        self.assertTrue(sink.close())
        with self.assertRaises(probe.Refused): sink.offer(RAW)


class EndpointTests(unittest.TestCase):
    def test_raw_tap_preserves_classification_call_bytes_and_complete_result(self):
        called, offered = [], []
        result = object()
        endpoint = SimpleNamespace(feed=lambda raw:(called.append(raw),result)[1])
        probe.attach_raw_tap(endpoint, SimpleNamespace(offer=lambda raw:offered.append(raw)))
        self.assertIs(endpoint.feed(RAW), result)
        self.assertEqual(called,[RAW]); self.assertEqual(offered,[RAW])
    def test_asr_overflow_fails_whole_probe_instead_of_silently_dropping_raw(self):
        called = []
        endpoint = SimpleNamespace(feed=lambda raw:called.append(raw))
        def overflow(raw): raise probe.Refused('ctc_backlog_overflow')
        probe.attach_raw_tap(endpoint, SimpleNamespace(offer=overflow))
        with self.assertRaises(probe.Refused): endpoint.feed(RAW)
        self.assertEqual(called,[RAW])


class WorkerTests(unittest.TestCase):
    def test_real_worker_protocol_retains_raw_normalization_one_model_and_official_tail(self):
        import numpy as np
        calls, accepted = [], []
        class Recognizer:
            ready = False
            def create_stream(self):
                def accept(rate, samples):
                    accepted.append((rate, np.array(samples, copy=True))); self.ready = True
                return SimpleNamespace(accept_waveform=accept, input_finished=lambda:calls.append('finished'))
            def is_ready(self, stream): return self.ready
            def decode_stream(self, stream): self.ready=False; calls.append('decode')
            def get_result(self, stream): return '公开结果'
        def factory(**kwargs): calls.append(kwargs); return Recognizer()
        fake_sherpa = SimpleNamespace(__version__='1.13.8', OnlineRecognizer=SimpleNamespace(from_zipformer2_ctc=factory))
        parent, child = socket.socketpair(); parent.settimeout(1.)
        fd = child.detach(); code=[]
        resource = SimpleNamespace(RUSAGE_SELF=0, getrusage=lambda _:SimpleNamespace(ru_maxrss=1000))
        def pin(path): return probe.CTC_MODEL_SHA if path.name=='model.int8.onnx' else probe.CTC_TOKEN_SHA
        with patch.dict(sys.modules, {'sherpa_onnx':fake_sherpa,'resource':resource}), \
             patch.object(probe,'digest',side_effect=pin), \
             patch.object(probe.os,'getpriority',return_value=0,create=True), \
             patch.object(probe.os,'PRIO_PROCESS',0,create=True):
            worker=threading.Thread(target=lambda:code.append(probe.ctc_worker(fd,'/public/fake'))); worker.start()
            kind, seq, raw = probe.receive(parent); self.assertEqual((kind,seq),(probe.READY,0))
            sink=probe.AsyncCtcSink(parent)
            try:
                sink.offer(RAW); value=sink.finish(1.)
                self.assertEqual(value['real_samples'],320)
                self.assertEqual(value['tail_zero_samples'],10560)
                self.assertEqual(value['tail_wait_ms'],0)
                self.assertEqual(value['model_constructions'],1)
            finally: sink.close()
            worker.join(1.); self.assertEqual(code,[0])
        factory_calls=[v for v in calls if isinstance(v,dict)]
        self.assertEqual(len(factory_calls),1); self.assertEqual(factory_calls[0]['num_threads'],1)
        self.assertFalse(factory_calls[0]['enable_endpoint_detection'])
        self.assertTrue(np.array_equal(accepted[0][1],np.frombuffer(RAW,dtype='<i2').astype(np.float32)/32768))
        self.assertEqual(len(accepted[1][1]),10560); self.assertFalse(accepted[1][1].any())
        self.assertIn('finished',calls)
    def test_python39_ast(self):
        ast.parse((ROOT/'probe_coexist.py').read_bytes(), feature_version=(3,9))


if __name__ == '__main__': unittest.main()
