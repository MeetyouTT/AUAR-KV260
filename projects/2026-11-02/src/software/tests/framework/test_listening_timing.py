"""Early PCM, bounded visual quarantine, and ACK-safe microphone handoff."""
import copy

import pytest

from tools.handsfree_recording import HandsFreeRecordingController
from tools.barge_in_recording import BargeInRecordingController
from board.runtime.audio.automatic_capture import AutomaticMcp01Capture
from tools.barge_in_capture import BargeInCapture
from tests.framework.test_handsfree_dialogue import Tx, view, gap
from tests.framework.test_automatic_conversation import FakeController, FakeCapture
from tests.framework.test_voice_barge_in import Barge


def setup(barge=False):
    now=[1.];source=[view()];tx=Tx();inner=FakeController();caps=[]
    def factory():
        cap=Barge('barge%d'%(len(caps)+1));caps.append(cap);return cap
    kind=BargeInRecordingController if barge else HandsFreeRecordingController
    extra={'barge_capture_factory':factory} if barge else {}
    owner=kind(inner,transcriber=tx,boot_id='boot',attention_provider=lambda:copy.deepcopy(source[0]),
        early_listen=True,clock=lambda:now[0],auto_capture_factory=FakeCapture,**extra)
    owner.tick()
    return now,source,tx,inner,owner,caps


def stable(now,source,owner):
    now[0]=1.6;source[0]=view(1600,2);owner.tick()


def submit(owner):
    owner.capture.on_speech_start();owner.capture.state='READY';owner.tick()


def test_first_frontal_frame_prepares_pcm_without_starting_a_conversation():
    now,source,tx,inner,owner,caps=setup()
    try:
        assert owner._recording() and owner.capture.counter==1
        assert not owner.entry_stable and not owner.auto_enabled
        assert tx.selections==[] and tx.submitted==[]
        stable(now,source,owner)
        assert owner.entry_stable and owner.capture.counter==1
    finally:owner.close()


def test_early_short_utterance_is_held_until_two_fresh_frames_confirm_target():
    now,source,tx,inner,owner,caps=setup()
    try:
        now[0]=1.2;owner.capture.on_speech_start();owner.capture.state='READY';owner.tick()
        assert owner.awaiting_entry and not tx.submitted and tx.selections==[]
        clip=owner.utterance
        stable(now,source,owner)
        assert tx.submitted==[clip] and tx.selections==[False]
        assert owner.capture.counter==1
    finally:owner.close()


def test_missing_visual_stability_never_promotes_a_held_utterance():
    now,source,tx,inner,owner,caps=setup()
    try:
        now[0]=1.2;owner.capture.on_speech_start();owner.capture.state='READY';owner.tick()
        now[0]=3.;source[0]=None;owner.tick()
        assert not tx.submitted and not owner.monitor_owned and not owner._recording()
    finally:owner.close()


def test_brief_loss_keeps_same_pcm_then_requires_fresh_same_target_to_submit():
    now,source,tx,inner,owner,caps=setup()
    try:
        stable(now,source,owner);owner.capture.on_speech_start()
        now[0]=2.7;source[0]=gap(2700,3);owner.tick()
        assert owner._recording() and owner.visual_hold_since is not None
        owner.capture.state='READY';owner.tick()
        assert owner.awaiting_entry and not tx.submitted
        clip=owner.utterance
        now[0]=3.0;source[0]=view(3000,4);owner.tick()
        assert tx.submitted==[clip] and owner.capture.counter==1
    finally:owner.close()


@pytest.mark.parametrize('change',['multiple','new_track','new_service','camera_lost','missing'])
def test_visual_hold_never_crosses_hard_source_or_target_changes(change):
    now,source,tx,inner,owner,caps=setup()
    try:
        stable(now,source,owner);owner.capture.on_speech_start()
        now[0]=2.7;source[0]=gap(2700,3);owner.tick()
        now[0]=2.8;source[0]=view(2800,4)
        if change=='multiple':source[0]['modules']['identity']['face_count']=2
        elif change=='new_track':source[0]['modules']['identity']['face_attention']['target']['track_generation']=2
        elif change=='new_service':source[0]['service_epoch']='new'
        elif change=='camera_lost':source[0]['modules']['camera']['state']='LOST'
        elif change=='missing':source[0]=None
        owner.tick()
        assert not owner._recording() and not tx.submitted and not owner.monitor_owned
    finally:owner.close()


def test_zero_face_packets_cannot_extend_visual_hold_indefinitely():
    now,source,tx,inner,owner,caps=setup()
    try:
        stable(now,source,owner);owner.capture.on_speech_start()
        for stamp in (2700,3200,4000):
            now[0]=stamp/1000;source[0]=gap(stamp,stamp);owner.tick()
            assert owner.monitor_owned
        now[0]=4.2;source[0]=gap(4200,4200);owner.tick()
        assert not owner.monitor_owned and not tx.submitted
    finally:owner.close()


def test_silent_present_person_does_not_force_a_thirty_second_device_reopen():
    now,source,tx,inner,owner,caps=setup()
    try:
        stable(now,source,owner)
        now[0]=32.;source[0]=view(32000,3);owner.tick()
        assert owner.monitor_owned and owner._recording() and owner.capture.counter==1
        assert not tx.submitted
    finally:owner.close()


def completed(now,source,tx,inner,owner,caps):
    stable(now,source,owner);submit(owner)
    owner.transcription.update(state='GENERATING',text='你好')
    inner.state.update(phase='SPEAKING',playing=True);owner.tick()
    capture=caps[0]
    inner.state.update(phase='IDLE',playing=False);tx.pending=False
    inner.completions.append(({'request_id':'req-1','capture_id':'cap-1'},{}));owner.tick()
    assert owner.transcription['state']=='ANSWERED'
    return capture


def test_speech_during_ack_tail_is_retained_without_cancelling_old_ack():
    now,source,tx,inner,owner,caps=setup(True)
    try:
        capture=completed(now,source,tx,inner,owner,caps)
        before=tx.cancelled
        capture.on_speech_start();capture.state='READY';owner.tick()
        assert tx.cancelled==before and len(tx.ack_calls)==1 and owner.barge_interruptions==0
        assert len(tx.submitted)==1 and not capture.closed
        assert owner.public()['voice_barge_in']['next_utterance_pending']
        tx.last_ack={'request_id':'req-1','committed':True}
        now[0]=2.2;source[0]=view(2200,3);owner.tick();owner.tick()
        assert len(tx.submitted)==2 and tx.submitted[-1].capture_id=='barge1'
        assert tx.submitted[-1].pcm==b'\x12\x34'*16000
        assert tx.selections==[False] and owner.tail_handoffs==1 and owner.barge_interruptions==0
    finally:owner.close()


def test_idle_tail_capture_is_handed_over_without_restarting_microphone():
    now,source,tx,inner,owner,caps=setup(True)
    try:
        capture=completed(now,source,tx,inner,owner,caps)
        tx.last_ack={'request_id':'req-1','committed':True}
        now[0]=2.2;source[0]=view(2200,3);owner.tick()
        assert owner.capture is capture and capture.counter==1 and not capture.closed
        capture.on_speech_start();capture.state='READY';owner.tick()
        assert len(tx.submitted)==2 and tx.selections==[False]
    finally:owner.close()


@pytest.mark.parametrize('committed',[False,None])
def test_failed_or_missing_ack_cannot_promote_early_next_utterance(committed):
    now,source,tx,inner,owner,caps=setup(True)
    try:
        capture=completed(now,source,tx,inner,owner,caps)
        capture.on_speech_start();capture.state='READY';owner.tick()
        if committed is False:tx.last_ack={'request_id':'req-1','committed':False}
        now[0]=9.;source[0]=view(9000,3);owner.tick()
        assert len(tx.submitted)==1 and capture.closed and not owner.auto_enabled
    finally:owner.close()


def test_pause_during_tail_closes_retained_microphone():
    now,source,tx,inner,owner,caps=setup(True)
    try:
        capture=completed(now,source,tx,inner,owner,caps)
        owner.cancel();owner.tick()
        assert capture.closed and not owner.monitor_enabled and not owner._recording()
    finally:owner.close()


def test_closed_capture_cannot_report_stale_endpoint_as_current_speech():
    now,source,tx,inner,owner,caps=setup()
    try:
        stable(now,source,owner)
        owner.capture.snapshot=lambda:{'state':'CANCELLED','error':'','sample_count':0,'speech_active':True}
        assert not owner.public()['automatic_conversation']['speech_active']
    finally:owner.close()


def test_capture_uses_small_period_with_existing_duplex_buffer_preserved():
    ordinary=AutomaticMcp01Capture(lambda:False)
    duplex=BargeInCapture(None)
    assert '--period-time=20000' in ordinary._command()
    assert '--buffer-time=160000' in ordinary._command()
    assert '--buffer-time=80000' in duplex._command()
    assert '--samples' not in ordinary._command()
