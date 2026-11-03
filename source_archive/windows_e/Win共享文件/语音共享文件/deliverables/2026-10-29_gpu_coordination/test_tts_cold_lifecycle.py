import bootstrap
import json,sys,threading,time
from pathlib import Path
from types import SimpleNamespace
import pytest
from common.gpu_coordination import GpuCoordinator,GpuPolicy,GpuBusy
from tools.selected_voice_service import VoiceWorker
from tools.voice_worker_transport import BoundedSpeechProcess
from test_gpu_coordination import Probe,policy

CHILD=r'''
import json,sys
for line in sys.stdin:
 request=json.loads(line)
 if request.get('text')=='exit':sys.exit(2)
 print('RESULT '+json.dumps({'ok':True,'request_id':request['request_id'],
  'result':{'echo':request.get('text','warmup'),'cache_hit':False,'cuda_idle_cache':{'available':True}}}),flush=True)
'''

class SpyCoordinator(GpuCoordinator):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.admissions=[]
    def acquire(self,kind,**kwargs):
        self.admissions.append(dict(kind=kind,**kwargs));return super().acquire(kind,**kwargs)

@pytest.fixture
def voice(tmp_path):
    worker=VoiceWorker.__new__(VoiceWorker);worker.cached_only=False;worker.ready=False;worker.error=''
    worker.python=Path(sys.executable);worker.engine='omnivoice';worker.cache=tmp_path
    worker.synth=SimpleNamespace(model_path=tmp_path/'unused-model',cached=lambda text:None)
    worker.cuda_idle_cache={};worker._gpu_start_state=threading.local();worker._gpu_warm_process=None
    worker.gpu_coordinator=SpyCoordinator(policy(),Probe())
    script=tmp_path/'fake_child.py';script.write_text(CHILD,encoding='utf-8')
    def command():
        # Check the actual pre-Popen cold guard, then return only this test
        # child command. Never execute the production/model script path.
        worker._worker_command()
        return [sys.executable,'-B','-u',str(script)]
    worker.transport=BoundedSpeechProcess(command,tmp_path/'fake_worker.log');worker.lock=worker.transport.lock
    yield worker
    worker.close()

def test_first_start_and_warmup_use_cold_then_same_live_worker_uses_steady(voice):
    voice.request({'text':'first'},timeout=2);first=voice.process
    assert voice.gpu_coordinator.admissions[-1]['cold'] is True
    voice.request({'text':'next'},timeout=2)
    assert voice.process is first and voice.gpu_coordinator.admissions[-1]['cold'] is False
    voice.warmup(timeout=2)
    assert voice.process is first and voice.gpu_coordinator.admissions[-1]['cold'] is True

def test_worker_failure_and_owned_retirement_require_cold_on_next_request(voice):
    voice.request({'text':'ok'},timeout=2);first=voice.process
    with pytest.raises(RuntimeError):voice.request({'text':'exit'},timeout=2)
    assert first.poll() is not None and voice.ready is False and voice._gpu_warm_process is None
    voice.request({'text':'recovery'},timeout=2)
    assert voice.process is not first and voice.gpu_coordinator.admissions[-1]['cold'] is True

def test_idle_worker_retired_between_requests_cannot_reuse_stale_steady_flag(voice):
    voice.request({'text':'ok'},timeout=2);first=voice.process
    voice.transport._retire(first,'test retirement')
    voice.request({'text':'new'},timeout=2)
    assert voice.gpu_coordinator.admissions[-1]['cold'] is True and voice.process is not first

def test_lifecycle_race_releases_steady_and_reacquires_cold_before_popen(voice):
    voice.request({'text':'ok'},timeout=2);first=voice.process;original=voice.gpu_coordinator.acquire
    once=[False]
    def acquire(kind,**kwargs):
        lease=original(kind,**kwargs)
        if not kwargs.get('cold') and not once[0]:
            once[0]=True;voice.transport._retire(first,'retired after steady admission')
        return lease
    voice.gpu_coordinator.acquire=acquire
    deadline=time.monotonic()+2
    voice.request({'text':'race recovery'},deadline=deadline,request_id='same-request')
    attempts=voice.gpu_coordinator.admissions[-2:]
    assert [r['cold'] for r in attempts]==[False,True] and voice.process is not first
    assert all(r['deadline']==deadline for r in attempts)
    assert attempts[0]['wait_deadline']==attempts[1]['wait_deadline']

def test_lifecycle_race_cannot_launch_new_model_when_only_steady_headroom_exists(voice):
    voice.request({'text':'ok'},timeout=2);first=voice.process;original=voice.gpu_coordinator.acquire
    voice.gpu_coordinator.policy=policy(max_wait_seconds=.03)
    def acquire(kind,**kwargs):
        lease=original(kind,**kwargs)
        if not kwargs.get('cold'):
            voice.transport._retire(first,'retired after steady admission');voice.gpu_coordinator.probe.free=800
        return lease
    voice.gpu_coordinator.acquire=acquire
    with pytest.raises(GpuBusy):voice.request({'text':'blocked cold'},timeout=1)
    assert voice.process is first and first.poll() is not None
    assert [r['cold'] for r in voice.gpu_coordinator.admissions[-2:]]==[False,True]

def test_cached_wav_works_without_gpu_admission_even_if_worker_absent(voice):
    cached={'cache_hit':True,'path':'public-cache.wav'};voice.synth.cached=lambda text:cached
    before=len(voice.gpu_coordinator.admissions)
    assert voice.generate_bounded('cached',deadline=time.monotonic()+1,cancelled=threading.Event(),request_id='cached') is cached
    assert len(voice.gpu_coordinator.admissions)==before and voice.process is None
    assert voice._cold_gpu_required({'text':'uncached'}) is True

def test_same_free_memory_admits_steady_but_rejects_cold_model_load():
    c=GpuCoordinator(policy(max_wait_seconds=.02),Probe(800))
    with c.acquire('tts',deadline=time.monotonic()+1,cold=False):pass
    with pytest.raises(GpuBusy):c.acquire('tts',deadline=time.monotonic()+1,cold=True)

def test_enforcement_requires_cold_tts_budget_not_below_steady():
    with pytest.raises(ValueError):policy(tts_cold_extra_mib=100)

def test_cold_peaks_and_warmup_are_not_mixed_into_steady_generation_peak():
    c=GpuCoordinator(GpuPolicy(),Probe())
    def result(peak,extra,initialize=False):
        return {'cache_hit':False,'cuda_inference':dict(measured=True,includes_cuda_initialization=initialize,
          baseline_allocated_bytes=0,baseline_reserved_bytes=0,peak_allocated_bytes=peak,peak_reserved_bytes=peak,
          allocated_extra_peak_bytes=extra,reserved_extra_peak_bytes=extra)}
    c.note_tts(result(5000,5000,True),warmup=True,cold=True)
    c.note_tts(result(5500,5500,True),cold=True)
    c.note_tts(result(2300,300),cold=False)
    stats=c.public()['tts_stats']
    assert stats['max_cold_reserved_peak_bytes']==5500 and stats['max_reserved_extra_peak_bytes']==300
    assert stats['warmup_inference']['peak_reserved_bytes']==5000 and stats['cold_start_inference']['peak_reserved_bytes']==5500
    assert stats['last_inference']['reserved_extra_peak_bytes']==300
