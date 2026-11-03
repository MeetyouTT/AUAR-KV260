"""Engine isolation, full-width delivery and real-model failure behavior."""
import pytest
from board.runtime.audio.selected_voice import SelectedVoiceSynthesizer
from board.runtime.audio.omnivoice_voice import OmniVoiceSynthesizer
from tools import dialogue_host_ollama as host

def test_engines_cannot_reuse_each_others_voice_cache():
    selected=SelectedVoiceSynthesizer.__new__(SelectedVoiceSynthesizer)
    omni=OmniVoiceSynthesizer.__new__(OmniVoiceSynthesizer)
    for synth in (selected,omni):
        synth.selection={'reference_sha256':'reference','reference_text':'逐字参考'}
        synth.revision='revision'
    qkey,qidentity=selected.identity('嗯，继续吧！')
    okey,oidentity=omni.identity('嗯，继续吧！')
    assert qkey!=okey
    assert qidentity['text']=='嗯,继续吧!'
    assert oidentity['text']=='嗯，继续吧！'

def test_reply_preserved_until_controller_submits_to_speech(stage=None):
    from tools.realtime_controller import RealtimeController
    from board.runtime.audio.omnivoice_voice import normalize_omnivoice_text
    class Jobs:
        normalize_text=staticmethod(normalize_omnivoice_text)
        def submit(self,text,emotion):self.text=text;return {'id':'one'}
    controller=RealtimeController.__new__(RealtimeController)
    controller.jobs=Jobs();controller.cancel=lambda:None;controller.send=lambda *args:None
    controller.record=lambda *args,**kwargs:None;controller.clock=lambda:0
    controller.core=type('Core',(),{'new_turn':lambda self:1})()
    controller.submit('好呀，继续！')
    assert controller.jobs.text=='好呀，继续！'

@pytest.mark.parametrize('content',['not json','{"emotion":"happy"}'])
def test_strict_model_errors_do_not_become_fixed_replies(monkeypatch,content):
    monkeypatch.setattr(host,'ollama_chat',lambda *args,**kwargs:content)
    with pytest.raises(RuntimeError,match='真实对话模型失败'):
        host.build_response({'transcript':'你好'},'ollama','model',strict=True)

def test_fast_profile_keeps_history_and_requests_speech_without_action(monkeypatch):
    captured={}
    def chat(model,system,user,**kwargs):
        captured.update(system=system,user=user,**kwargs)
        return '{"reply_text":"记得，是蓝鲸呀！","emotion":"happy","avatar_action":""}'
    monkeypatch.setattr(host,'ollama_chat',chat)
    history=[{'role':'user','content':'实验叫蓝鲸'}]
    response=host.build_response({'transcript':'叫什么？'},'ollama','model',history=history,strict=True,fast=True)
    assert captured['history']==history and captured['fast'] is True
    assert captured['user']=='叫什么？' and '汐蓝' in captured['system']
    assert response['reply_text']=='记得，是蓝鲸呀！' and response['avatar_action']==''
