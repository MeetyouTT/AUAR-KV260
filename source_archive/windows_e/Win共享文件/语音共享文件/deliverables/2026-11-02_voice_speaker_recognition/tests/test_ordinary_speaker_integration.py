"""Exercise the real released Jobs/runtime/controller composition with fake models."""
import ast
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import os
from pathlib import Path
import sys
import threading
import time

import pytest

TASK=Path(__file__).resolve().parents[1]
RUNTIME=Path(os.environ.get('AURA_SPEAKER_RUNTIME',str(TASK/'candidate_runtime')))
sys.path.insert(0,str(RUNTIME))
ORIGINAL=(TASK.parent/'2026-11-02_5090_deployment/other_components_20261102/'
    'live_enrollment_20261102/voice_conversation_address_20261102/composition.py')


def harness_classes():
    # Reuse only the existing synthetic harness definitions/imports, not its
    # old source-selection logic, pin assertions, fixtures or tests. All target
    # runtime classes are imported from the candidate selected above.
    tree=ast.parse(ORIGINAL.read_text(encoding='utf-8'))
    definitions=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.ClassDef))]
    namespace={'__name__':'synthetic_current_speaker_composition','HERE':ORIGINAL.parent,
        'RELEASE':RUNTIME,'MODE':'candidate'}
    exec(compile(ast.Module(body=definitions,type_ignores=[]),str(ORIGINAL),'exec'),namespace)
    for key in ('BoardBusinessRuntime','BoardSpeakerBusiness','BoardDialogueController','BoardDialogueJobs'):
        module=sys.modules[namespace[key].__module__]
        assert Path(module.__file__).resolve().is_relative_to(RUNTIME.resolve())
    original_models=namespace['Models']
    class Models(original_models):
        def __init__(self):
            super().__init__();self.payloads=[]
        def request(self,kind,payload,**kwargs):
            self.payloads.append((kind,copy.deepcopy(payload)))
            return super().request(kind,payload,**kwargs)
    class Encoder:
        model_id='synthetic-ecapa-model';dimension=192
        def __init__(self):
            self.kind=0;self.calls=0;self.block_kind=None
            self.entered=threading.Event();self.release=threading.Event()
        def encode(self,raw):
            self.calls+=1;kind=self.kind
            if kind==self.block_kind:
                self.entered.set();assert self.release.wait(3)
            return tuple(1. if n==kind else 0. for n in range(192))
    namespace['Models']=Models;namespace['Encoder']=Encoder
    return namespace['Composition']


@pytest.fixture
def full(tmp_path,monkeypatch):
    value=harness_classes()(tmp_path,monkeypatch)
    def setup():
        store=value.business.hub.speaker.store.original
        store.enroll('synthetic-identity-a','测试甲',tuple(1. if n==0 else 0. for n in range(192)),consent=True)
        store.enroll('synthetic-identity-b','测试乙',tuple(1. if n==1 else 0. for n in range(192)),consent=True)
        value.business._refresh_public()
    value.business.pool.submit(setup).result(2)
    try:yield value
    finally:
        value.encoder.release.set();value.close()


def current_name(full):
    llm=[payload for kind,payload in full.models.payloads if kind=='llm'][-1]
    notes=[m['content'] for m in llm['messages'] if m['role']=='system' and '声纹称呼候选' in m['content']]
    assert len(notes)==1
    return json.loads(notes[0].partition('：')[2].split('。',1)[0])['display_name']


def test_actual_ordinary_route_switches_voice_names_and_clears_unknown(full):
    for kind,name in ((0,'测试甲'),(1,'测试乙'),(2,None),(0,'测试甲')):
        full.encoder.kind=kind
        latency,errors=full.say('雪妃，今天我想轻松聊一聊，请和我打个招呼。')
        assert not errors
        assert current_name(full)==name
        public=full.business.public()
        assert public['speaker_calibrated'] is False and public['automatic_profile_access'] is False
        assert public['conversation_address']['personal_memory_allowed'] is False
    assert full.encoder.calls==4
    assert [kind for kind in full.models.calls if kind=='llm']==['llm']*4


def test_real_prompt_waits_for_this_voice_instead_of_sending_old_name(full):
    assert not full.say('雪妃，和我打个招呼吧。')[1]
    assert current_name(full)=='测试甲'
    count=sum(kind=='llm' for kind in full.models.calls)
    full.encoder.kind=1;full.encoder.block_kind=1
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(full.say,'今天我来和你聊天，你先说一句欢迎吧。')
        assert full.encoder.entered.wait(1)
        try:
            time.sleep(.04)
            assert sum(kind=='llm' for kind in full.models.calls)==count
        finally:full.encoder.release.set()
        assert not future.result(3)[1]
    assert current_name(full)=='测试乙'
    assert full.encoder.calls==2
