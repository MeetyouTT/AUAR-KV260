"""Real worker/matcher/SQLite with synthetic voices; no microphone or real users."""
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import threading
import time

import pytest

TASK=Path(__file__).resolve().parents[1]
RUNTIME=Path(os.environ.get('AURA_SPEAKER_RUNTIME',str(TASK/'candidate_runtime')))
sys.path.insert(0,str(RUNTIME))
from board.runtime.board_speaker_business import BoardSpeakerBusiness
from board.runtime.board_dialogue import conversation_address_note


def vector(index):
    return tuple(1. if n==index else 0. for n in range(192))


class Encoder:
    model_id='synthetic-speaker-model'
    dimension=192
    def __init__(self):
        self.calls=0
        self.block_kind=None
        self.entered=threading.Event()
        self.release=threading.Event()
    def encode(self,pcm):
        self.calls+=1
        marker=struct.unpack('<h',pcm[:2])[0]
        if marker==self.block_kind:
            self.entered.set()
            assert self.release.wait(3),'Synthetic blocking encoder was not released'
        if marker==4:
            return tuple(1. if n in (0,1) else 0. for n in range(192))
        return vector({1:0,2:1,3:2}.get(marker,0))


def quality(pcm):
    if struct.unpack('<h',pcm[:2])[0]==5:
        raise ValueError('Synthetic insufficient speech')
    return pcm,{'vad_speech_seconds':3.}


class Harness:
    cid='a'*32
    def __init__(self,path):
        self.encoder=Encoder();self.sequence=0
        self.service=BoardSpeakerBusiness.create(path,encoder_factory=lambda:self.encoder,
            board_boot_id='synthetic-boot',quality=quality,expected_model_id=self.encoder.model_id,
            anonymous_config={'enabled':True},calibration={'threshold':.35,'margin':.1,
            'consistency':.6,'field_calibrated':False},clock=time.monotonic,wall_clock=time.time,
            data_origin='synthetic')
        def setup():
            # Fixture-only synthetic registrations. Actual production enrollment
            # still uses the existing explicit voice registration FSM.
            store=self.service.hub.speaker.store.original
            store.enroll('synthetic-person-a','测试甲',vector(0),consent=True)
            store.enroll('synthetic-person-b','测试乙',vector(1),consent=True)
            self.service._refresh_public()
        self.service.pool.submit(setup).result(2)
    def begin(self,marker,*,cancel=None,cid=None,generation=None,session='synthetic-session'):
        self.sequence+=1;n=self.sequence
        pcm=struct.pack('<hh',marker,n)+b'\x01\x00'*(48000-2)
        meta=dict(protocol='aura-asr-1',board_boot_id='synthetic-boot',session_id=session,
            request_id='synthetic-request-'+str(n),generation=n if generation is None else generation,
            capture_id='synthetic-capture-'+str(n),sample_count=48000,
            pcm_sha256=hashlib.sha256(pcm).hexdigest(),budget_ms=120000)
        cancel=cancel or threading.Event();cid=cid or self.cid
        def adopt(value):
            self.service.adopt_conversation_address(meta,cid,cancel_event=cancel)
        self.service.submit_analysis(meta,pcm,cid,on_evidence=adopt,cancel_event=cancel,
            deadline=time.monotonic()+4)
        return meta,pcm,cancel,cid
    def settled(self):
        self.service.pool.submit(lambda:None).result(3)
    def hint(self,call,*,seconds=2):
        meta,pcm,cancel,cid=call
        owner={k:meta[k] for k in ('board_boot_id','session_id','generation','request_id')}
        return self.service.conversation_address(owner,cid,cancel_event=cancel,
            deadline=time.monotonic()+seconds)
    def say(self,marker,**kwargs):
        call=self.begin(marker,**kwargs);self.settled();return call,self.hint(call)
    def close(self):
        self.encoder.release.set()
        assert self.service.close(timeout=3)


@pytest.fixture
def h(tmp_path):
    value=Harness(tmp_path/'synthetic-speaker-only')
    try:yield value
    finally:value.close()


def test_first_capture_identifies_without_three_repetitions(h):
    call,hint=h.say(1)
    assert hint['display_name']=='测试甲'
    assert hint['field_calibrated'] is False and hint['identity_verified'] is False
    assert hint['personal_memory_allowed'] is False
    assert h.encoder.calls==1


def test_same_conversation_waits_for_new_speaker_instead_of_old_name(h):
    assert h.say(1)[1]['display_name']=='测试甲'
    h.encoder.block_kind=2
    call=h.begin(2);assert h.encoder.entered.wait(1)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(h.hint,call)
        try:
            time.sleep(.04)
            assert not future.done(),'Current utterance returned the previous speaker before analysis'
        finally:h.encoder.release.set()
        assert future.result(2)['display_name']=='测试乙'
    assert h.encoder.calls==2


@pytest.mark.parametrize('marker',[3,4,5],ids=['unknown','ambiguous','insufficient-speech'])
def test_unmatched_current_capture_never_inherits_previous_name(h,marker):
    assert h.say(1)[1]['display_name']=='测试甲'
    call,hint=h.say(marker)
    assert hint is None
    public=h.service.public()['conversation_address']
    assert public['matched_captures']==0
    assert public.get('current_capture_match',False) is False


def test_each_known_speaker_switches_in_one_utterance(h):
    for marker,name in ((1,'测试甲'),(2,'测试乙'),(1,'测试甲'),(2,'测试乙')):
        call,hint=h.say(marker)
        assert hint['display_name']==name
    assert h.encoder.calls==4


def test_cancel_during_new_voice_does_not_restore_previous_name(h):
    assert h.say(1)[1]['display_name']=='测试甲'
    h.encoder.block_kind=2;call=h.begin(2);assert h.encoder.entered.wait(1)
    call[2].set();h.encoder.release.set();h.settled()
    assert h.hint(call) is None
    assert h.service.public()['conversation_address'].get('current_capture_match',False) is False


def test_explicit_cancel_analysis_revokes_the_current_capture_name(h):
    call,hint=h.say(1);assert hint['display_name']=='测试甲'
    h.service.cancel_analysis(call[0],call[3])
    assert h.hint(call) is None
    assert h.service.public()['conversation_address']['matched_captures']==0


def test_expired_new_analysis_does_not_fall_back_to_previous_name(h):
    assert h.say(1)[1]['display_name']=='测试甲'
    h.encoder.block_kind=2;call=h.begin(2);assert h.encoder.entered.wait(1)
    try:assert h.hint(call,seconds=.02) is None
    finally:h.encoder.release.set()
    h.settled()


def test_late_older_result_cannot_replace_the_new_speaker(h):
    assert h.say(2)[1]['display_name']=='测试乙'
    h.encoder.block_kind=1;old=h.begin(1);assert h.encoder.entered.wait(1)
    new=h.begin(2);h.encoder.release.set();h.settled()
    assert h.hint(old) is None
    assert h.hint(new)['display_name']=='测试乙'


def test_duplicate_request_reuses_only_that_capture_without_reencoding(h):
    call,hint=h.say(1);before=h.encoder.calls
    meta,pcm,cancel,cid=call
    h.service.submit_analysis(meta,pcm,cid,cancel_event=cancel)
    assert h.hint(call)['display_name']=='测试甲'
    assert h.encoder.calls==before


def test_conversation_and_session_are_not_interchangeable(h):
    old,hint=h.say(1);assert hint['display_name']=='测试甲'
    call,hint=h.say(3,cid='b'*32,session='another-synthetic-session')
    assert hint is None
    owner={k:old[0][k] for k in ('board_boot_id','session_id','generation','request_id')}
    assert h.service.conversation_address(owner,'b'*32,cancel_event=threading.Event(),
        deadline=time.monotonic()+1) is None


def test_gallery_change_invalidates_current_name(h):
    call,hint=h.say(1);assert hint['display_name']=='测试甲'
    def change():
        h.service.hub.speaker.store.original.delete('synthetic-person-a')
        h.service._refresh_public()
    h.service.pool.submit(change).result(2)
    assert h.hint(call) is None


def test_cancel_old_capture_does_not_revoke_new_speaker(h):
    old,hint=h.say(1);assert hint['display_name']=='测试甲'
    new,hint=h.say(2);assert hint['display_name']=='测试乙'
    h.service.cancel_analysis(old[0],old[3])
    assert h.hint(new)['display_name']=='测试乙'


def test_stale_generation_cannot_clear_current_speaker(h):
    call,hint=h.say(2);assert hint['display_name']=='测试乙'
    current,hint=h.say(1);assert hint['display_name']=='测试甲'
    with pytest.raises(ValueError,match='Stale or reused'):
        h.begin(2,generation=0)
    assert h.hint(current)['display_name']=='测试甲'


def test_quiet_expiry_is_not_projected_as_a_current_capture_match(h):
    call,hint=h.say(1);assert hint['display_name']=='测试甲'
    original=h.service.clock
    h.service.clock=lambda:original()+30
    assert h.hint(call) is None
    public=h.service.public()['conversation_address']
    assert public['current_capture_match'] is False and public['matched_captures']==0


def test_unavailable_named_analyzer_cannot_reuse_old_name(h):
    call,hint=h.say(1);assert hint['display_name']=='测试甲'
    h.service.hub.progressive_speaker=None
    assert h.say(2)[1] is None


def test_public_status_is_per_utterance_and_has_no_identity_values(h):
    call,hint=h.say(1);public=h.service.public()['conversation_address']
    assert public['mode']=='PER_UTTERANCE'
    assert public['current_capture_match'] is True
    assert public['session_cached'] is False
    serialized=json.dumps(public,ensure_ascii=False)
    for private in ('测试甲','synthetic-person-a',call[0]['request_id'],call[0]['pcm_sha256']):
        assert private not in serialized


def test_prompt_uses_current_voice_as_data_without_profile_authority():
    note=conversation_address_note({'display_name':'测试乙'})
    assert note['role']=='system' and '测试乙' in note['content']
    assert '本轮' in note['content'] and '个人记忆' in note['content']
    assert conversation_address_note({'display_name':'测试乙','personal_memory_allowed':True}) is None
