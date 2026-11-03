"""Decode metadata has no credit/authority; cold frontend cannot time out reader."""
import importlib.util
import json
from pathlib import Path
import socket
import struct
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('coexist_diagnostics_candidate',ROOT/'probe_coexist.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
RAW=b'\x01\x00'*320


class DiagnosticsTests(unittest.TestCase):
    def setup_sink(self):
        parent,peer=socket.socketpair();parent.settimeout(1.);peer.settimeout(1.)
        self.now=10.
        sink=probe.AsyncCtcSink(parent,clock=lambda:self.now)
        self.addCleanup(peer.close);self.addCleanup(sink.close)
        return sink,peer
    def wait(self,predicate):
        until=time.monotonic()+1.
        while time.monotonic()<until:
            if predicate():return
            time.sleep(.001)
        self.fail('diagnostic reader did not complete')
    def progress(self,peer,phase,*,index=1,**extra):
        body=dict(phase=phase,decode_index=index,accepted_samples=320,worker_mono=10.)
        if phase==2:body.update(wall_ms=430.,process_cpu_ms=310.)
        body.update(extra)
        probe.send(peer,probe.DECODE_PROGRESS,1,json.dumps(body).encode())
    def test_start_and_done_expose_completed_cpu_wall_without_returning_credit(self):
        sink,peer=self.setup_sink();sink.offer(RAW)
        self.progress(peer,1)
        self.wait(lambda:sink.public()['decode_diagnostics']['active_decode'])
        self.assertEqual(sink.public()['outstanding_samples'],320)
        self.now=10.9
        self.assertAlmostEqual(sink.public()['decode_diagnostics']['active_decode_phase_age_ms'],900.)
        self.progress(peer,2)
        self.wait(lambda:sink.public()['decode_diagnostics']['worker_decode_calls']==1)
        value=sink.public()
        self.assertEqual(value['outstanding_samples'],320)
        self.assertEqual(value['decode_diagnostics']['worker_decode_wall_total_ms'],430.)
        self.assertEqual(value['decode_diagnostics']['worker_decode_cpu_total_ms'],310.)
        self.assertFalse(value['decode_diagnostics']['active_decode'])
        probe.send(peer,probe.ACK,1,struct.pack('!I',320))
        self.wait(lambda:sink.public()['outstanding_samples']==0)
    def test_pending_age_reports_current_debt_even_without_any_ack(self):
        sink,_=self.setup_sink();sink.offer(RAW);self.now=11.25
        value=sink.public()
        self.assertEqual(value['oldest_ack_max_ms'],0.)
        self.assertEqual(value['decode_diagnostics']['oldest_pending_current_ms'],1250.)
    def test_overflow_snapshot_is_bounded_and_cannot_be_overwritten_by_late_progress(self):
        sink,peer=self.setup_sink()
        for _ in range(50):sink.offer(RAW)
        self.progress(peer,1);self.progress(peer,2)
        self.wait(lambda:sink.public()['decode_diagnostics']['worker_decode_calls']==1)
        self.now=11.
        with self.assertRaises(probe.Refused):sink.offer(RAW)
        frozen=sink.public()['at_failure']
        self.assertEqual(frozen['oldest_pending_current_ms'],1000.)
        self.assertEqual(frozen['worker_decode_calls'],1)
        self.assertEqual(frozen['pending_frames'],50)
        self.progress(peer,1,index=2);self.progress(peer,2,index=2)
        self.wait(lambda:sink.public()['decode_diagnostics']['worker_decode_calls']==2)
        self.assertEqual(sink.public()['at_failure'],frozen)
        self.assertEqual(sink.public()['outstanding_samples'],16000)
    def test_malformed_or_unpaired_progress_cannot_return_credit_or_leak_text(self):
        for extra in ({'exception_message':'SECRET_BODY'}, {'worker_mono':float('nan')},
                      {'accepted_samples':640}, {'decode_index':True}):
            with self.subTest(extra=extra):
                sink,peer=self.setup_sink();sink.offer(RAW)
                self.progress(peer,1,**extra)
                self.assertTrue(sink.done.wait(1.))
                value=sink.public()
                self.assertEqual(value['error'],'ctc_receive_failed')
                self.assertEqual(value['outstanding_samples'],320)
                self.assertNotIn('SECRET_BODY',json.dumps(value))
    def test_uninitialized_metadata_remains_numeric_and_nullable(self):
        sink,_=self.setup_sink();value=sink.public()['decode_diagnostics']
        self.assertFalse(value['decode_metadata_available'])
        self.assertEqual(value['worker_decode_calls'],0)
        self.assertEqual(value['oldest_pending_current_ms'],0.)
        self.assertIsNone(value['active_decode_sequence'])


class StartupTests(unittest.TestCase):
    def test_reader_starts_after_complete_gate_construction_and_warmup(self):
        events=[];gate=SimpleNamespace(close=lambda:events.append('gate_close'))
        def factory():events.append('gate_warmup_complete');return gate
        stream=SimpleNamespace(settimeout=lambda v:events.append(('timeout',v)))
        with patch.object(probe,'AsyncCtcSink',side_effect=lambda s:(events.append('reader_start'),object())[1]):
            selected,sink=probe.initialize_frontend_and_sink(stream,factory)
        self.assertIs(selected,gate)
        self.assertEqual(events,['gate_warmup_complete',('timeout',3.),'reader_start'])
    def test_gate_or_reader_start_failure_does_not_leave_unowned_frontend(self):
        events=[];gate=SimpleNamespace(close=lambda:events.append('gate_close'))
        stream=SimpleNamespace(settimeout=lambda v:None)
        with patch.object(probe,'AsyncCtcSink',side_effect=RuntimeError('public fixture')):
            with self.assertRaises(RuntimeError):probe.initialize_frontend_and_sink(stream,lambda:gate)
        self.assertEqual(events,['gate_close'])
        with patch.object(probe,'AsyncCtcSink') as reader:
            with self.assertRaises(ValueError):
                probe.initialize_frontend_and_sink(stream,lambda:(_ for _ in ()).throw(ValueError()))
            reader.assert_not_called()


if __name__=='__main__':unittest.main()
