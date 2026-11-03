"""Real socketpair + original automatic endpoint/8queue; fake model/microphone."""
import ast
import importlib
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]/'production_business_overlay/candidate/aura'
AFTER=HERE.parent/'after/aura'
sys.path.insert(0,str(BASE))
import board.runtime.audio as package
if str(AFTER/'board/runtime/audio') not in package.__path__:
    package.__path__.insert(0,str(AFTER/'board/runtime/audio'))
from board.runtime.audio.board_capture import BoardFrontendPool,BoardAutomaticCapture
wire=importlib.import_module('board.runtime.audio.board_frontend_process')
auto=importlib.import_module('board.runtime.audio.board_frontend_auto')


class Gate:
    def __init__(self):
        self.lock=threading.Lock();self.closed=False;self.error=''
        self.frames=self.samples=0;self.last_ms=None;self.max_ms=0.
        self.denoiser=SimpleNamespace(reset=lambda:None);self.vad=SimpleNamespace(reset=lambda:None)
    def __call__(self,frame):
        with self.lock:
            if self.closed:raise RuntimeError('closed fixture gate')
            self.frames+=1;self.samples+=320;self.last_ms=self.max_ms=.01
            return bool(np.max(np.abs(frame))>.05)
    def close(self):self.closed=True
    def public(self):
        return dict(enabled=True,frames=self.frames,processed_samples=self.samples,
                    last_roundtrip_ms=self.last_ms,max_roundtrip_ms=self.max_ms,closed=self.closed,error=self.error)


class Raw:
    def __init__(self,stop,quiet):self.stop,self.quiet,self.index=stop,quiet,0;self.closed=False
    def read(self,count):
        if self.stop.wait(.001) or self.closed:return b''
        self.index+=1
        loud=not self.quiet and 8<=self.index<23
        return (b'\x00\x20' if loud else b'\x00\x00')*320
    def close(self):self.closed=True


class Arecord:
    counter=0
    def __init__(self,quiet):
        Arecord.counter+=1;self.pid=10000+Arecord.counter
        self.stopped=threading.Event();self.stdout=Raw(self.stopped,quiet);self.returncode=None
    def poll(self):return self.returncode
    def send_signal(self,value):self.returncode=1;self.stopped.set()
    def kill(self):self.send_signal(signal.SIGTERM)
    def wait(self,timeout):
        if not self.stopped.wait(timeout):raise subprocess.TimeoutExpired('fixture arecord',timeout)
        return self.returncode


class Process:
    def __init__(self,stream,target):
        self.pid=os.getpid();self.stream=stream;self.thread=threading.Thread(target=self.run,args=(target,),daemon=True)
        self.thread.start()
    def run(self,target):
        try:target(self.stream)
        finally:self.stream.close()
    def poll(self):return None if self.thread.is_alive() else 0
    def wait(self,timeout):
        self.thread.join(timeout)
        if self.thread.is_alive():raise subprocess.TimeoutExpired('fixture worker',timeout)
        return 0
    def terminate(self):
        try:self.stream.shutdown(socket.SHUT_RDWR)
        except OSError:pass


def duplicate(handle):
    borrowed=socket.socket(fileno=handle)
    try:return borrowed.dup()
    finally:borrowed.detach()


class WorkerTests(unittest.TestCase):
    def make(self,quiet=False):
        self.arecords=[];self.gates=[];self.captures=[];self.mic_owners=0
        parent=self
        class FixtureCapture(BoardAutomaticCapture):
            def _acquire_owner(self):
                if parent.mic_owners:raise RuntimeError('fixture microphone already owned')
                parent.mic_owners+=1;self._owner=123
            def _release_owner(self):
                if self._owner is not None:parent.mic_owners-=1;self._owner=None
        def source(*args,**kwargs):
            process=Arecord(quiet);self.arecords.append(process);return process
        def capture(*args,**kwargs):
            value=FixtureCapture(*args,**kwargs,process_factory=source);self.captures.append(value);return value
        def gate():
            value=Gate();self.gates.append(value);return value
        def factory(argv,**kwargs):
            return Process(duplicate(kwargs['pass_fds'][0]),
                lambda stream:wire.serve(stream,gate,auto_capture_factory=capture))
        proxy=wire.BoardProcessSpeechGate('/public-fixture',process_factory=factory,startup_timeout=.5)
        self.addCleanup(proxy.shutdown)
        pool=BoardFrontendPool(proxy)
        return proxy,pool

    def remote(self,pool):
        return auto.RemoteAutomaticCapture(lambda:False,frontend_pool=pool,max_seconds=2,
            speech_start_ready=lambda cid:True,poll_interval=.02)

    def ready(self,capture):
        deadline=time.monotonic()+2.
        while time.monotonic()<deadline:
            snapshot=capture.snapshot()
            if snapshot['state']=='READY':return snapshot
            if snapshot['state']=='ERROR':self.fail(snapshot['error'])
            time.sleep(.005)
        self.fail('Synthetic automatic endpoint did not complete')

    def test_original_capture_endpoint_and_queue_to_once_pcm_over_local_ipc(self):
        proxy,pool=self.make()
        capture=self.remote(pool);self.addCleanup(capture.close)
        events=[];capture.on_speech_start=lambda:events.append(capture.capture_id)
        cid=capture.start();status=self.ready(capture)
        self.assertEqual(events,[cid])
        self.assertEqual(status['input_queue']['capacity_frames'],8)
        self.assertTrue(status['audio_frontend']['worker_capture_process'])
        self.assertEqual(self.mic_owners,0)
        self.assertTrue(all(p.poll() is not None for p in self.arecords))
        clip=capture.take()
        self.assertEqual(clip.capture_id,cid)
        self.assertGreater(len(clip.pcm),3200)
        self.assertLessEqual(len(clip.pcm),64000)
        self.assertEqual(capture.snapshot()['state'],'IDLE')
        with self.assertRaises(RuntimeError):capture.take()
        capture.close();pool.close()
        self.assertTrue(proxy.shutdown())
        self.assertEqual(len(self.gates),1)

    def test_auto_active_refuses_barge_then_cancel_releases_for_same_gate(self):
        proxy,pool=self.make(quiet=True)
        capture=self.remote(pool);self.addCleanup(capture.close)
        cid=capture.start();time.sleep(.03)
        generation=proxy._generation
        with self.assertRaises(wire.FrontendModeBusy):pool.acquire()
        self.assertEqual(proxy._generation,generation)
        self.assertFalse(proxy.error)
        capture.cancel()
        self.assertEqual(self.mic_owners,0)
        lease=pool.acquire()
        self.assertFalse(lease(np.zeros(320,np.float32)))
        lease.close()
        next_cid=capture.start()
        self.assertNotEqual(cid,next_cid)
        capture.cancel();capture.close();pool.close()
        self.assertEqual(len(self.gates),1)
        self.assertTrue(proxy.shutdown())

    def test_closing_retired_automatic_proxy_does_not_cancel_active_barge(self):
        proxy,pool=self.make()
        capture=self.remote(pool);self.addCleanup(capture.close)
        capture.start();self.ready(capture);capture.take()
        lease=pool.acquire()  # Child closes old idle automatic owner before barge.
        capture.close()       # Exact old owner tombstone; must not touch barge.
        self.assertTrue(lease(np.ones(320,np.float32)))
        lease.close();pool.close()
        self.assertTrue(proxy.shutdown())
        self.assertEqual(self.mic_owners,0)

    def test_socket_eof_closes_original_microphone_before_worker_exit(self):
        proxy,pool=self.make(quiet=True)
        capture=self.remote(pool)
        capture.start();time.sleep(.02)
        self.assertEqual(self.mic_owners,1)
        proxy._channel.stream.shutdown(socket.SHUT_RDWR)
        proxy.process.wait(timeout=2.)
        self.assertEqual(self.mic_owners,0)
        self.assertTrue(all(p.poll() is not None for p in self.arecords))
        with self.assertRaises(Exception):capture.close()
        self.assertTrue(proxy.shutdown())


class GuardTests(unittest.TestCase):
    def test_parent_death_guard_checks_before_and_after_arming_and_preserves_argv(self):
        events=[];command=['arecord','--quiet','--device','hw:CARD=MCP01,DEV=0']
        auto.exec_arecord_parent(123,command,getppid=lambda:123,
            arm=lambda:events.append('prctl'),execvp=lambda exe,args:events.append((exe,args)))
        self.assertEqual(events,['prctl',('arecord',command)])
        for sequence in ([124],[123,124]):
            values=iter(sequence);events=[]
            with self.assertRaises(RuntimeError):
                auto.exec_arecord_parent(123,command,getppid=lambda:next(values),
                    arm=lambda:events.append('prctl'),execvp=lambda *args:events.append('exec'))
            self.assertNotIn('exec',events)

    def test_arecord_factory_uses_exec_shim_without_preexec_or_argument_changes(self):
        command=['arecord','--quiet','--device','hw:CARD=MCP01,DEV=0','--rate','16000']
        with patch.object(auto.subprocess,'Popen',return_value='owned-child') as spawn:
            self.assertEqual(auto.owned_arecord_factory(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL),'owned-child')
        argv=spawn.call_args.args[0]
        self.assertEqual(argv[0],sys.executable)
        self.assertIn('--exec-arecord-parent',argv)
        self.assertEqual(argv[argv.index('--')+1:],command)
        self.assertNotIn('preexec_fn',spawn.call_args.kwargs)

    def test_only_take_reply_has_pcm_limit_and_source_is_python39(self):
        self.assertEqual(wire._payload_limit(auto.AUTO_TAKE|128),640000+4096+4)
        self.assertEqual(wire._payload_limit(wire.FRAME),1280)
        self.assertEqual(wire._payload_limit(auto.AUTO_POLL|128),4096)
        for path in AFTER.rglob('*.py'):ast.parse(path.read_text(encoding='utf-8'),feature_version=(3,9))


if __name__=='__main__':unittest.main()
