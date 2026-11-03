import hashlib,threading
from types import SimpleNamespace
import pytest
from tools.speaker_capture_scope import speaker_capture_scope,begin_speaker_turn,cancel_speaker_turn

def meta(pcm=b'\0\0'*3200,**changes):
    value=dict(protocol='aura-asr-1',board_boot_id='test-boot',session_id='test-session',request_id='test-request',
      generation=1,capture_id='test-capture',sample_count=len(pcm)//2,pcm_sha256=hashlib.sha256(pcm).hexdigest(),budget_ms=60000)
    return dict(value,**changes)
class Tracker:
    def __init__(self):self.rows=[];self.cancelled=[]
    def begin(self,owner,cid,pcm,**kwargs):self.rows.append((dict(owner),cid,pcm,kwargs));return True
    def cancel(self,owner):self.cancelled.append(owner);return True
def model():return SimpleNamespace(speaker_turns=Tracker(),speaker_capture_local=threading.local())

def test_valid_pcm_handed_to_exact_original_turn_then_released():
    m=model();pcm=b'\0\0'*3200;owner=meta(pcm);cid='a'*32
    with speaker_capture_scope(m,owner,pcm,cid,deadline=123):
        assert begin_speaker_turn(m,owner,cid)
        assert m.speaker_capture_local.current['pcm'] is None
        assert not begin_speaker_turn(m,owner,cid)
    assert m.speaker_capture_local.current is None
    assert m.speaker_turns.rows==[(owner,cid,pcm,dict(visual=None,deadline=123))]

def test_no_conversation_and_legacy_model_do_not_enable_recording():
    pcm=b'\0\0'*3200;m=model()
    with speaker_capture_scope(m,meta(pcm),pcm,None):assert not begin_speaker_turn(m,meta(pcm),'a'*32)
    with speaker_capture_scope(SimpleNamespace(),meta(pcm),pcm,'a'*32):pass
    assert not m.speaker_turns.rows

@pytest.mark.parametrize('field,value',[('request_id','different-request'),('capture_id','different-capture'),('generation',2),('pcm_sha256','b'*64)])
def test_other_recording_cannot_receive_current_pcm(field,value):
    m=model();pcm=b'\0\0'*3200;owner=meta(pcm)
    with speaker_capture_scope(m,owner,pcm,'a'*32):
        with pytest.raises(ValueError):begin_speaker_turn(m,dict(owner,**{field:value}),'a'*32)
    assert not m.speaker_turns.rows

@pytest.mark.parametrize('headers',[['invalid-base64'],['bad-one','bad-two']])
def test_malformed_or_duplicate_visual_header_keeps_ordinary_speech(headers):
    m=model();pcm=b'\0\0'*3200;owner=meta(pcm)
    with speaker_capture_scope(m,owner,pcm,'a'*32,headers):assert begin_speaker_turn(m,owner,'a'*32)
    assert m.speaker_turns.rows[0][3]['visual'] is None
    assert m.speaker_visual_invalid_headers==1

def test_failed_reply_releases_capture_without_submitting_identity():
    m=model();pcm=b'\0\0'*3200
    with pytest.raises(RuntimeError):
        with speaker_capture_scope(m,meta(pcm),pcm,'a'*32):raise RuntimeError('reply preparation failed')
    assert m.speaker_capture_local.current is None and not m.speaker_turns.rows

def test_cancellation_is_forwarded_with_original_context():
    m=model();owner=meta();assert cancel_speaker_turn(m,owner)
    assert m.speaker_turns.cancelled==[owner]
    assert not cancel_speaker_turn(SimpleNamespace(),owner)

def test_concurrent_handlers_keep_pcm_thread_local():
    m=model();barrier=threading.Barrier(2);errors=[]
    def run(number):
        try:
            pcm=bytes([number,0])*3200;owner=meta(pcm,request_id='req-'+str(number),capture_id='cap-'+str(number))
            with speaker_capture_scope(m,owner,pcm,str(number)*32):
                barrier.wait(timeout=1);assert begin_speaker_turn(m,owner,str(number)*32)
        except Exception as e:errors.append(e)
    threads=[threading.Thread(target=run,args=(i,)) for i in (1,2)]
    for t in threads:t.start()
    for t in threads:t.join(timeout=2)
    assert not errors and len(m.speaker_turns.rows)==2
    assert all(row[0]['pcm_sha256']==hashlib.sha256(row[2]).hexdigest() for row in m.speaker_turns.rows)
