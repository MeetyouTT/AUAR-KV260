import bootstrap_bridge
import base64,copy,hashlib,json,sqlite3,threading,time
from pathlib import Path
from unittest.mock import Mock
import pytest
from common.face_binding_wire import (validate_packet,packet_sha256,encode_gallery_header,
    decode_gallery_header,validate_binding_request,canonical)
from board.runtime.audio.face_gallery_readback import FaceGalleryReadback
from board.runtime.audio.face_binding_bridge import FaceBindingBridge
from common import voice_enrollment as speech
from test_helpers import meta,snapshot,pcm

NAME='测试小林';ID='1'*32;ATTEMPT='2'*32;MODEL='synthetic-sface-int8';FP='3'*64

def packet(owner=None,current=True,revision=2):
    return dict(version=1,context=owner or meta(),gallery=dict(store_id='gallery-synthetic',model_id=MODEL,revision=revision,source_kind='actual'),
        current=dict(identity_id=ID,template_fingerprint=FP) if current else None,inventory=[[ID,FP]])

def face(now=4000,frame=40,*,known=True,revision=2):
    s=snapshot(now,frame,person=ID);i=s['modules']['identity']
    i.update(backend='DPU_SFACE_INT8',display_name=NAME,people=[dict(person_id=ID,display_name=NAME)],db_version=revision)
    if not known:i.update(state='UNKNOWN',person_id='',display_name='',people=[])
    return s

def request(owner=None,*,known=False,name=NAME):
    owner=owner or meta()
    return dict(version=1,attempt_id=ATTEMPT,origin_context=owner,
        face_guard=dict(service_epoch='camera-service',camera_epoch='camera',target=dict(camera_epoch='camera',track_id=1,track_generation=1),
            gallery_revision=2,face_identity_id=ID if known else None),name=name,board_text='确认登记',confirmed_existing=known)

def test_gallery_codec_exact_owner_digest_and_no_private_payload():
    p=packet();h=encode_gallery_header(p,meta());v=decode_gallery_header(h,meta())
    assert v['packet_sha256']==hashlib.sha256(canonical(p)).hexdigest()==packet_sha256(p)
    assert len(h)<4096 and v['current']==p['current']
    assert not any(key in canonical(p).decode() for key in ('embedding','display_name','photo','personal_memory'))
    with pytest.raises(ValueError):decode_gallery_header(h,meta(2))

@pytest.mark.parametrize('mutate',[
 lambda p:p.update(name=NAME),lambda p:p['gallery'].update(source_kind='fixture'),
 lambda p:p['inventory'].append(p['inventory'][0]),lambda p:p.update(inventory=[['x',FP],[ID,FP]]),
 lambda p:p.update(current={'identity_id':'missing','template_fingerprint':FP}),
 lambda p:p.update(inventory=[[str(i),FP] for i in range(33)]),
 lambda p:p['gallery'].update(revision=True),lambda p:p.update(personal_memory_allowed=True)])
def test_gallery_packet_rejects_untrusted_or_unbounded_metadata(mutate):
    p=packet();mutate(p)
    with pytest.raises(ValueError):validate_packet(p,meta())

def test_name_inquiry_ticket_is_narrow_and_ordinary_name_is_not_enrollment():
    r=request();r.update(attempt_id='name-wait-'+'a'*32,name=None,confirmed_existing=False,board_text='帮我登记身份')
    assert validate_binding_request(r,meta())==r
    r['confirmed_existing']=True
    with pytest.raises(ValueError):validate_binding_request(r,meta())
    assert speech.enrollment_requested('我叫测试小林') is False

def test_binding_request_rejects_foreign_origin_and_unknown_claims():
    r=request();r['origin_context']=meta(2)
    with pytest.raises(ValueError):validate_binding_request(r,meta())
    r=request();r['personal_memory_allowed']=True
    with pytest.raises(ValueError):validate_binding_request(r,meta())

def database(tmp_path,*,model=MODEL):
    path=tmp_path/'faces.sqlite3';db=sqlite3.connect(path)
    db.executescript('CREATE TABLE identities(id TEXT PRIMARY KEY,name TEXT);CREATE TABLE templates(identity_id TEXT,model_id TEXT,dimension INTEGER,embedding TEXT);'
        'CREATE TABLE metadata(key TEXT PRIMARY KEY,value INTEGER);CREATE TABLE identity_model_binding(model_id TEXT,dimension INTEGER);')
    raw=json.dumps([1.]+[0.]*127)
    db.execute('INSERT INTO identities VALUES(?,?)',(ID,NAME));db.execute('INSERT INTO templates VALUES(?,?,?,?)',(ID,model,128,raw))
    db.execute("INSERT INTO metadata VALUES('revision',2)");db.execute('INSERT INTO identity_model_binding VALUES(?,128)',(model,));db.commit();db.close()
    return path,raw

def reader(path):
    return FaceGalleryReadback(dict(version=1,enabled=True,board_boot_id='boot',database=str(path),model_id=MODEL,dimension=128,backend='DPU_SFACE_INT8'),
        verify=lambda c:None,clock=lambda:4050)

def test_private_gallery_mode_ro_hashes_inside_owner_without_exporting_names_or_vectors(tmp_path):
    path,raw=database(tmp_path);before=path.read_bytes();p=reader(path).read(meta(),face())
    assert p['inventory']==[[ID,hashlib.sha256(raw.encode()).hexdigest()]]
    assert p['current']['identity_id']==ID and path.read_bytes()==before
    assert NAME not in canonical(p).decode() and raw not in canonical(p).decode()

def test_unknown_or_missing_visible_template_keeps_actual_revision_and_complete_inventory(tmp_path):
    path,_=database(tmp_path);s=face(known=False);s['modules']['identity']['people']=[dict(person_id=ID,display_name=NAME)]
    assert reader(path).read(meta(),s)['current'] is None
    s=face();s['modules']['identity']['person_id']='missing'
    p=reader(path).read(meta(),s)
    assert p['gallery']['revision']==2 and p['current'] is None and len(p['inventory'])==1

def test_private_readback_rejects_wrong_model_backend_and_revision_without_creating_db(tmp_path):
    path,_=database(tmp_path,model='old-cpu')
    with pytest.raises(ValueError):reader(path).read(meta(),face())
    missing=tmp_path/'not-created.sqlite3'
    with pytest.raises(ValueError):reader(missing).read(meta(),face())
    assert not missing.exists()

def test_sqlite_lock_has_small_bound_and_keeps_voice_fallback_possible(tmp_path):
    path,_=database(tmp_path);db=sqlite3.connect(path);db.execute('BEGIN EXCLUSIVE')
    started=time.monotonic()
    try:
        with pytest.raises(ValueError):reader(path).read(meta(),face())
        assert time.monotonic()-started<.3
    finally:db.rollback();db.close()

def command(before):
    return dict(protocol_version='aura-ui-1',board_boot_id='boot',service_epoch=before['service_epoch'],command_id='voice-command',
        ui_epoch='voice-flow',ui_generation=0,context=before['context'],snapshot_sequence=before['sequence'],issued_mono_ms=4000,deadline_mono_ms=6500,
        action='identity_enroll',params=dict(target=before['modules']['identity']['face_target'],display_name=NAME,confirmed=True))

def ack(cmd,accepted=True):
    return dict({k:cmd[k] for k in ('protocol_version','board_boot_id','service_epoch','command_id','ui_epoch','ui_generation')},
        accepted=accepted,detail='synthetic command ACK')

def committed(before):
    after=face(4100,41,revision=3);after['modules']['identity']['last_operation']=dict(command_id='voice-command',action='identity_enroll',
        state='COMMITTED',db_version=3,detail='synthetic committed')
    return after

def setup_commit(*,accepted=True,state='COMMITTED',text='确认登记',current=lambda:True):
    before=face(known=False);after=committed(before);after['modules']['identity']['last_operation']['state']=state
    fake=Mock();fake.read.return_value=packet(revision=3)
    bridge=FaceBindingBridge(lambda:after,lambda cmd:ack(cmd,accepted),fake,clock=lambda:4150)
    exchange=bridge.exchange(meta(),request(),before,text,current)
    with bridge.scope(exchange):
        exchange.snapshot(before);bridge.command(command(before))
    return bridge,exchange,after

def test_real_commit_ack_revision_and_unique_original_id_create_payload():
    bridge,exchange,after=setup_commit()
    payload=exchange.receipt(speech.result('registered'),lambda:after)
    assert payload['state']=='COMMITTED' and payload['identity_id']==ID and payload['template_fingerprint']==FP
    assert payload['origin_context']==payload['commit_context']==meta() and payload['face_guard']==request()['face_guard']
    assert payload['checks']['single_speaker_verified'] is False
    assert exchange.receipt(speech.result('registered'),lambda:after) is None

@pytest.mark.parametrize('accepted,state',[(False,'COMMITTED'),(True,'PENDING'),(True,'REJECTED')])
def test_spoken_registered_without_original_committed_evidence_never_gets_receipt(accepted,state):
    bridge,exchange,after=setup_commit(accepted=accepted,state=state)
    assert exchange.receipt(speech.result('registered'),lambda:after) is None

def test_explicit_asr_confirmation_not_host_board_text_alone_is_required():
    with pytest.raises(ValueError):setup_commit(text='随便聊聊')

def test_commit_revision_or_id_change_rejects_receipt():
    bridge,exchange,after=setup_commit();bridge.readback.read.return_value=packet(revision=4)
    with pytest.raises(ValueError):exchange.receipt(speech.result('registered'),lambda:after)

def test_cancelled_exchange_does_not_forward_command_or_return_late_receipt():
    current=[True];bridge,exchange,after=setup_commit(current=lambda:current[0]);current[0]=False
    with pytest.raises(InterruptedError):exchange.receipt(speech.result('registered'),lambda:after)

def test_existing_known_requires_fresh_same_face_and_actual_confirmation():
    s=face();fake=Mock();fake.config={'result_ttl_ms':3000};fake.read.return_value=packet();bridge=FaceBindingBridge(lambda:s,Mock(),fake,clock=lambda:4050)
    exchange=bridge.exchange(meta(),request(known=True),s,'确认登记',lambda:True)
    p=exchange.receipt(speech.result('already_known'),lambda:s)
    assert p['state']=='EXISTING_CONFIRMED' and p['revision_before']==p['revision_after']==2
    stale=copy.deepcopy(s);stale['modules']['identity']['source_mono_ms']=1
    exchange=bridge.exchange(meta(),request(known=True),stale,'确认登记',lambda:True)
    with pytest.raises(ValueError):exchange.receipt(speech.result('already_known'),lambda:s)

def test_existing_known_does_not_bind_first_already_known_prompt():
    s=face();fake=Mock();bridge=FaceBindingBridge(lambda:s,Mock(),fake,clock=lambda:4050)
    r=request(known=True);r['confirmed_existing']=False
    ex=bridge.exchange(meta(),r,s,'记住我，我叫测试小林',lambda:True)
    assert ex.receipt(speech.result('already_known'),lambda:s) is None and fake.read.call_count==0

@pytest.mark.parametrize('mutation',[
 lambda s:s['modules']['camera'].update(state='LOST'),
 lambda s:s['modules']['identity'].update(person_id='other'),
 lambda s:s['modules']['identity'].update(db_version=3),
 lambda s:s.update(service_epoch='restarted'),
 lambda s:s['modules']['identity'].update(target=dict(camera_epoch='camera',track_id=2,track_generation=1))])
def test_existing_receipt_rejects_changed_independent_face_evidence(mutation):
    s=face();changed=copy.deepcopy(s);mutation(changed);fake=Mock();fake.config={'result_ttl_ms':3000}
    bridge=FaceBindingBridge(lambda:changed,Mock(),fake,clock=lambda:4050)
    ex=bridge.exchange(meta(),request(known=True),s,'确认登记',lambda:True)
    with pytest.raises(ValueError):ex.receipt(speech.result('already_known'),lambda:changed)

def test_original_ack_for_another_command_is_never_a_binding_commit():
    before=face(known=False);after=committed(before)
    def wrong(cmd):
        value=ack(cmd);value['command_id']='another-command';return value
    bridge=FaceBindingBridge(lambda:after,wrong,Mock(),clock=lambda:4150)
    ex=bridge.exchange(meta(),request(),before,'确认登记',lambda:True)
    with bridge.scope(ex):
        ex.snapshot(before)
        with pytest.raises(ValueError):bridge.command(command(before))
    assert ex.receipt(speech.result('registered'),lambda:after) is None

def test_original_fsm_is_preserved_and_real_command_is_observed_only_at_confirm():
    from board.identity.voice_enrollment import VoiceEnrollment
    before=face(known=False);latest=[before];calls=[];fake=Mock();fake.read.return_value=packet(revision=3)
    before['capabilities']['identity_enroll']=True
    def send(cmd):
        calls.append(cmd);latest[0]=committed(before)
        latest[0]['modules']['identity']['last_operation']['command_id']=cmd['command_id']
        return ack(cmd)
    bridge=FaceBindingBridge(lambda:latest[0],send,fake,clock=lambda:4150)
    flow=VoiceEnrollment('boot',bridge.snapshot,bridge.command,now_ms=lambda:4150,simple=True)
    assert flow.handle('帮我登记身份',before)['code']=='ask_name'
    assert flow.handle('我叫'+NAME,before)['code']=='confirm_name'
    assert calls==[]
    ex=bridge.exchange(meta(),request(),before,'确认登记',lambda:True)
    with bridge.scope(ex):reply=flow.handle('确认登记',before)
    assert reply['code']=='registered' and len(calls)==1
    assert ex.receipt(reply,lambda:latest[0])['identity_id']==ID

def test_bridge_thread_scopes_never_assign_commit_to_new_exchange():
    bridge,old,after=setup_commit();other=bridge.exchange(meta(2),request(),face(known=False),'确认登记',lambda:True)
    assert other.receipt(speech.result('registered'),lambda:after) is None
    assert old.receipt(speech.result('registered'),lambda:after)['commit_context']==meta()

def test_gallery_transport_ack_owner_and_receipt_stay_in_original_token(monkeypatch):
    from board.runtime.audio import voice_channel as transport
    calls=[]
    class Response:
        status=200
        def read(self,*args):return canonical({'accepted':True,'packet_sha256':packet_sha256(packet())})
    class Connection:
        def __init__(self,*args,**kwargs):pass
        def request(self,*args):calls.append(args)
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr(transport.http.client,'HTTPConnection',Connection)
    client=transport.VoiceChannel('wired')
    assert client.submit_face_gallery(meta(),packet()) is True
    assert json.loads(calls[0][2])=={'context':meta(),'packet':packet()}
    assert calls[0][1]=='/v1/voice/identity/gallery'
    with pytest.raises(ValueError):client.identity_result(meta(),'a'*48,speech.result('sample_auto'),final=False,binding_receipt={'fake':True})

def test_transport_enforces_actual_identity_result_body_bytes_without_truncation(monkeypatch):
    from board.runtime.audio import voice_channel as transport
    sent=[]
    class Response:
        status=200
        def read(self,*args):return b'{"accepted":true}'
    class Connection:
        def __init__(self,*args,**kwargs):pass
        def request(self,*args):sent.append(args)
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr(transport.http.client,'HTTPConnection',Connection)
    client=transport.VoiceChannel('wired');bridge,ex,after=setup_commit();receipt=ex.receipt(speech.result('registered'),lambda:after)
    client.identity_result(meta(),'a'*48,speech.result('registered'),binding_receipt=receipt)
    assert len(sent[-1][2])<=4096 and json.loads(sent[-1][2])['binding_receipt']==receipt
    client.identity_result(meta(),'a'*48,speech.result('registered'),binding_receipt={'oversized':'大'*5000})
    body=json.loads(sent[-1][2]);assert len(sent[-1][2])<=4096 and 'binding_receipt' not in body
    assert body['reply']==speech.result('registered') and body['token']=='a'*48 and body['context']==meta()
