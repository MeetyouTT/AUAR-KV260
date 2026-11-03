"""Dependency failure, cached checks and explicit loaded-source compatibility."""
import json
import threading
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from common.voice_service_capabilities import CAPABILITIES,SERVICE_REVISION,require_current_voice
from tools.board_model_host import ModelHost,ModelHandler
from tools.selected_voice_service import VoiceWorker
from tools.voice_service_health import OllamaDependencyHealth


def model(voice_ready=True,warmed=True,llm_ready=True):
    value=ModelHost.__new__(ModelHost)
    value.voice=SimpleNamespace(health=lambda:{'ready':voice_ready},
        generate=lambda *a:(_ for _ in ()).throw(AssertionError('Health must not synthesize')))
    value.llm_health=SimpleNamespace(status=lambda:{'ready':llm_ready})
    value.warmed_up=warmed
    value.service_fingerprint='f'*64
    return value


@pytest.mark.parametrize('voice,warmed,llm',[(False,True,True),(True,False,True),(True,True,False)])
def test_health_rejects_failed_dependency_or_unfinished_warmup(voice,warmed,llm):
    value=model(voice,warmed,llm).dependency_health(SimpleNamespace(model_id='test-asr'))
    assert value['ready'] is False


def test_healthy_loaded_model_reports_reliability_revision_without_inference():
    value=model().dependency_health(SimpleNamespace(model_id='test-asr'))
    assert value['ready'] is True
    assert value['service_revision']==SERVICE_REVISION
    assert value['capabilities']==CAPABILITIES


def test_dead_worker_does_not_keep_stale_ready_flag():
    worker=VoiceWorker.__new__(VoiceWorker)
    worker.ready=True;worker.error='';worker.cached_only=False
    worker.transport=SimpleNamespace(health=lambda:{'alive':False,'closed':False,'quarantined':False,'error':''})
    assert worker.health()['ready'] is False


def test_handler_unready_dependency_returns_503_instead_of_false_ready():
    handler=ModelHandler.__new__(ModelHandler);handler.path='/health'
    handler.server=SimpleNamespace(engine=SimpleNamespace(model_id='test-asr'),models=SimpleNamespace(
        lock=threading.Lock(),voice=SimpleNamespace(ready=False),face_features=None,conversations=None))
    observed=[]
    handler.send=lambda code,value:observed.append((code,value))
    handler.do_GET()
    assert observed[0][0]==503 and observed[0][1]['ready'] is False


def test_cheap_dependency_probe_is_cached_but_failure_replaces_old_ready():
    calls=[]
    def probe():
        calls.append(1)
        if len(calls)==1:return {'ready':True,'reachable':True,'model_available':True}
        raise OSError('injected local backend unavailable')
    dependency=OllamaDependencyHealth('http://127.0.0.1:1','fake',ttl=5,probe=probe)
    assert dependency.status()['ready'] is True
    assert dependency.status()['ready'] is True and len(calls)==1
    dependency.checked-=6
    assert dependency.status()['ready'] is False and len(calls)==2


def test_ollama_inventory_missing_configured_model_is_not_ready():
    class Connection:
        def __init__(self,*a,**kw):pass
        def request(self,*a,**kw):pass
        def getresponse(self):return SimpleNamespace(status=200,read=lambda n:json.dumps({'models':[{'name':'different-model'}]}).encode())
        def close(self):pass
    with patch('tools.voice_service_health.http.client.HTTPConnection',Connection):
        result=OllamaDependencyHealth('http://127.0.0.1:1','expected').status()
    assert result['reachable'] is True and result['model_available'] is False and result['ready'] is False


def current():
    return {'ready':True,'voice_protocol':'aura-voice-1','llm_model':'expected',
            'service_revision':SERVICE_REVISION,'source_fingerprint':'f'*64,'capabilities':dict(CAPABILITIES)}


@pytest.mark.parametrize('changes',[{'ready':False},{'llm_model':'old'},
    {'service_revision':'old'},{'source_fingerprint':'0'*64},{'capabilities':{}}])
def test_launcher_rejects_same_protocol_listener_with_wrong_capabilities_or_source(changes):
    with pytest.raises(ValueError):require_current_voice(dict(current(),**changes),'expected','f'*64)


def test_launcher_accepts_exact_loaded_source_and_model():
    require_current_voice(current(),'expected','f'*64)
