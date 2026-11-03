"""Controller-level tests: audio timing, bounded wait, cancellation and diagnostics."""
import sys,types,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'aura'))
import tools
tools.__path__=[str(HERE/'candidate_sources/tools'),*tools.__path__]
from tools.streaming_controller import StreamingController
import pytest

@pytest.fixture
def ctrl():
    c=StreamingController.__new__(StreamingController)
    core=types.SimpleNamespace(fsm=types.SimpleNamespace(state=types.SimpleNamespace(label='ACK_NOD')),
                               emotion='neutral',talk_gen=1)
    calls=[]
    def apply(value):
        calls.append(value);core.fsm.state.label={'ack_nod':'ACK_NOD','deny_shake':'DENY_SHAKE'}.get(value['avatar_action'],'SPEAKING_NEUTRAL')
    core.apply_response=apply;c.core=core;c.reply='test';c.render_requested=False;c.last_meta={}
    c.output=types.SimpleNamespace(paused=False,read=lambda:dict(audible=True,track='answer',answer_clock=0),
                                  position=lambda:0,finished=lambda:False)
    c.stream=dict(generation=1,response_applied=True,controls=[dict(action='deny_shake',at_sample=0,emotion='friendly')],
                  actions=[],motion_events=[],puzzled_visible_at=None,audio_done=False,network=None,hint=False)
    c.now=lambda:0;c.record=lambda *args,**kw:None
    return c,calls

def test_busy_material_waits_then_applies_exactly_once(ctrl):
    c,calls=ctrl;c.tick();assert len(c.stream['controls'])==1 and calls==[]
    c.core.fsm.state.label='SPEAKING_NEUTRAL';c.tick();c.tick()
    assert len(calls)==1 and not c.stream['controls']
    assert c.stream['motion_events'][0]['outcome']=='apply'

def test_busy_material_expires_with_reason(ctrl):
    c,calls=ctrl;c.tick()
    c.output.read=lambda:dict(audible=True,track='answer',answer_clock=1.6)
    c.tick();assert calls==[] and c.stream['controls']==[]
    assert c.stream['motion_events'][0]['reason']=='expired_audio_cue'

def test_feedback_and_pause_do_not_consume_action(ctrl):
    c,calls=ctrl;c.core.fsm.state.label='SPEAKING_NEUTRAL'
    c.output.read=lambda:dict(audible=True,track='feedback',answer_clock=0)
    c.tick();assert not calls
    c.output.paused=True;c.output.read=lambda:dict(audible=True,track='answer',answer_clock=0)
    c.tick();assert not calls
    c.output.paused=False;c.tick();assert len(calls)==1

def test_cancel_clears_pending_actions_and_rejects_late_owner(ctrl):
    c,calls=ctrl
    # Base cancel owns the media stop; verify streaming cancels its queue first.
    from unittest.mock import patch
    with patch('tools.realtime_controller.RealtimeController.cancel'):
        c.cancel()
    c.channel_event(dict(kind='control',action='ack_nod'),b'',{}, {},0)
    assert c.stream is None and calls==[]
