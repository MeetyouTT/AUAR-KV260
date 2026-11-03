"""Real registered assets, independent invariants; no UI/audio/camera devices."""
import visual_bootstrap
import hashlib
import numpy as np
import pytest
from PIL import Image,ImageChops
from tools.demo_script import create_demo_core
from tools.realtime_facials import RealtimeFacials
from tools.facial_layers import BlinkLayer
from tools.idle_body_compositor import seed_speaking_materials,material_variant,composite_idle_mouth

CASES=[('SPEAKING_NEUTRAL',0,'idle_normal'),('SPEAKING_NEUTRAL',2,'idle_present'),
       ('SPEAKING',4,'talking_normal'),('SPEAKING_LOW',6,'talking_low')]

@pytest.fixture(scope='module')
def rig():
    core=create_demo_core('reuse');core.idle_gain=0
    face=RealtimeFacials(core,expressive_body=True);face.body.warmup()
    return core,face

def reset(rig,state,generation,now=.4):
    core,face=rig;core.reset_playback();face.body.reset()
    core.talk_gen=generation;core.reply_text='公开测试素材';seed_speaking_materials(core,generation,now)
    return core.display_frame(state,now)

@pytest.mark.parametrize('state,generation,family',CASES)
def test_registered_body_is_displayed_with_pcm_silence_closed(rig,state,generation,family):
    core,face=rig;meta=reset(rig,state,generation)
    silent=face.apply(meta,.4,0,1);closed=face.apply(meta,.4,1,0)
    assert silent['body_asset']==family
    assert silent['image'].tobytes()==closed['image'].tobytes()
    opened=face.apply(meta,.4,1,1)
    assert opened['image'].tobytes()!=closed['image'].tobytes()
    body=face.body.player.display_frame(face.body.BODY_STATES[family],.4)['image']
    assert np.array_equal(np.asarray(opened['image'].getchannel('A')),np.asarray(body.getchannel('A')))
    # Original full-body art survives; all face edits remain above the waist.
    assert opened['image'].crop((0,340,464,480)).tobytes()==body.crop((0,340,464,480)).tobytes()

@pytest.mark.parametrize('state,generation,family',CASES)
def test_blink_uses_the_actual_body_track(rig,state,generation,family):
    core,face=rig;reset(rig,state,generation)
    meta=core.display_frame(state,1.4);seen=[];original=face.eyes.overlay
    def capture(asset,t,index=0,pose=None):
        seen.append((asset,pose));return original(asset,t,index,pose)
    face.eyes.overlay=capture
    try:result=face.apply(meta,1.4,1,.8)
    finally:face.eyes.overlay=original
    assert result['blink_active'] and seen[-1][0]==family
    assert seen[-1][1]==result['body_face_matrix']
    pose=face.body.pose_tracks[family][result['body_index']]['matrix']
    assert np.allclose(pose,result['body_face_matrix'],atol=.2)

def test_variants_stay_stable_within_owner_and_vary_in_short_turns(rig):
    core,face=rig;assets=[]
    for generation in (0,2,4,6):
        first=reset(rig,'SPEAKING_NEUTRAL',generation)
        family=face.apply(first,.4,1,.5)['body_asset']
        asset=first['asset'];assets.append((asset,family))
        for t in (.5,.6,.7):
            later=core.display_frame('SPEAKING_NEUTRAL',t)
            assert later['asset']==asset and face.apply(later,t,1,.5)['body_asset']==family
    assert all(assets[i]!=assets[i+1] for i in range(3))
    assert {row[1] for row in assets}=={'idle_normal','idle_present'}

@pytest.mark.parametrize('state',['ACK_NOD','DENY_SHAKE','AWAKE','PUZZLED'])
def test_one_shot_actions_keep_original_body(rig,state):
    core,face=rig;meta=reset(rig,state,10)
    result=face.apply(meta,.4,1,.9)
    assert 'body_asset' not in result and result['asset']==meta['asset']
    assert result['image'].tobytes()==meta['image'].tobytes()

def test_stop_finishes_closing_and_new_owner_can_reset(rig):
    core,face=rig;meta=reset(rig,'SPEAKING',4)
    face.apply(meta,.4,1,1);face.stop(.4)
    assert face.values(0,False,.4)==(1,1)
    assert face.values(0,False,.6)==(0,0) and face.closing is None
    face.body.reset();core.reset_playback();core.talk_gen=2
    seed_speaking_materials(core,2,2)
    result=face.apply(core.display_frame('SPEAKING_NEUTRAL',2),2,0,0)
    assert result['body_asset']=='idle_present' and result['speech_gain']==0

def test_legacy_constructor_retains_old_idle_override(rig):
    core,_=rig;meta=reset(rig,'SPEAKING',4)
    old=RealtimeFacials(core);result=old.apply(meta,.4,0,0)
    assert result['body_asset']=='idle_normal'
