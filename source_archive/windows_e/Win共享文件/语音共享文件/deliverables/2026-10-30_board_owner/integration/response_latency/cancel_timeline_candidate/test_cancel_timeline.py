"""Narrow control-frame acceptance and real rev3 fake-capture cancellation race."""
import importlib.util
import math
import os
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
R3=ROOT.parents[1]/'production_frontend_process_capture_candidate'
AURA=ROOT.parents[4]/'aura'
sys.path.insert(0,str(AURA))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module
fixture=load('cancel_r3_fixture',R3/'tests/test_worker_ipc.py')
baseline=load('board.runtime.audio.cancel_timeline_baseline',R3/'after/aura/board/runtime/audio/board_frontend_process.py')
fixed=load('board.runtime.audio.cancel_timeline_fixed',ROOT/'after/board/runtime/audio/board_frontend_process.py')

def result(module,*,frames=1,samples=640,number=0.,pid=None,nice=-10):
    return module.RESULT.pack(0,0,0,frames,samples,*([number]+[0.]*7),os.getpid() if pid is None else pid,nice)

def rpc_gate(module,kind,payload,*,wrong_sequence=False):
    gate=module.BoardProcessSpeechGate.__new__(module.BoardProcessSpeechGate)
    gate.clock=time.monotonic;gate.frame_timeout=.5;gate._generation=1;gate._sequence=0
    gate._io_lock=threading.Lock();gate._shutdown=False;gate._abandoned=set()
    gate.process=SimpleNamespace(pid=os.getpid(),poll=lambda:None)
    gate.error='';gate.closed=False;gate._rpc_last_ms=gate._rpc_max_ms=gate._rpc_total_ms=0.
    class Channel:
        def send(self,k,g,s,p,d):self.owner=(k,g,s)
        def receive(self,deadline,cancelled):
            k,g,s=self.owner
            return k|128,g,s+(1 if wrong_sequence else 0),payload
    gate._channel=Channel()
    return gate


class ControlTests(unittest.TestCase):
    def test_original_release_rejects_realistic_cancelled_frame_residue(self):
        body=result(baseline)
        with self.assertRaisesRegex(baseline.FrontendProcessError,'protocol_failed'):
            rpc_gate(baseline,6,body)._rpc(6)
    def test_closed_release_and_stop_accept_only_one_unpublished_frame(self):
        for kind in (6,fixed.STOP):
            for lag in (-320,-1,0,1024):
                with self.subTest(kind=kind,lag=lag):
                    frames=4;samples=frames*320-lag
                    self.assertFalse(rpc_gate(fixed,kind,result(fixed,frames=frames,samples=samples))._rpc(kind))
    def test_active_frame_and_reset_still_reject_any_negative_lag(self):
        for kind in (fixed.FRAME,fixed.RESET_DENOISER,fixed.RESET_VAD):
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(fixed.FrontendProcessError,'protocol_failed'):
                    rpc_gate(fixed,kind,result(fixed,frames=1,samples=321))._rpc(kind)
    def test_control_bounds_metrics_owner_priority_sequence_and_payload_are_still_strict(self):
        cases=[result(fixed,frames=1,samples=641),result(fixed,frames=4,samples=0),
               result(fixed,number=math.nan),result(fixed,number=math.inf),
               result(fixed,pid=os.getpid()+1),result(fixed,nice=0),b'bad']
        for body in cases:
            with self.subTest(body_len=len(body)):
                with self.assertRaises(fixed.FrontendProcessError):rpc_gate(fixed,6,body)._rpc(6)
        with self.assertRaisesRegex(fixed.FrontendProcessError,'owner_mismatch'):
            rpc_gate(fixed,6,result(fixed),wrong_sequence=True)._rpc(6)


class FullRaceTests(unittest.TestCase):
    def run_race(self,module,expect_success):
        class CancelledNativeFrame(fixture.Gate):
            def __init__(self):
                super().__init__();self.first=True;self.entered=threading.Event();self.release=threading.Event()
            def __call__(self,frame):
                if self.first:
                    self.first=False
                    with self.lock:
                        self.samples+=320  # Native state advances before completed-frame publication.
                        self.entered.set();self.release.wait(timeout=1.)
                        if self.closed:
                            self.error='InterruptedError'
                            raise InterruptedError('Synthetic native frame cancelled')
                        self.frames+=1
                        return False
                return super().__call__(frame)
        def paced(raw,count):
            if raw.stop.wait(.01) or raw.closed:return b''
            raw.index+=1
            return b'\0\0'*320
        case=fixture.WorkerTests('test_auto_active_refuses_barge_then_cancel_releases_for_same_gate')
        old_wire,old_auto_wire=fixture.wire,fixture.auto.wire
        fixture.wire=module;fixture.auto.wire=module
        proxy=pool=capture=None
        try:
            with patch.object(fixture,'Gate',CancelledNativeFrame),patch.object(fixture.Raw,'read',paced):
                proxy,pool=case.make(quiet=True);capture=case.remote(pool)
                first=capture.start();gate=case.gates[0]
                self.assertTrue(gate.entered.wait(.5))
                threading.Timer(.035,gate.release.set).start()
                capture.cancel()
                self.assertEqual(case.mic_owners,0)
                self.assertLess(gate.frames*320-gate.samples,0)
                worker=proxy.process
                if expect_success:
                    second=capture.start();self.assertNotEqual(first,second)
                    time.sleep(.05)
                    self.assertIs(proxy.process,worker);self.assertIsNone(worker.poll())
                    self.assertEqual(len(case.gates),1)
                    capture.cancel();capture.close();pool.close()
                    self.assertTrue(proxy.shutdown())
                    self.assertEqual(case.mic_owners,0)
                else:
                    with self.assertRaisesRegex(module.FrontendProcessError,'protocol_failed'):capture.start()
        finally:
            if capture is not None:
                try:capture.close()
                except Exception:pass
            if pool is not None:pool.close()
            case.doCleanups()
            fixture.wire,fixture.auto.wire=old_wire,old_auto_wire
    def test_old_helper_reproduces_cancel_then_resume_failure(self):self.run_race(baseline,False)
    def test_fixed_helper_reuses_worker_after_mid_native_frame_cancel(self):self.run_race(fixed,True)


if __name__=='__main__':unittest.main()
