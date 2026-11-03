"""Independent real-proxy contracts; only transport/model/device data are fake."""
import copy
import dataclasses
import importlib.util
from pathlib import Path
import struct
import sys
import threading
import time
import unittest
from types import SimpleNamespace as NS

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]/'production_business_overlay/candidate/aura'
AFTER=HERE.parent/'after/aura'
sys.path.insert(0,str(BASE))
from board.runtime.audio.capture import CapturedAudio,FORMAT
from board.runtime.audio.automatic_capture import SpeechEndpoint
from board.runtime.audio.board_capture import BoardFrontendPool
from host.model_service.protocol import AudioRef
import board.runtime.audio as audio_package
if str(AFTER/'board/runtime/audio') not in audio_package.__path__:
    audio_package.__path__.insert(0,str(AFTER/'board/runtime/audio'))


def load_remote():
    path=AFTER/'board/runtime/audio/board_frontend_auto.py'
    spec=importlib.util.spec_from_file_location('board.runtime.audio.external_remote_capture_contract',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module


def original_endpoint_pcm():
    """Golden bytes from the unchanged endpoint, never a second implementation."""
    decisions=iter([False]*25+[True]*10+[False]*40)
    endpoint=SpeechEndpoint(20,frame_classifier=lambda frame:next(decisions),pre_roll_ms=500)
    original=bytearray();result=None
    for frame in range(75):
        samples=[((frame*320+i)%67-33)*400 for i in range(320)]
        raw=struct.pack('<320h',*samples);original.extend(raw)
        result=endpoint.feed(raw)
        if result is not None:break
    assert result is not None and endpoint.done
    assert result==bytes(original[-len(result):])
    return result


def clip(capture_id):
    pcm=original_endpoint_pcm()
    return CapturedAudio(capture_id,AudioRef(73,0,len(pcm)//2,FORMAT),pcm,100000,100000+len(pcm)//32)


class FakeTransport:
    def __init__(self):
        self.lock=threading.RLock();self.generation=0;self.polls=0;self.calls=[]
        self.status=None;self.result=None;self.inject=[];self.mic_released=True
    def _copy(self):return copy.deepcopy(self.status)
    def start(self,max_seconds):
        with self.lock:
            self.calls.append(('start',max_seconds));self.generation+=1
            self.mic_released=False;self.result=None
            self.status=dict(state='RECORDING',capture_id=f'{self.generation:032x}',generation=self.generation,
                speech_started=False,sample_count=0,speech_active=False,input_ready=True,listening_seconds=0.,
                has_result=False,error='',audio_frontend={},input_queue={})
            return self._copy()
    def poll(self,generation,capture_id):
        with self.lock:
            self.polls+=1
            if self.inject:return self.inject.pop(0)
            return self._copy()
    def finish(self):
        with self.lock:
            self.result=clip(self.status['capture_id'])
            # The real worker must likewise use original Mcp READY, after its
            # finally closed arecord and released the sole microphone owner.
            self.mic_released=True
            self.status.update(state='READY',speech_started=True,sample_count=self.result.audio.sample_count,
                               speech_active=False,listening_seconds=2.,has_result=True)
            return self._copy()
    def take(self,generation,capture_id):
        with self.lock:
            assert (generation,capture_id)==(self.status['generation'],self.status['capture_id'])
            assert self.status['state']=='READY' and self.result is not None and self.mic_released
            result=self.result;self.result=None;self.status.update(state='IDLE',has_result=False)
            self.calls.append(('take',generation,capture_id))
            return self._copy(),result.metadata(),result.pcm
    def cancel(self,generation,capture_id):
        with self.lock:
            self.calls.append(('cancel',generation,capture_id));self.result=None;self.mic_released=True
            self.status.update(state='CANCELLED',has_result=False,speech_started=False,speech_active=False)
            return self._copy()
    def close(self,generation,capture_id):
        with self.lock:
            self.calls.append(('close',generation,capture_id));self.result=None;self.mic_released=True
            if self.status is None:
                self.status=dict(state='CLOSED',capture_id='0'*32,generation=0,speech_started=False,
                    sample_count=0,speech_active=False,input_ready=False,listening_seconds=0.,has_result=False,
                    error='',audio_frontend={},input_queue={})
            else:self.status.update(state='CLOSED',has_result=False,speech_started=False,speech_active=False)
            return self._copy()


def wait_for(predicate,seconds=.6):
    deadline=time.monotonic()+seconds
    while not predicate():
        if time.monotonic()>=deadline:raise AssertionError('bounded fake poll did not arrive')
        threading.Event().wait(.003)


class PublicGate:
    def __init__(self):
        self.lock=threading.Lock();self.closed=False;self.error='';self.frames=self.samples=0
        self.last_ms=None;self.max_ms=0.;self.resets=[0,0]
        self.denoiser=NS(reset=lambda:self.reset(0));self.vad=NS(reset=lambda:self.reset(1))
    def reset(self,index):self.resets[index]+=1
    def __call__(self,frame):return False
    def close(self):self.closed=True
    def public(self):return dict(enabled=True,frames=self.frames,processed_samples=self.samples,closed=self.closed)


class PublicCapture:
    def __init__(self,playback_active,*,frontend_factory,max_seconds):
        self.frontend_factory=frontend_factory;self.max_seconds=max_seconds;self.starts=0
        self.state='IDLE';self.error='';self.result=None;self.lease=None
        self._owner=self._process=self._thread=None;self._closed=False
    def start(self):
        self.lease=self.frontend_factory();self.starts+=1
        self.capture_id=f'{self.starts:032x}';self.state='RECORDING'
        self._owner=object();self._process=object()
        return self.capture_id
    def finish(self):
        self.on_speech_start();self.result=clip(self.capture_id);self.state='READY'
    def release_mic(self):
        self._owner=self._process=self._thread=None
        if self.lease is not None:self.lease.close();self.lease=None
    def snapshot(self):
        return dict(state=self.state,error=self.error,has_result=self.result is not None,
            sample_count=self.result.audio.sample_count if self.result else 0,speech_active=False,
            input_ready=self.state in ('RECORDING','READY'),listening_seconds=2.,audio_frontend={},input_queue={})
    def take(self):
        if self.state!='READY' or self.result is None:raise RuntimeError('No public result')
        result,self.result=self.result,None;self.state='IDLE';return result
    def stop(self):self.finish();self.release_mic()
    def cancel(self):self.result=None;self.release_mic();self.state='CANCELLED'
    def close(self):self.cancel();self._closed=True;self.state='CLOSED'


class ExternalCaptureContracts(unittest.TestCase):
    def make(self,guard=None,playback=lambda:False):
        m=load_remote();transport=FakeTransport()
        proxy=m.RemoteAutomaticCapture(playback,transport=transport,max_seconds=20,
            speech_start_ready=guard,poll_interval=.02)
        self.addCleanup(proxy.close)
        return proxy,transport

    def test_original_endpoint_fixture_is_actual_raw_pcm(self):
        pcm=original_endpoint_pcm()
        self.assertGreaterEqual(len(pcm),6400)
        self.assertLessEqual(len(pcm),640000)
        self.assertEqual(len(pcm)%640,0)

    def test_onset_waits_for_cid_binding_and_precedes_ready_once_on_owner(self):
        bound={'cid':None};events=[];owner_thread=threading.get_ident()
        proxy,transport=self.make(lambda cid:bound['cid']==cid)
        proxy.on_speech_start=lambda:events.append(('onset',bound['cid'],threading.get_ident()))
        cid=proxy.start();transport.finish();wait_for(lambda:transport.polls>0)
        self.assertEqual(proxy.snapshot()['state'],'RECORDING')
        self.assertEqual(events,[])
        bound['cid']=cid
        status=proxy.snapshot();events.append(('observed',status['state']))
        self.assertEqual(status['state'],'READY')
        self.assertEqual(events[0],('onset',cid,owner_thread))
        self.assertEqual(events[1],('observed','READY'))
        for _ in range(3):proxy.snapshot()
        self.assertEqual(sum(e[0]=='onset' for e in events),1)

    def test_take_keeps_original_bytes_audio_ref_and_timestamps_exact(self):
        proxy,transport=self.make(lambda cid:True);calls=[]
        proxy.on_speech_start=lambda:calls.append('onset')
        cid=proxy.start();transport.finish();expected=transport.result
        wait_for(lambda:transport.polls>0)
        actual=proxy.take()
        self.assertIsInstance(actual,CapturedAudio)
        self.assertEqual(actual.pcm,expected.pcm)
        self.assertEqual(dataclasses.asdict(actual),dataclasses.asdict(expected))
        self.assertEqual(actual.metadata(),expected.metadata())
        self.assertEqual(calls,['onset'])
        self.assertEqual(proxy.snapshot()['state'],'IDLE')
        with self.assertRaises((RuntimeError,ValueError)):proxy.take()

    def test_cancelled_generation_late_ready_cannot_become_new_result(self):
        proxy,transport=self.make(lambda cid:False);onsets=[]
        proxy.on_speech_start=lambda:onsets.append(True)
        first=proxy.start();old=transport.finish();wait_for(lambda:transport.polls>0)
        proxy.cancel();second=proxy.start()
        self.assertNotEqual(first,second)
        with transport.lock:
            before=transport.polls;transport.inject.append(old)
        wait_for(lambda:transport.polls>before)
        status=proxy.snapshot()
        self.assertNotEqual(status['state'],'READY')
        self.assertEqual(onsets,[])
        self.assertFalse(status.get('has_result',False))
        with self.assertRaises((RuntimeError,ValueError)):proxy.take()

    def test_consumed_same_generation_ready_cannot_be_consumed_again(self):
        proxy,transport=self.make(lambda cid:True);calls=[]
        proxy.on_speech_start=lambda:calls.append(True)
        proxy.start();old=transport.finish();wait_for(lambda:transport.polls>0)
        proxy.take()
        with transport.lock:
            before=transport.polls;transport.inject.append(old)
        # A consumed proxy may stop its poller completely, also acceptable.
        threading.Event().wait(.035)
        self.assertNotEqual(proxy.snapshot()['state'],'READY')
        self.assertEqual(calls,[True])
        with self.assertRaises((RuntimeError,ValueError)):proxy.take()

    def test_close_retires_mic_and_refuses_new_start(self):
        proxy,transport=self.make(lambda cid:True)
        proxy.start();proxy.close();proxy.close()
        self.assertTrue(transport.mic_released)
        self.assertEqual(proxy.snapshot()['state'],'CLOSED')
        with self.assertRaises((RuntimeError,ValueError)):proxy.start()

    def test_invalid_complete_pcm_metadata_cannot_become_captured_audio(self):
        for field in ('capture_id','sample_count','pcm_sha256'):
            with self.subTest(field=field):
                proxy,transport=self.make(lambda cid:True)
                proxy.start();transport.finish();wait_for(lambda:transport.polls>0)
                original=transport.take
                def bad_take(generation,capture_id):
                    status,meta,pcm=original(generation,capture_id)
                    meta[field]=('f'*32 if field=='capture_id' else 1 if field=='sample_count' else '0'*64)
                    return status,meta,pcm
                transport.take=bad_take
                try:
                    with self.assertRaises((RuntimeError,ValueError)):proxy.take()
                finally:proxy.close()

    def test_playback_guard_blocks_before_child_microphone_start(self):
        proxy,transport=self.make(lambda cid:True,playback=lambda:True)
        with self.assertRaises((RuntimeError,ValueError)):proxy.start()
        self.assertEqual(transport.calls,[])

    def child(self):
        m=load_remote();gate=PublicGate();pool=BoardFrontendPool(gate);created=[]
        def factory(*args,**kwargs):
            capture=PublicCapture(*args,**kwargs);created.append(capture);return capture
        child=m.ChildAutomaticSession(pool,capture_factory=factory)
        self.addCleanup(pool.close);self.addCleanup(child.shutdown)
        return m,child,pool,gate,created

    def test_child_ready_waits_for_original_microphone_owner_release(self):
        m,child,pool,gate,created=self.child()
        child.start(1,20);capture=created[0];capture.finish()
        self.assertEqual(child.status()['state'],'RECORDING')
        self.assertFalse(child.status()['has_result'])
        with self.assertRaises(ValueError):child.take()
        capture.release_mic()
        self.assertEqual(child.status()['state'],'READY')
        status,meta,pcm=m.decode_take(child.take())
        self.assertEqual(status['state'],'IDLE')
        self.assertEqual(meta,clip(capture.capture_id).metadata())
        self.assertEqual(pcm,clip(capture.capture_id).pcm)

    def test_child_reuses_one_model_pool_and_refuses_auto_barge_overlap_before_capture(self):
        _,child,pool,gate,created=self.child()
        barge=pool.acquire()
        with self.assertRaisesRegex(ValueError,'mode_busy'):child.start(1,20)
        self.assertEqual(created,[])
        barge.close();child.start(1,20)
        self.assertEqual(len(created),1)
        self.assertIs(pool.gate,gate)
        with self.assertRaisesRegex(ValueError,'mode_busy'):child.retire_idle()
        with self.assertRaises(RuntimeError):pool.acquire()
        child.cancel();child.start(2,20)
        self.assertEqual(len(created),1)  # Same capture and same one model.
        self.assertIs(pool.gate,gate)
        child.cancel();child.retire_idle()
        barge=pool.acquire();self.assertIs(pool.gate,gate)
        barge.close()

    def test_child_old_speech_callback_after_cancel_cannot_mark_new_generation(self):
        _,child,pool,gate,created=self.child()
        child.start(1,20);old_onset=created[0].on_speech_start
        child.cancel();child.start(2,20)
        old_onset()
        self.assertFalse(child.status()['speech_started'])
        created[0].finish();created[0].release_mic()
        self.assertTrue(child.status()['speech_started'])

    def test_real_paired_voicefirst_binds_onset_before_submitting_original_clip(self):
        fixture_path=HERE.parents[1]/'listening_entry_fix/automatic_preference/test_production_listening.py'
        spec=importlib.util.spec_from_file_location('original_voicefirst_fakes_for_remote_contract',fixture_path)
        fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
        from tools.formal_yuki import paired_recording_type
        from tools.voice_first_recording import VoiceFirstRecordingController
        m=load_remote();transport=FakeTransport();reference={};clips=[];wake=[]
        pair=fixtures.Pair();pair.ready=True
        tx=fixtures.Transcriber()
        def submit(value):
            clips.append(value);tx.pending=True
            return dict(request_id='public-request')
        tx.submit=submit;tx.mark_wake_entry=lambda cid:wake.append(cid)
        def guard(cid):
            owner=reference['owner']
            return bool(owner.monitor_owned and owner.monitor_key and owner.listen_id==cid
                        and owner.capture is not None and owner.capture.capture_id==cid)
        def factory(*args,**kwargs):
            return m.RemoteAutomaticCapture(*args,transport=transport,speech_start_ready=guard,
                poll_interval=.02,**kwargs)
        kind=paired_recording_type(VoiceFirstRecordingController,pair)
        owner=kind(fixtures.Controller(),transcriber=tx,boot_id='public-boot',clock=lambda:10.,
            attention_provider=lambda:None,auto_capture_factory=factory,
            barge_capture_factory=lambda:None,barge_enabled=False,device_observer=False,visual_social=False)
        reference['owner']=owner;self.addCleanup(owner.close)
        owner.monitor_enabled=True  # Explicit synthetic test admission, no preference I/O.
        owner.tick()
        self.assertTrue(owner.monitor_owned)
        self.assertEqual(owner.listen_id,owner.capture.capture_id)
        transport.finish();expected=transport.result
        wait_for(lambda:transport.polls>0)
        owner.tick()
        self.assertEqual(owner.speech_proof,(expected.capture_id,owner.monitor_key))
        self.assertEqual(wake,[expected.capture_id])
        self.assertEqual(len(clips),1)
        self.assertEqual(dataclasses.asdict(clips[0]),dataclasses.asdict(expected))


if __name__=='__main__':unittest.main()
