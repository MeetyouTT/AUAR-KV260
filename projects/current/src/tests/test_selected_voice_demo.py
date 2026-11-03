"""Behavior checks for cached audio, activity gating and state recovery."""
import hashlib
import json
import wave

import numpy as np
import pytest
from PIL import Image

from board.interaction.avatar_player import AvatarPlayer
from tools.selected_voice_demo import VoicePlan,SelectedVoiceRunner,activity_envelope,output_clock_seconds,RATE


@pytest.fixture
def voice_source(tmp_path):
    source=tmp_path/'voice';(source/'audio').mkdir(parents=True)
    n=int(4.4*RATE);t=np.arange(n)/RATE
    audio=(7000*np.sin(2*np.pi*240*t)).astype('<i2')
    audio[:int(.2*RATE)]=0;audio[int(1.5*RATE):int(1.9*RATE)]=0;audio[int(4.0*RATE):]=0
    rows=[];scenes=[]
    for name in ('greeting','explanation','excited','gentle'):
        path=source/'audio'/f'{name}.wav'
        with wave.open(str(path),'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(RATE);stream.writeframes(audio.tobytes())
        rows.append({'id':name,'output_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        scenes.append({'id':name,'label':name,'text':'你好，汐蓝。'})
    (source/'audio_verification.json').write_text(json.dumps({'clips':rows}),encoding='utf-8')
    (source/'scenes.json').write_text(json.dumps({'scenes':scenes}),encoding='utf-8')
    return source


@pytest.fixture
def core(tmp_path):
    root=tmp_path/'sprites'
    for name in ('idle_normal','idle_present','idle_listening','idle_thinking',
                 'talking_neutral','talking_normal','talking_low','ack_nod','emo_surprised'):
        d=root/name;d.mkdir(parents=True)
        count=22 if name in ('ack_nod','emo_surprised') else 39
        for i in range(count):Image.new('RGBA',(16,20),(i*5,70,100,255)).save(d/f'{i:06d}.png')
        (d/'meta.json').write_text(json.dumps({'fps':24,'frames':count}),encoding='utf-8')
        if count==39:(d/'segments.json').write_text(json.dumps({'enter':[0,11],'loop':[12,27],'exit':[35,38]}),encoding='utf-8')
    result=AvatarPlayer(sprite_root=root);result.idle_gain=0
    return result


def test_real_pause_closes_but_brief_gap_does_not_chatter(voice_source):
    plan=VoicePlan(voice_source);row=plan.utterances[0]
    assert plan.gain_at(row['start']+.1)==0
    assert plan.gain_at(row['start']+.5)>.99
    assert plan.gain_at(row['start']+1.75)==0
    assert plan.gain_at(row['start']+2.2)>.99
    # Keep a 40ms gap inside a word flowing rather than snapping shut.
    clip=plan.clips['greeting'].copy();clip[int(.8*RATE):int(.84*RATE)]=0
    envelope=activity_envelope(clip)
    assert min(envelope['gains'][75:90])>.99


def test_track_contains_verified_clips_and_silence_with_faded_cut(voice_source,tmp_path):
    plan=VoicePlan(voice_source);track=plan.write_audio(tmp_path/'script.wav')
    assert not np.any(track[:round(plan.utterances[0]['start']*RATE)])
    for row in plan.utterances[:-1]:
        start=round(row['start']*RATE);clip=plan.clips[row['scene']]
        assert np.array_equal(track[start:start+len(clip)],clip)
    cancelled=plan.utterances[-1];end=round(cancelled['end']*RATE)
    assert track[end-1]==0 and not np.any(track[end:end+1000])
    assert len(track)==round(plan.end*RATE)
    assert plan.gain_at(cancelled['end']+.18)==0
    assert plan.gain_at(cancelled['end']+.09)<plan.gain_at(cancelled['end']-.001)


def test_changed_selected_voice_fails_before_playback(voice_source):
    path=voice_source/'audio'/'greeting.wav';path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='hash changed'):VoicePlan(voice_source)


def test_all_emotions_cancel_and_replay_share_normal_fsm(voice_source,core):
    runner=SelectedVoiceRunner(core,VoicePlan(voice_source))
    for repeat in range(2):
        runner.reset()
        for t in np.arange(0,runner.plan.end+.05,1/30):runner.advance(min(t,runner.plan.end))
        assert not runner.trace.errors and not runner.trace.rejected
        states={row['display_state'] for row in runner.trace.samples}
        assert {'AWAKE','ACK_NOD','LISTENING','SPEAKING','SPEAKING_NEUTRAL','SPEAKING_LOW'}<=states
        assert runner.trace.samples[-1]['display_state']=='IDLE'
        assert not runner._speaking and core.speech_gain==0
        assert len([event for _,event in runner.trace.events if event.startswith('cancel')])==1
    with pytest.raises(ValueError,match='Reset'):runner.advance(0)


def test_action_finishes_before_excited_audio_starts(voice_source,core):
    runner=SelectedVoiceRunner(core,VoicePlan(voice_source));runner.reset()
    row=next(r for r in runner.plan.utterances if r['label']=='excited')
    samples=[]
    for t in np.arange(0,row['start']+.1,1/60):
        meta=runner.advance(t);samples.append((t,meta['display_state']))
    during=[state for t,state in samples if row['start']<=t]
    assert during and set(during)=={'SPEAKING'}


def test_partial_audio_block_finishes_without_a_frozen_last_frame():
    assert output_clock_seconds(47_264_000,47.27,47.264,idle=True,exhausted=True)==47.27
    assert output_clock_seconds(47_264_000,47.27,47.264,idle=True,exhausted=False)==47.264
    assert output_clock_seconds(47_264_000,47.27,47.264,idle=True,exhausted=True,paused=True)==47.264


def test_audio_clock_does_not_go_back_or_advance_from_wall_time():
    assert output_clock_seconds(1_000_000,4,1.1)==1.1
    assert output_clock_seconds(1_000_000,4,1)==1
