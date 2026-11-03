"""End-to-end legacy budget must include phase admission and ASR elapsed time."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import wave
import pytest
from tools.board_model_host import ModelHost
from common.gpu_coordination import GpuBusy

def fixture(tmp_path,monkeypatch,*,admitted_at=14.,deny=False):
    now=[10.];calls=[]
    monkeypatch.setattr('tools.board_model_host.time.monotonic',lambda:now[0])
    class Coordinator:
        def acquire(self,kind,**kwargs):
            calls.append(('lease',kind,kwargs['deadline']))
            if deny:raise GpuBusy('resource busy')
            now[0]=admitted_at
            @contextmanager
            def held():
                try:yield
                finally:calls.append(('released',kind))
            return held()
    output=tmp_path/'public.wav'
    with wave.open(str(output),'wb') as f:
        f.setparams((1,2,24000,0,'NONE',''));f.writeframes(b'\0\0'*24000)
    def llm(*args,**kwargs):
        calls.append(('llm',kwargs.get('timeout_s')));now[0]+=.4
        return dict(reply_text='公开预算检查',emotion='neutral',avatar_action='')
    monkeypatch.setattr('tools.board_model_host.dialogue.build_response',llm)
    class Voice:
        def generate(self,*args):raise AssertionError('Bounded legacy caller must not restart the default TTS timeout')
        def generate_bounded(self,text,*,deadline,cancelled,request_id):
            assert not cancelled.is_set();calls.append(('tts',deadline,request_id));now[0]+=.3
            return dict(path=str(output),duration_seconds=1.,cache_hit=False)
    models=ModelHost.__new__(ModelHost);models.gpu_coordinator=Coordinator();models.root=tmp_path
    models.histories={};models.wire_histories={};models.preference_memories={};models.voice=Voice()
    owner=dict(board_boot_id='public-boot',session_id='public-session',request_id='public-budget',generation=1,budget_ms=60000)
    return models,owner,calls

def test_same_absolute_budget_is_passed_through_admission_llm_and_tts(tmp_path,monkeypatch):
    models,owner,calls=fixture(tmp_path,monkeypatch)
    result=models.answer(owner,'你好',deadline=15.)
    assert result['reply_text']=='公开预算检查'
    assert calls[0]==('lease','llm',15.)
    assert ('llm',1.) in calls and ('tts',15.,owner['request_id']) in calls
    assert ('released','llm') in calls

def test_expired_admission_never_starts_model_or_tts(tmp_path,monkeypatch):
    models,owner,calls=fixture(tmp_path,monkeypatch,admitted_at=15.1)
    with pytest.raises(TimeoutError):models.answer(owner,'你好',deadline=15.)
    assert calls==[('lease','llm',15.),('released','llm')]

def test_busy_admission_does_not_touch_the_warm_voice_worker(tmp_path,monkeypatch):
    models,owner,calls=fixture(tmp_path,monkeypatch,deny=True)
    with pytest.raises(GpuBusy):models.answer(owner,'你好',deadline=15.)
    assert calls==[('lease','llm',15.)]

def test_disconnected_client_is_rejected_before_any_gpu_phase(tmp_path,monkeypatch):
    models,owner,calls=fixture(tmp_path,monkeypatch)
    with pytest.raises(InterruptedError):models.answer(owner,'你好',deadline=15.,is_cancelled=lambda:True)
    assert calls==[]
