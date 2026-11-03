"""Independent local privacy, short-circuit and exception-preservation probes."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
EXPECTED={
 'board/runtime/audio/board_dialogue_jobs.py':'580b2cf796275104cf15f2295afa2de29f82f32eabdd783a4b3aff858840a464',
 'board/runtime/board_business.py':'d034227118063dc4dbfb69f4bc735000980bd166e91262b4953f0db4b1baf5cc'}
for relative,digest in EXPECTED.items():
 assert hashlib.sha256((ROOT/'candidate'/relative).read_bytes()).hexdigest()==digest
spec=importlib.util.spec_from_file_location('original_trace_fixture',ROOT/'test_entry_trace.py')
fixture=importlib.util.module_from_spec(spec);sys.modules[spec.name]=fixture;spec.loader.exec_module(fixture)
assert fixture.MODE=='candidate'
CANARY='PRIVATE_SYNTHETIC_PERSON_ID_TEXT_TARGET_PCM_7d92'


def test_blank_ASR_called_once_and_does_not_reach_any_handler_or_dialogue():
 j,job,ctl,clock=fixture.jobs_fixture('')
 calls=[]
 original=j.asr.transcribe
 def counted(*args,**kwargs):calls.append('ASR');return original(*args,**kwargs)
 j.asr.transcribe=counted
 j._route=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Blank reached route'))
 assert j.run_next()
 trace=j.public()['last_voice_route']['entry_trace']
 assert calls==['ASR'] and trace['outcome']=='rejected' and not trace['handler_called']
 assert trace['asr_characters']==0 and trace['asr_result_seen']
 fixture.no_text(trace)


@pytest.mark.parametrize('branch',['speaker-query','active-enrollment','explicit-memory'])
def test_original_short_circuits_and_single_handler_dispatch_are_preserved(branch):
 calls=[]
 class Handler:
  def public(self):return {'active':False}
  def __call__(self,text,**kwargs):calls.append(('handler',text));return None
 h=Handler();j,job,ctl,_=fixture.jobs_fixture(handlers={'speaker_identity':h,'identity_enrollment':h})
 def state():calls.append(('state',));return {'active':branch=='active-enrollment'}
 j._enrollment_state=state
 if branch=='speaker-query':
  assert fixture.route(j,job,'声纹保存了吗')==(None,None)
  assert calls==[('handler','声纹保存了吗')]
  assert not fixture.trace(j)['enrollment_checked']
 elif branch=='active-enrollment':
  with patch('common.voice_enrollment.enrollment_requested',side_effect=AssertionError('Original OR short circuit changed')):
   assert fixture.route(j,job,'普通话题')==(None,None)
  assert calls==[('state',),('handler','普通话题')]
  assert fixture.trace(j)['enrollment_checked'] and fixture.trace(j)['enrollment_active']
 else:
  ctl.command_handler=object()
  with patch('common.profile_memory.scoped_command',return_value=('synthetic-command',None)):
   assert fixture.route(j,job,'普通话题')==(None,None)
  assert calls==[] and fixture.trace(j)['capability']=='explicit_memory_commands'


def test_speaker_presence_does_not_expire_or_read_private_fields_or_call_state():
 f=fixture.fixture();device=f.business.device
 def forbidden(*args,**kwargs):raise AssertionError('Diagnostic called mutating state')
 device.state=forbidden
 key=('synthetic-boot','synthetic-session')
 device.sessions[key]={'until':f.clock()-1,'name':CANARY,'person_id':CANARY,'target':CANARY,'vectors':[]}
 before=copy.deepcopy(device.sessions)
 value=f.handler._entry_speaker_presence({'board_boot_id':key[0],'session_id':key[1]})
 assert value=={'known':True,'present':True,'active':False}
 assert device.sessions==before and CANARY not in json.dumps(value)


def test_business_SystemExit_same_object_is_rethrown_once_without_message_projection():
 f=fixture.fixture();f.forbid_source=True;calls=[];error=SystemExit(CANARY)
 def fail(*args,**kwargs):calls.append('turn');raise error
 f.business.turn=fail
 with pytest.raises(SystemExit) as captured:f.say('登记声纹，我叫合成姓名')
 assert captured.value is error and calls==['turn']
 trace=f.handler.public()['entry_trace']
 assert trace['business_turn_calls']==1 and trace['business_turn_result']=='error'
 assert trace['error_class']=='other' and trace['phase']=='error'
 assert CANARY not in json.dumps(trace) and 'SystemExit' not in json.dumps(trace)
 fixture.no_text(trace)
