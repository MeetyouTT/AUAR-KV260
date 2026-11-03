import importlib.util
from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

from board.runtime.reasoning_dialogue import LocalReasoningDialogue
from board.runtime.board_dialogue import StaleGeneration
from common.inference_output_contract import build_body
from tools.production_output_format import NegotiatedDialogueClient

H=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('public_d01_integration_fixture',H/'board_integration_v17/worker.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


@pytest.fixture
def h(tmp_path):
    harness=fixture.Harness(H/'board_integration_v17/local_runtime_v17',tmp_path,'public-d01')
    try:yield harness
    finally:harness.close()


def test_actual_paired_reasoning_uses_original_controller_wire_and_complete_ack(h):
    text='雪妃，帮我计算17乘以23'
    answer=h.say(text,route='reasoning_dialogue',reject_bad_ack=True)
    calls=[payload for kind,payload in h.transport.calls if kind=='llm']
    assert len(calls)==1 and calls[0]['options']=={'think':True}
    assert text in [row['text'] for row in h.bundle.store.history(h.scope) if row['source']=='user_said']
    assert answer['full_ack'] and answer['partial_ack_rejected'] and not h.bundle.access.grants
    body=build_body(dict(options={'num_ctx':2048}),calls[0])
    assert body['think'] is True and body['options']=={'num_ctx':2048,'num_predict':120}
    assert body['format']=='json' and body['messages']==calls[0]['messages']


def test_ordinary_chat_keeps_original_options_and_no_reasoning_interceptor(h):
    answer=h.say('雪妃，今天有点累，陪我聊一会儿')
    calls=[payload for kind,payload in h.transport.calls if kind=='llm']
    assert len(calls)==1 and calls[0]['options']=={} and 'reasoning_dialogue' not in answer['routes']


@pytest.mark.parametrize('mode',['stale','cancelled','expired','no_profile_grant','not_reasoning'])
def test_admission_preserves_original_stale_deadline_and_profile_scope(h,mode):
    cancel=threading.Event();current=lambda:mode!='stale'
    if mode=='cancelled':cancel.set()
    scope=dict(kind='profile',id='a'*32) if mode=='no_profile_grant' else h.scope
    job=SimpleNamespace(deadline=h.clock() if mode=='expired' else h.clock()+10,scope=scope)
    text='今天想闲聊' if mode=='not_reasoning' else '计算17乘以23'
    error=(StaleGeneration if mode in ('stale','cancelled') else TimeoutError if mode=='expired'
           else PermissionError if mode=='no_profile_grant' else ValueError)
    with pytest.raises(error):
        LocalReasoningDialogue()(text,job=job,controller=h.bundle.controller,is_current=current,cancel_event=cancel)
    assert h.transport.calls==[] and not h.bundle.access.grants


def test_negotiated_compact_adapter_preserves_reasoning_json_and_original_prompt(h):
    h.transport.output_format_capabilities=lambda:dict(format_contract_version=1,output_formats=['json','dialogue_abc_v1'])
    client=NegotiatedDialogueClient(h.transport,system_prompt=h.pair.selected_prompt,mode='dialogue_abc_v1')
    h.bundle.controller.model_client=client
    h.say('雪妃，请逐步计算17乘以23',route='reasoning_dialogue')
    payload=next(payload for kind,payload in h.transport.calls if kind=='llm')
    assert payload['options']=={'think':True}
    assert payload['messages'][0]==dict(role='system',content=h.pair.selected_prompt)
    assert client.public()['negotiated_dialogue_format']=='dialogue_abc_v1'
