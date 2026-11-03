import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'aura'));sys.path.insert(0,str(HERE))
from motion_queue import decide
import pytest

def cue(action='ack_nod',target=0,**kwargs):
    defaults=dict(sample=0,state='SPEAKING_NEUTRAL',audible=True,track='answer',paused=False)
    defaults.update(kwargs)
    history=defaults.pop('history',[])
    return decide(dict(action=action,at_sample=target),history,**defaults)

@pytest.mark.parametrize('action',['ack_nod','deny_shake','emo_surprised','emo_puzzled'])
def test_four_materials_start_at_audio(action):assert cue(action)==('apply','audio_cue')

def test_busy_action_is_retained_then_applied():
    assert cue(state='ACK_NOD')[0]=='wait'
    assert cue(sample=12000)[0]=='apply'
    assert cue(sample=36001)==('skip','expired_audio_cue')

@pytest.mark.parametrize('values',[dict(sample=-1),dict(audible=False),dict(track='feedback'),dict(paused=True)])
def test_no_gesture_before_answer_or_during_pause(values):assert cue(**values)[0]=='wait'

def test_budget_duplicate_and_actual_spacing():
    history=[dict(action='deny_shake',at_sample=0,started_sample=24000)]
    assert cue('deny_shake',history=history)[1]=='duplicate_action'
    assert cue(target=96000,sample=96000,history=history)[1]=='gesture_spacing'
    assert cue(target=120000,sample=120000,history=history)[0]=='apply'
    assert cue(history=history*2)[1]=='turn_budget'

def test_invalid_and_non_speech_states():
    assert cue('unknown')[1]=='unsupported_action'
    assert cue(state='LISTENING')[1]=='state_not_speaking'
    assert cue('',state='ACK_NOD')[0]=='apply'
