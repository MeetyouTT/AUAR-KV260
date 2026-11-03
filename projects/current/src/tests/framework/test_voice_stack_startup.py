"""Import-safe launcher validation; no real network, model or service starts."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from common.voice_service_capabilities import CAPABILITIES,SERVICE_REVISION


@pytest.fixture
def launcher(tmp_path,monkeypatch):
    path=Path(__file__).resolve().parents[3]/'deliverables/2026-10-18_board_dialogue/launch_models.py'
    spec=importlib.util.spec_from_file_location('tested_voice_stack_launcher',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    root=tmp_path/'project';aura=root/'aura';(aura/'config').mkdir(parents=True)
    (aura/'config/board_dialogue_model.json').write_text(json.dumps({'model':'expected','ollama_host':'http://127.0.0.1:1'}))
    here=root/'deliverables/launcher';here.mkdir(parents=True)
    monkeypatch.setattr(module,'ROOT',root);monkeypatch.setattr(module,'AURA',aura);monkeypatch.setattr(module,'HERE',here)
    monkeypatch.setattr(module,'source_fingerprint',lambda path:'f'*64)
    records=[];monkeypatch.setattr(module,'save',lambda value:records.append(copy.deepcopy(value)))
    class Socket:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def bind(self,address):pass
        def settimeout(self,value):pass
        def connect_ex(self,address):return 0
    monkeypatch.setattr(module.socket,'socket',Socket)
    monkeypatch.setattr(module.subprocess,'Popen',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Existing listeners must not be replaced')))
    voice={'ready':True,'voice_protocol':'aura-voice-1','llm_model':'expected',
           'service_revision':SERVICE_REVISION,'source_fingerprint':'f'*64,'capabilities':dict(CAPABILITIES)}
    monkeypatch.setattr(module,'read_health',lambda port:{'ready':True,'protocol':'aura-asr-1'} if port==8791 else voice)
    return module,records,voice


def test_existing_ready_models_still_require_audio_frontend_readiness(launcher,monkeypatch):
    module,records,voice=launcher
    calls=[]
    def frontend(*args,**kwargs):
        calls.append(args[0]);return SimpleNamespace(returncode=0,stdout='{"ready":true}',stderr='')
    monkeypatch.setattr(module.subprocess,'run',frontend)
    assert module.main(['--voice-python',sys.executable,'--run-id','test-run'])==0
    assert len(calls)==1 and 'start_frontend.py' in calls[0][-1]
    assert records[-1]['ready'] is True
    assert set(records[-1]['services'])=={'8791','8792','8795'}


def test_old_same_protocol_listener_is_rejected_without_starting_or_stopping_it(launcher,monkeypatch):
    module,records,voice=launcher
    voice.pop('service_revision')
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Do not start frontend after incompatible model')))
    assert module.main(['--voice-python',sys.executable])==1
    assert records[-1]['status']=='FAILED' and not records[-1]['ready']
    assert 'revision' in records[-1]['error']


def test_frontend_failure_is_not_reported_as_whole_stack_ready(launcher,monkeypatch):
    module,records,voice=launcher
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=1,stdout='',stderr='injected failure'))
    assert module.main(['--voice-python',sys.executable])==1
    assert records[-1]['status']=='FAILED' and not records[-1]['ready']
    assert 'frontend' in records[-1]['error']
