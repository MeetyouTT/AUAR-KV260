import bootstrap
from concurrent.futures import ThreadPoolExecutor
import io,json,queue,socket,threading,time
from pathlib import Path
from types import SimpleNamespace
import pytest
from common.gpu_coordination import (DeferredLlmEvents,GpuBusy,GpuCoordinator,GpuPolicy,GpuProbeUnavailable,
 MemorySample,NvidiaMemoryProbe,OllamaResidencyProbe)
from tools import cuda_memory_stats
from tools.selected_voice_service import VoiceWorker
from tools.voice_channel_source import channel_frames
from common.voice_channel import ChannelState,read_frame
import tests.framework.test_voice_channel as fixtures

class Probe:
    def __init__(self,free=4096):self.free=free;self.calls=0;self.unavailable=False
    def read(self,**kwargs):
        self.calls+=1
        if self.unavailable:raise GpuProbeUnavailable('injected')
        return MemorySample('GPU-fixture',8192,self.free,8192-self.free,time.monotonic())
    def public(self):return {'available':not self.unavailable,'calls':self.calls}

def policy(**changes):
    return GpuPolicy(**dict(dict(mode='adaptive',gpu_uuid='GPU-fixture',calibration_id='synthetic-test-only',
        reserve_mib=128,llm_extra_mib=256,llm_cold_extra_mib=512,tts_extra_mib=512,tts_cold_extra_mib=1024,max_wait_seconds=.5),**changes))

@pytest.mark.parametrize('value',[dict(mode='adaptive'),dict(mode='serial'),dict(mode='adaptive',reserve_mib=512),
 {'max_pending':True},{'max_wait_seconds':float('inf')},{'sample_max_age_seconds':True},{'reserve_mib':True}])
def test_enforcement_requires_explicit_measured_policy(value):
    with pytest.raises(ValueError):GpuPolicy.from_dict(value)

def test_high_headroom_preserves_llm_tts_overlap():
    c=GpuCoordinator(policy(),Probe())
    with c.acquire('llm',deadline=time.monotonic()+1),c.acquire('tts',deadline=time.monotonic()+1):
        assert c.public()['active']=={'llm':1,'tts':1}
    assert c.public()['active']=={'llm':0,'tts':0}

def test_insufficient_overlap_headroom_waits_without_preempting_llm():
    c=GpuCoordinator(policy(),Probe(800));first=c.acquire('llm',deadline=time.monotonic()+1)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(c.acquire,'tts',deadline=time.monotonic()+1)
        time.sleep(.06);assert not pending.done() and c.public()['active']['llm']==1
        first.release();lease=pending.result(1);assert lease.wait_ms>=40;lease.release()

def test_waiting_cancel_does_not_release_another_lease():
    c=GpuCoordinator(policy(),Probe());held=c.acquire('tts',deadline=time.monotonic()+1);cancel=threading.Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(c.acquire,'tts',deadline=time.monotonic()+1,cancelled=cancel)
        time.sleep(.03);cancel.set()
        with pytest.raises(InterruptedError):pending.result(1)
    assert c.public()['active']['tts']==1 and c.public()['queued']==0;held.release()

def test_queue_is_bounded_and_preserves_existing_owner():
    c=GpuCoordinator(policy(max_pending=1),Probe());held=c.acquire('tts',deadline=time.monotonic()+1);cancel=threading.Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        waiting=pool.submit(c.acquire,'tts',deadline=time.monotonic()+1,cancelled=cancel)
        end=time.monotonic()+.5
        while c.public()['queued']!=1 and time.monotonic()<end:time.sleep(.001)
        with pytest.raises(GpuBusy,match='queue'):c.acquire('tts',deadline=time.monotonic()+1)
        assert c.public()['active']['tts']==1;cancel.set()
        with pytest.raises(InterruptedError):waiting.result(1)
    held.release()

def test_original_deadline_expires_without_admitting_or_extension():
    c=GpuCoordinator(policy(),Probe(50));began=time.monotonic()
    with pytest.raises(TimeoutError):c.acquire('llm',deadline=began+.04)
    assert time.monotonic()-began<.2 and c.public()['queued']==0 and not any(c.public()['active'].values())

@pytest.mark.parametrize('kind',['llm','tts'])
def test_unavailable_memory_fails_closed_when_enforcing(kind):
    probe=Probe();probe.unavailable=True;c=GpuCoordinator(policy(max_wait_seconds=.04),probe)
    with pytest.raises(GpuBusy):c.acquire(kind,deadline=time.monotonic()+1)
    assert not any(c.public()['active'].values())

def test_observe_mode_does_not_treat_unknown_memory_as_an_enforcement_gate():
    probe=Probe();probe.unavailable=True;c=GpuCoordinator(GpuPolicy(),probe)
    with c.acquire('llm',deadline=time.monotonic()+1):assert c.public()['mode']=='observe'
    assert not c.public()['enforcing']

def test_wrong_gpu_and_stale_snapshot_are_rejected():
    for sample in (MemorySample('GPU-other',8192,8192,0,time.monotonic()),
                   MemorySample('GPU-fixture',8192,8192,0,time.monotonic()-10)):
        probe=Probe();probe.read=lambda **kw:sample;c=GpuCoordinator(policy(max_wait_seconds=.02),probe)
        with pytest.raises(GpuBusy):c.acquire('llm',deadline=time.monotonic()+1)

def test_nvidia_probe_ttl_and_bad_refresh_do_not_reuse_old_valid_memory():
    now=[0.];calls=[]
    def run(args,**kw):
        calls.append((args,kw))
        return SimpleNamespace(returncode=0,stdout='GPU-fixture,8192,4096,2048' if len(calls)==1 else 'GPU-fixture,N/A,1,1')
    probe=NvidiaMemoryProbe(clock=lambda:now[0],run=run)
    assert probe.read().free_mib==4096;assert probe.read().free_mib==4096 and len(calls)==1
    now[0]=1
    with pytest.raises(GpuProbeUnavailable):probe.read()
    assert not probe.public()['available'] and len(calls)==2
    assert not any('load' in arg or 'kill' in arg for arg in calls[0][0])

def test_residency_distinguishes_inventory_readiness_cpu_residency_and_gpu_bytes():
    rows=[{'models':[]},{'models':[{'name':'configured','size_vram':0}]},
          {'models':[{'name':'configured','size_vram':123456}]}]
    now=[0.];probe=OllamaResidencyProbe('http://127.0.0.1:11435','configured',clock=lambda:now[0],fetch=lambda **kw:rows.pop(0))
    assert probe.status()['llm_resident'] is False
    now[0]=3;assert probe.status()['llm_resident'] is True and probe.status()['llm_gpu_resident'] is False
    now[0]=6;assert probe.status()['llm_gpu_bytes']==123456

def test_residency_unknown_is_not_reported_as_zero_bytes_or_unloaded():
    probe=OllamaResidencyProbe('http://127.0.0.1:11435','configured',fetch=lambda **kw:{'models':[{'name':'configured','size_vram':True}]})
    value=probe.status();assert value['available'] is False and value['llm_resident'] is None and value['llm_gpu_bytes'] is None

def test_cold_llm_uses_load_budget_and_changes_to_decode_when_confirmed_resident():
    state={'available':True,'llm_resident':False,'llm_gpu_bytes':0};residency=SimpleNamespace(status=lambda **kw:dict(state,fresh=True,sampled_mono=time.monotonic()))
    c=GpuCoordinator(policy(llm_cold_extra_mib=1024,max_wait_seconds=.02),Probe(800),llm_residency=residency)
    with pytest.raises(GpuBusy):c.acquire('llm',deadline=time.monotonic()+1)
    assert c.public()['llm_requirement']['kind']=='cold_or_unknown'
    state.update(llm_resident=True,llm_gpu_bytes=1000)
    with c.acquire('llm',deadline=time.monotonic()+1):
        assert c.public()['llm_requirement']['extra_mib']==256 and c.public()['llm_requirement']['kind']=='resident_decode'

def test_active_cold_load_does_not_keep_reserving_loaded_weights_during_tts():
    state={'available':True,'llm_resident':False,'llm_gpu_bytes':0};residency=SimpleNamespace(status=lambda **kw:dict(state,fresh=True,sampled_mono=time.monotonic()))
    p=Probe(2000);c=GpuCoordinator(policy(llm_cold_extra_mib=1024),p,llm_residency=residency)
    with c.acquire('llm',deadline=time.monotonic()+1):
        state.update(llm_resident=True,llm_gpu_bytes=1000);p.free=1000
        with c.acquire('tts',deadline=time.monotonic()+1):assert c.public()['active']=={'llm':1,'tts':1}

def test_residency_lock_cannot_extend_a_callers_original_deadline():
    probe=OllamaResidencyProbe('http://127.0.0.1:11435','configured',fetch=lambda **kw:pytest.fail('Lock was not owned'))
    probe.lock.acquire();began=time.monotonic()
    try:result=probe.status(deadline=began+.03,refresh=True)
    finally:probe.lock.release()
    assert time.monotonic()-began<.15 and result['available'] is False and result['llm_resident'] is None

def test_health_refresh_holding_lock_does_not_hold_admission_past_deadline():
    entered=threading.Event();release=threading.Event()
    def fetch(*,deadline):
        entered.set();release.wait(max(0,deadline-time.monotonic()));return {'models':[]}
    probe=OllamaResidencyProbe('http://127.0.0.1:11435','configured',fetch=fetch)
    thread=threading.Thread(target=probe.status,daemon=True);thread.start();assert entered.wait(.5)
    c=GpuCoordinator(policy(),Probe(),llm_residency=probe);began=time.monotonic()
    try:
        with pytest.raises(TimeoutError):c.acquire('llm',deadline=began+.03)
        assert time.monotonic()-began<.15 and c.active=={} and not c.pending
    finally:release.set();thread.join(.5)

@pytest.mark.parametrize('headers',[b'Content-Length: 1000\r\n',b'Connection: close\r\n'])
def test_trickled_residency_response_is_bounded_by_total_deadline(headers):
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(.5)
    stopped=threading.Event()
    def server():
        try:
            conn,_=listener.accept()
            with conn:
                conn.recv(4096);conn.sendall(b'HTTP/1.1 200 OK\r\n'+headers+b'\r\n')
                while not stopped.wait(.005):conn.sendall(b' ')
        except OSError:pass
    thread=threading.Thread(target=server,daemon=True);thread.start()
    probe=OllamaResidencyProbe('http://127.0.0.1:'+str(listener.getsockname()[1]),'configured')
    began=time.monotonic()
    try:
        result=probe.status(deadline=began+.04,refresh=True)
        assert not result['available'] and time.monotonic()-began<.18
    finally:stopped.set();listener.close();thread.join(.5)

def test_residency_lock_wait_and_fetch_share_one_absolute_deadline():
    seen=[]
    def fetch(*,deadline):seen.append(deadline);return {'models':[]}
    probe=OllamaResidencyProbe('http://127.0.0.1:11435','configured',fetch=fetch)
    probe.lock.acquire()
    release=threading.Timer(.025,probe.lock.release);release.start();deadline=time.monotonic()+.08
    result=probe.status(deadline=deadline,refresh=True);release.join(.2)
    assert result['available'] is True and seen==[deadline]

def test_llm_admission_bypasses_resident_ttl_after_natural_unload_or_daemon_restart():
    remote={'models':[{'name':'configured','size_vram':2000}]};calls=[]
    def fetch(**kwargs):calls.append(kwargs);return dict(remote)
    probe=OllamaResidencyProbe('http://127.0.0.1:11435','configured',fetch=fetch)
    assert probe.status()['llm_resident'] is True
    remote['models']=[]
    c=GpuCoordinator(policy(llm_cold_extra_mib=1024,max_wait_seconds=.02),Probe(800),llm_residency=probe)
    with pytest.raises(GpuBusy):c.acquire('llm',deadline=time.monotonic()+1)
    assert len(calls)>=2 and probe.status()['llm_resident'] is False and c.active=={}

def test_active_llm_requires_this_round_fresh_evidence_before_reducing_cold_budget():
    old=time.monotonic();state={'available':True,'llm_resident':False,'sampled_mono':old,'fresh':True}
    residency=SimpleNamespace(status=lambda **kw:dict(state));probe=Probe(2000)
    c=GpuCoordinator(policy(llm_cold_extra_mib=1024,max_wait_seconds=.02),probe,llm_residency=residency)
    with c.acquire('llm',deadline=time.monotonic()+1):
        state['llm_resident']=True;probe.free=1000
        with pytest.raises(GpuBusy):c.acquire('tts',deadline=time.monotonic()+1)
        state['sampled_mono']=time.monotonic()
        with c.acquire('tts',deadline=time.monotonic()+1):assert c.public()['active']=={'llm':1,'tts':1}

def test_new_probe_sequence_distinguishes_fresh_evidence_on_coarse_windows_clock():
    state={'available':True,'llm_resident':False,'sampled_mono':time.monotonic(),'fresh':True,'probe_calls':1}
    residency=SimpleNamespace(status=lambda **kw:dict(state));probe=Probe(2000)
    c=GpuCoordinator(policy(llm_cold_extra_mib=1024,max_wait_seconds=.03),probe,llm_residency=residency)
    with c.acquire('llm',deadline=time.monotonic()+1):
        admitted=next(iter(c.active.values()))['admitted_at']
        state.update(llm_resident=True,sampled_mono=admitted,probe_calls=2);probe.free=1000
        with c.acquire('tts',deadline=time.monotonic()+1):assert c.public()['active']=={'llm':1,'tts':1}

def test_deferred_events_preserve_exact_order_and_both_bounds():
    q=queue.Queue();rows=[('text','你'),('speech_ready',None),('complete',{'reply_text':'你好'}),('eof',None)]
    for row in rows:q.put(row)
    deferred=DeferredLlmEvents();deferred.drain(q)
    assert [deferred.get(q,0) for _ in rows]==rows and deferred.bytes==0
    for limits in ((1,1024),(100,1)):
        deferred=DeferredLlmEvents(*limits)
        with pytest.raises(ValueError):
            deferred.append(('text','hello'));deferred.append(('text','world'))

def test_cached_and_warmup_results_do_not_become_inference_peaks():
    c=GpuCoordinator(GpuPolicy(),Probe())
    peak={k:100 for k in ('baseline_allocated_bytes','baseline_reserved_bytes','peak_allocated_bytes','peak_reserved_bytes',
                         'allocated_extra_peak_bytes','reserved_extra_peak_bytes')};peak['measured']=True
    c.note_tts({'cache_hit':False,'cuda_inference':peak})
    bad=dict(peak,reserved_extra_peak_bytes=999999)
    c.note_tts({'cache_hit':True,'cuda_inference':bad});c.note_tts({'cuda_inference':bad},warmup=True)
    value=c.public();assert value['tts_stats']['max_reserved_extra_peak_bytes']==100
    assert value['tts_counts']=={'generated':1,'cache_hit':1,'warmup':1}

def test_cuda_measurement_does_not_synchronize_load_or_change_parameters():
    calls=[];cuda=SimpleNamespace(is_initialized=lambda:True,memory_allocated=lambda:100,memory_reserved=lambda:150,
      reset_peak_memory_stats=lambda:calls.append('reset'),max_memory_allocated=lambda:250,max_memory_reserved=lambda:300)
    torch=SimpleNamespace(cuda=cuda)
    before=cuda_memory_stats.begin(torch);result=cuda_memory_stats.finish(torch,before)
    assert calls==['reset'] and result['allocated_extra_peak_bytes']==150 and result['reserved_extra_peak_bytes']==150
    assert cuda_memory_stats.finish(torch,before,cache_hit=True)['measured'] is False

def test_voice_admission_failure_preserves_warm_worker_and_never_calls_transport():
    c=GpuCoordinator(policy(max_wait_seconds=.02),Probe(0));worker=VoiceWorker.__new__(VoiceWorker)
    worker.cached_only=False;worker.gpu_coordinator=c;worker.ready=True;worker.error=''
    worker.transport=SimpleNamespace(request=lambda *a,**kw:pytest.fail('Unsafe transport call'))
    with pytest.raises(GpuBusy):worker.request({'text':'public fixture'},timeout=.2)
    assert worker.ready is True and worker.error==''

def test_transport_receives_the_original_absolute_deadline_after_admission():
    seen={};worker=VoiceWorker.__new__(VoiceWorker);worker.cached_only=False;worker.ready=True;worker.error=''
    worker.gpu_coordinator=GpuCoordinator(policy(),Probe())
    def request(req,**kw):seen.update(kw);return {'cache_hit':False}
    worker.transport=SimpleNamespace(request=request);deadline=time.monotonic()+.5
    worker.request({'text':'public fixture'},deadline=deadline,request_id='fixed')
    assert seen['deadline']==deadline and seen['request_id']=='fixed' and worker.gpu_coordinator.public()['active']['tts']==0

@pytest.mark.parametrize('free,expect_overlap',[(4096,True),(800,False)])
def test_channel_preserves_pipeline_or_finishes_llm_without_queue_deadlock(tmp_path,free,expect_overlap):
    c=GpuCoordinator(policy(max_wait_seconds=1),Probe(free));completed=threading.Event();tts_started=threading.Event();observed=[]
    models=fixtures.VoiceChannelTests().fixture_models(tmp_path);base_generate=models.voice.generate
    def generate(text,**options):
        with c.acquire('tts',deadline=options['deadline'],cancelled=options['cancelled']):
            observed.append(not completed.is_set());tts_started.set();return base_generate(text)
    models.voice.generate_bounded=generate;models.gpu_coordinator=c
    first='这是一段公开的测试回答，第一句足够长。';tail='后续内容保持原顺序。'*15;text=first+tail
    class Stream:
        def __iter__(self):
            yield 'text',first
            if expect_overlap:assert tts_started.wait(1),'Pipeline was unnecessarily serialized'
            for char in tail:yield 'text',char
            completed.set();yield 'complete',{'reply_text':text,'emotion':'friendly','avatar_action':''}
        def cancel(self):pass
    packets=list(channel_frames(models,fixtures.owner(),'公开测试',3,model='fake',host='fake',stream_factory=lambda *a,**kw:Stream()))
    state=ChannelState(fixtures.owner());kinds=[]
    for packet in packets:
        header,pcm=read_frame(io.BytesIO(packet));state.accept(header,pcm);kinds.append(header['kind'])
    assert kinds[-1]=='end' and state.text==text and state.samples>0,header
    assert observed[0] is expect_overlap and not any(c.public()['active'].values())
