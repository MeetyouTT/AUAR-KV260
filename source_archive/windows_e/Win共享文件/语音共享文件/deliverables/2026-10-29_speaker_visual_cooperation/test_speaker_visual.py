import bootstrap
import copy,json,threading
import pytest
from common.speaker_visual import build_visual,encode_visual_header,decode_visual_header,validate_visual,unavailable
from test_helpers import meta,snapshot

def test_same_face_is_only_independent_observation_without_names_or_image():
    owner=meta();result=build_visual(snapshot(1000,10),snapshot(4000,40),owner,4050)
    assert result['state']=='FACE_AT_CAPTURE_BOUNDARIES'
    assert result['evidence']['face_identity_id']=='face-one'
    assert result['reason']=='NOT_ACTIVE_SPEAKER_PROOF'
    raw=json.dumps(result,ensure_ascii=False)
    assert '公开测试姓名' not in raw and 'display_name' not in raw and 'jpeg' not in raw and 'embedding' not in raw
    assert decode_visual_header(encode_visual_header(result,owner),owner)==result

@pytest.mark.parametrize('mutation,expected',[
 (lambda s:s.update(board_boot_id='other'),'UNAVAILABLE'),
 (lambda s:s.update(service_epoch='restarted'),'UNAVAILABLE'),
 (lambda s:s.update(source_kind='fixture'),'UNAVAILABLE'),
 (lambda s:s['modules']['camera'].update(state='LOST'),'UNAVAILABLE'),
 (lambda s:s['modules']['identity'].update(face_count=2),'UNAVAILABLE'),
 (lambda s:s['modules']['identity'].update(face_target=None,face_count=0),'UNAVAILABLE'),
 (lambda s:s['modules']['identity'].update(db_version=3),'UNAVAILABLE'),
 (lambda s:s['modules']['identity']['face_target'].update(track_generation=4),'UNAVAILABLE'),
 (lambda s:s['modules']['identity'].update(source_mono_ms=50),'UNAVAILABLE'),
 (lambda s:s['modules']['identity'].update(source_frame_id=10),'UNAVAILABLE'),
 (lambda s:s['modules']['identity'].update(person_id='different'),'UNAVAILABLE')])
def test_old_foreign_many_or_changed_faces_are_not_carried(mutation,expected):
    end=snapshot(4000,40);mutation(end)
    result=build_visual(snapshot(1000,10),end,meta(),4050)
    assert result['state']==expected and result['evidence'] is None

def test_no_face_or_invalid_provider_does_not_require_vision_to_talk():
    assert build_visual(None,None,meta(),4050)==unavailable(meta(),'VISUAL_STALE_OR_INVALID')

def test_known_to_unknown_never_carries_prior_face_identity():
    end=snapshot(4000,40);end['modules']['identity'].update(state='UNKNOWN',person_id='',display_name='')
    result=build_visual(snapshot(1000,10),end,meta(),4050)
    assert result['state']=='FACE_AT_CAPTURE_BOUNDARIES' and result['evidence']['face_identity_id'] is None

def test_header_rejects_foreign_context_extra_claims_and_oversize():
    owner=meta();good=build_visual(snapshot(1000,10),snapshot(4000,40),owner,4050)
    with pytest.raises(ValueError):decode_visual_header(encode_visual_header(good,owner),meta(2))
    for extra in ({'personal_memory_allowed':True},{'display_name':'秘密'},{'single_speaker_verified':True}):
        with pytest.raises(ValueError):validate_visual(dict(good,**extra),owner)
    with pytest.raises(ValueError):decode_visual_header('a'*4097,owner)

def test_board_provider_is_in_memory_and_does_not_open_camera(monkeypatch):
    from board.runtime.audio.channel_jobs import ChannelConversationJobs
    from board.interaction import ui_contract
    item=ChannelConversationJobs.__new__(ChannelConversationJobs);item.condition=threading.Condition()
    item.capture_owners={'capture-1':snapshot(1000,10)};item.identity_snapshot=lambda:snapshot(4000,40)
    monkeypatch.setattr(ui_contract,'millis',lambda:4050)
    assert item._speaker_visual(meta())['state']=='FACE_AT_CAPTURE_BOUNDARIES'
    item.identity_snapshot=None
    assert item._speaker_visual(meta())['state']=='UNAVAILABLE'
    def broken():raise OSError('Camera provider disconnected')
    item.identity_snapshot=broken
    assert item._speaker_visual(meta())['reason']=='VISUAL_PROVIDER_UNAVAILABLE'

def test_optional_header_is_bounded_and_missing_vision_uses_ordinary_transport(monkeypatch):
    from board.runtime.audio import voice_channel as transport
    class Sock:
        def settimeout(self,*args):pass
        def setsockopt(self,*args):pass
    class Response:
        status=204
        def getheader(self,name):return 'wake-word-v1' if name=='X-Aura-Entry' else None
        def read(self,*args):return b''
    class Connection:
        def __init__(self,*args,**kwargs):self.sock=Sock();self.headers=None
        def request(self,method,url,body,headers):self.headers=headers
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr(transport.http.client,'HTTPConnection',Connection)
    monkeypatch.setattr(transport.select,'select',lambda *args:([],[],[]))
    from test_helpers import pcm,CID
    for visual in (None,unavailable(meta())):
        client=transport.VoiceChannel('wired')
        result=client.exchange(meta(),pcm(),lambda *args:None,conversation=CID,wake_entry=True,speaker_visual=visual)
        assert result['wake_only']
        assert ('X-Aura-Speaker-Visual' in client.connection.headers)==(visual is not None)
        if visual:assert decode_visual_header(client.connection.headers['X-Aura-Speaker-Visual'],meta())==visual
