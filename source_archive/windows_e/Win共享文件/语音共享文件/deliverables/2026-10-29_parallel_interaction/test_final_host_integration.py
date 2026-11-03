"""Parent wiring through real HTTP handlers, with synthetic devices/models."""
from contextlib import contextmanager, nullcontext
import hashlib,http.client,json,threading,time,wave
from types import SimpleNamespace
import pytest
from common.asr_wire import encode_context
from tools.asr_server import AsrServer
from tools.board_model_host import ModelHandler,ModelHost

@contextmanager
def server():
    models=SimpleNamespace(lock=threading.Lock(),meta_lock=threading.Lock())
    engine=SimpleNamespace(transcribe=lambda pcm:'记住我，我叫测试者')
    instance=AsrServer(('127.0.0.1',0),engine,handler=ModelHandler);instance.models=models
    worker=threading.Thread(target=instance.serve_forever,kwargs={'poll_interval':.01},daemon=True);worker.start()
    try:yield instance
    finally:instance.shutdown();instance.server_close();worker.join(timeout=1)

def test_handler_routes_binding_before_device_and_cancels_exchange_on_write_failure(monkeypatch):
    calls=[];exchange=SimpleNamespace(cancel=lambda:calls.append('cancel'))
    def prepare(models,meta,text,pcm,headers,**kw):
        assert text=='记住我，我叫测试者' and len(pcm)==6400 and 0<kw['timeout']<=60
        calls.append('binding');return None,exchange,{}
    def serve(handler,meta,text,timeout,**kw):
        assert kw['identity_exchange_override'] is exchange and kw['device_reply'] is None
        calls.append('channel');raise OSError('synthetic disconnected writer')
    monkeypatch.setattr('tools.binding_model_adapter.prepare_channel',prepare)
    monkeypatch.setattr('tools.device_client.command',lambda *a:pytest.fail('Legacy command bypassed typed decision'))
    monkeypatch.setattr('tools.voice_channel_source.serve_channel',serve)
    raw=bytes(6400);owner=dict(protocol='aura-asr-1',board_boot_id='synthetic',session_id='synthetic',request_id='synthetic',
        generation=1,capture_id='synthetic',sample_count=3200,pcm_sha256=hashlib.sha256(raw).hexdigest(),budget_ms=60000)
    with server() as instance:
        connection=http.client.HTTPConnection(*instance.server_address,timeout=2)
        connection.request('POST','/v1/voice/channel',raw,{'Content-Type':'application/octet-stream','X-Aura-Asr':encode_context(owner)})
        result=connection.getresponse();assert result.status==500;result.read();connection.close()
        assert not instance.models.lock.locked()
    assert calls==['binding','channel','cancel']

@pytest.mark.parametrize('origin', [None,'https://foreign.example'])
def test_gallery_handler_passes_only_bounded_non_origin_json(monkeypatch,origin):
    seen=[]
    def accept(models,value):seen.append(value);return {'accepted':True,'packet_sha256':'a'*64}
    monkeypatch.setattr('tools.binding_model_adapter.accept_model_gallery',accept)
    body={'context':{'synthetic':True},'packet':{'synthetic':True}}
    with server() as instance:
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        connection=http.client.HTTPConnection(*instance.server_address,timeout=2)
        connection.request('POST','/v1/voice/identity/gallery',json.dumps(body),headers)
        result=connection.getresponse();assert result.status==(400 if origin else 200);result.read();connection.close()
    assert seen==([] if origin else [body])

def test_warmup_shares_startup_deadline_without_resetting_phase_timeouts(monkeypatch):
    now=[10.];calls=[];host=ModelHost.__new__(ModelHost)
    monkeypatch.setattr('tools.board_model_host.time.monotonic',lambda:now[0])
    def voice_warmup(**kw):calls.append(('tts',kw));now[0]=14.
    host.voice=SimpleNamespace(warmup=voice_warmup,ready=True)
    host.gpu_coordinator=SimpleNamespace(acquire=lambda *a,**kw:(calls.append(('lease',kw)) or nullcontext()))
    host._warmup_llm=lambda deadline:calls.append(('llm',deadline))
    monkeypatch.setattr('tools.thinking_feedback.prepare',lambda *a,**kw:calls.append(('thinking',kw)))
    monkeypatch.setattr('tools.social_feedback.prepare',lambda *a,**kw:calls.append(('social',kw)))
    host.warmup(deadline=15.)
    assert calls==[('tts',{'timeout':5.}),('lease',{'deadline':15.}),('llm',15.),
                   ('thinking',{'deadline':15.}),('social',{'deadline':15.})]
    assert host.warmed_up

def test_expired_startup_never_starts_voice_worker(monkeypatch):
    host=ModelHost.__new__(ModelHost)
    monkeypatch.setattr('tools.board_model_host.time.monotonic',lambda:16.)
    host.voice=SimpleNamespace(warmup=lambda **kw:pytest.fail('Expired startup started TTS'))
    with pytest.raises(TimeoutError):host.warmup(deadline=15.)

def test_startup_cues_use_remaining_original_deadline(tmp_path):
    output=tmp_path/'cue.wav'
    with wave.open(str(output),'wb') as f:f.setparams((1,2,24000,0,'NONE',''));f.writeframes(bytes(48000))
    calls=[]
    class Voice:
        def generate(self,text):pytest.fail('Startup cue reset a default TTS deadline')
        def generate_bounded(self,text,**kw):
            assert kw['deadline']==123. and not kw['cancelled'].is_set();calls.append(kw['request_id'])
            return dict(path=str(output),duration_seconds=1.)
    host=SimpleNamespace(voice=Voice(),root=tmp_path)
    from tools.thinking_feedback import prepare
    from tools.social_feedback import prepare as social
    prepare(host,deadline=123.);social(host,deadline=123.)
    assert len(calls)==len(set(calls))==3 and set(host.social_assets)=={'arrival','invitation'}
