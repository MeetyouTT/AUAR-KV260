import bootstrap
import copy,hashlib,json,threading,time
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from tools.device_hub import Hub
from tools.binding_model_adapter import BindingModelAdapter,accept_model_result,prepare_channel
from tools.enrollment_receipts import face_commit_payload
from common.face_binding_wire import packet_sha256,encode_gallery_header
from test_identity_binding import Encoder,meta,pcm,visual,quality,FACE

CONFIG=dict(enabled=True,threshold=.9,margin=.1,retention_seconds=86400,max_clusters=32)
def packet(owner,*,revision=0,identity=None,fingerprint='f'*64,inventory=None):
    if inventory is None:inventory=[] if identity is None else [[identity,fingerprint]]
    return dict(version=1,context=owner,gallery=dict(FACE,revision=revision,source_kind='actual'),
      current=None if identity is None else dict(identity_id=identity,template_fingerprint=fingerprint),inventory=inventory)
def wait(predicate):
    until=time.monotonic()+3
    while time.monotonic()<until:
        value=predicate()
        if value:return value
        time.sleep(.005)
    raise AssertionError('Bounded Hub initialization did not complete')
def speaker_snapshot(hub):
    return hub.speaker_pool.submit(lambda:dict(revision=hub.speaker.store.revision,people=hub.speaker.store.people())).result()
@pytest.fixture
def hub(tmp_path):
    encoder=Encoder();value=Hub(tmp_path/'private',tmp_path/'NO_MODEL',anonymous_config=CONFIG,
      encoder_factory=lambda _:encoder,private_root_validator=lambda root:root)
    wait(lambda:value.binding is not None or value.binding_error not in ('disabled',''))
    assert value.binding is not None,value.binding_error
    value.speaker_pool.submit(lambda:setattr(value.progressive_speaker,'quality',quality)).result()
    yield value
    value.speaker_pool.shutdown(wait=True,cancel_futures=True)
def adapter(hub):
    return BindingModelAdapter(call=lambda path,value,timeout=12:hub.binding_call(path,copy.deepcopy(value)))
def route(hub,owner,utterance,*,revision=0,identity=None):
    bridge=adapter(hub);p=packet(owner,revision=revision,identity=identity)
    assert bridge.accept_gallery(dict(context=owner,packet=p))==dict(accepted=True,packet_sha256=packet_sha256(p))
    return bridge,bridge.before_device(owner,utterance,pcm(owner['generation']),visual=visual(owner,revision=revision,person=identity),
      gallery_headers=[encode_gallery_header(p,owner)])
def consume(models,exchange,owner,reply,receipt=None,*,sequence=0,final=True):
    models.latest_generations[(owner['board_boot_id'],owner['session_id'])]=owner['generation']
    models.identity_exchanges[owner['request_id']]=exchange
    value=dict(context=owner,token=exchange.token,reply=reply,sequence=sequence,final=final)
    if receipt is not None:value['binding_receipt']=receipt
    return accept_model_result(models,value)
def activate(hub):
    models=SimpleNamespace(meta_lock=threading.RLock(),latest_generations={},identity_exchanges={})
    bridge,first=route(hub,meta(1),'记住我，我叫小明')
    exchange=bridge.open_exchange(meta(1),pcm(1),first,timeout=10)
    assert first['decision']['reply'] is None and exchange.binding_request['board_text']=='帮我登记身份，我叫小明'
    consume(models,exchange,meta(1),dict(code='prepare_name',name='小明'))
    assert '两部分' in ''.join(row[1] for row in exchange if row[0]=='text')
    assert exchange.pcm_holder['pcm'] is None
    bridge,confirmation=route(hub,meta(2),'确认登记')
    exchange=bridge.open_exchange(meta(2),pcm(2),confirmation,timeout=10)
    binding=confirmation['binding_request']
    command=dict(action='identity_enroll',board_boot_id='boot',params=dict(confirmed=True,display_name='小明'))
    ack=dict(accepted=True,command_id='original-face-operation')
    after=dict(db_version=1,people=[dict(person_id='face-identity',display_name='小明')],
      last_operation=dict(command_id=ack['command_id'],action='identity_enroll',state='COMMITTED',db_version=1,detail='saved'))
    receipt=face_commit_payload(attempt_id=binding['attempt_id'],origin=binding['origin_context'],commit=meta(2),
      face_guard=binding['face_guard'],gallery=FACE,name='小明',command=command,ack=ack,before=dict(db_version=0,people=[]),after=after,template_fingerprint='f'*64)
    consume(models,exchange,meta(2),dict(code='sample_auto',name=''),sequence=0,final=False)
    consume(models,exchange,meta(2),dict(code='registered',name=''),receipt,sequence=1)
    with patch('tools.speaker_device.voiced_pcm',quality):
        text=''.join(row[1] for row in exchange if row[0]=='text')
        assert '接下来' in text and hub.speaker.state(meta(2))['active']
        for i in (3,4,5):
            _,result=route(hub,meta(i),'公开合成测试句子'+str(i),revision=1,identity='face-identity')
            assert result['decision']['route']=='device_reply' and not result['decision']['unified_saved']
            evidence=hub.analysis_submit(meta(i),pcm(i),'a'*32,visual(meta(i),revision=1,person='face-identity'))
            assert evidence['status']=='COMPLETE' and evidence['anonymous']['code']=='a1'
        _,result=route(hub,meta(6),'确认保存身份关联',revision=1,identity='face-identity')
    assert result['decision']['unified_saved'] and hub.speaker.encoder.calls==3
    assert hub.binding.registry.health()['active_people']==1
    with hub.binding.registry._db() as db:person=db.execute("SELECT person_id FROM linked_people WHERE state='ACTIVE'").fetchone()[0]
    return person

def test_typed_actual_hub_runs_one_registration_intent_and_one_encoder_per_sample(hub):
    activate(hub)
    assert speaker_snapshot(hub)['revision']==1 and not hub.speaker.calibrated
    assert len((hub.root/'identity-link-receipt.key').read_bytes())==32
    assert not list(hub.root.rglob('*.wav')) and not list(hub.root.rglob('*.pcm'))

def test_ordinary_chat_uses_existing_tracker_once_and_no_face_is_needed(hub):
    activate(hub);owner=meta(7);bridge=adapter(hub)
    routed=bridge.before_device(owner,'今天聊点什么',pcm(7))
    assert routed['decision']['route']=='ordinary' and routed['analysis_mode']=='TRACKER' and hub.speaker.encoder.calls==3
    hub.analysis_submit(owner,pcm(7),'a'*32,None)
    result=wait(lambda:(value if (value:=hub.speaker_turns.result(owner,'a'*32))['status']!='PENDING' else None))
    assert result['status']=='COMPLETE' and result['identity']['state']=='PROVISIONAL_NAME_CANDIDATE'
    assert hub.speaker.encoder.calls==4 and result['personal_memory_allowed'] is False

def test_explicit_identity_query_uses_single_encoder_and_reuses_tracker_receipt(hub):
    activate(hub);owner=meta(7);routed=adapter(hub).before_device(owner,'我是谁',pcm(7))
    assert routed['decision']['route']=='device_reply' and '可能' in routed['decision']['reply'] and '不能确认' in routed['decision']['reply']
    evidence=hub.analysis_submit(owner,pcm(7),'a'*32,None)
    assert evidence['version']==3 and evidence['identity']['state']=='PROVISIONAL_NAME_CANDIDATE'
    assert hub.speaker.encoder.calls==4 and not hub.speaker.calibrated

def test_original_confirmed_voice_delete_invalidates_only_derived_index(hub):
    activate(hub)
    hub.speaker_call('turn',meta(7),'删除声纹，名字是小明',pcm(7))
    assert hub.binding.registry.health()['active_people']==1
    hub.speaker_call('turn',meta(8),'确认删除声纹',pcm(8))
    snapshot=speaker_snapshot(hub);assert snapshot['revision']==2 and not snapshot['people']
    assert hub.binding.registry.health()['active_people']==0
    with hub.binding.registry._db() as db:
        assert db.execute('SELECT reason FROM binding_invalidations').fetchall()[0][0]=='ORIGINAL_VOICE_DELETED'
        assert db.execute('SELECT count(*) FROM modality_links').fetchone()[0]==2

def test_complete_inventory_invalidates_invisible_deleted_face(hub):
    activate(hub);owner=meta(7);p=packet(owner,revision=2,inventory=[])
    adapter(hub).accept_gallery(dict(context=owner,packet=p))
    assert hub.binding.registry.health()['active_people']==0
    snapshot=speaker_snapshot(hub);assert len(snapshot['people'])==1 and snapshot['revision']==1
    with hub.binding.registry._db() as db:assert db.execute('SELECT reason FROM binding_invalidations').fetchone()[0]=='ORIGINAL_FACE_DELETED'

def test_complete_inventory_invalidates_changed_face_template(hub):
    activate(hub);owner=meta(7);p=packet(owner,revision=2,identity='face-identity',fingerprint='e'*64)
    adapter(hub).accept_gallery(dict(context=owner,packet=p))
    assert hub.binding.registry.health()['active_people']==0 and len(speaker_snapshot(hub)['people'])==1

def test_original_authorization_revocation_hook_retains_original_templates(hub):
    person=activate(hub)
    assert hub.speaker_pool.submit(lambda:hub.binding.revoke_derived_identity(person)).result()
    assert not hub.binding.registry.health()['active_people'] and len(speaker_snapshot(hub)['people'])==1

def test_fake_or_foreign_receipt_cannot_use_scoped_signing_gate(hub):
    bridge,routed=route(hub,meta(1),'记住我，我叫小明');exchange=bridge.open_exchange(meta(1),pcm(1),routed,timeout=10)
    with pytest.raises(ValueError):hub.binding_call('/v1/binding/face-result',dict(context=meta(1),attempt_id=routed['decision']['attempt_id'],
      token=exchange.token,capability='0'*64,pcm=__import__('base64').b64encode(pcm(1)).decode(),reply=dict(code='registered',name=''),binding_receipt={},final=True))
    with pytest.raises(ValueError):hub.binding_call('/v1/binding/sign',dict(payload={}))
    exchange.cancel();assert exchange.pcm_holder['pcm'] is None
    assert not hub.binding.registry.health()['active_people']

def test_registered_text_without_original_receipt_never_starts_voice(hub):
    bridge,routed=route(hub,meta(1),'记住我，我叫小明');exchange=bridge.open_exchange(meta(1),pcm(1),routed,timeout=10)
    exchange.accept(meta(1),exchange.token,dict(code='registered',name=''))
    text=''.join(row[1] for row in exchange if row[0]=='text')
    assert '还没有完成' in text and not hub.speaker.state(meta(1))['active']

def test_old_or_inconsistent_gallery_packet_cannot_invalidate_fresh_state(hub):
    owner=meta(1);p=packet(owner,revision=2)
    adapter(hub).accept_gallery(dict(context=owner,packet=p))
    for value in (packet(meta(2),revision=1),packet(meta(2),revision=2,identity='face-new')):
        with pytest.raises(ValueError):adapter(hub).accept_gallery(dict(context=value['context'],packet=value))

def test_model_adapter_keeps_face_exchange_ahead_of_legacy_device_reply(hub):
    from email.message import Message
    from common.speaker_visual import encode_visual_header
    owner=meta(1);bridge=adapter(hub);p=packet(owner);bridge.accept_gallery(dict(context=owner,packet=p))
    headers=Message();headers['X-Aura-Face-Gallery']=encode_gallery_header(p,owner)
    headers['X-Aura-Speaker-Visual']=encode_visual_header(visual(owner),owner)
    models=SimpleNamespace(binding_adapter=bridge,meta_lock=threading.RLock(),identity_exchanges={},latest_generations={('boot','session'):1})
    with patch('tools.device_client.command',side_effect=AssertionError('Legacy device route must be skipped')):
        reply,exchange,routed=prepare_channel(models,owner,'记住我，我叫小明',pcm(1),headers,timeout=10)
    assert reply is None and exchange is not None and models.identity_exchanges[owner['request_id']] is exchange
    assert exchange.binding_request['attempt_id']==routed['decision']['attempt_id']
    exchange.cancel()

def test_missing_packet_or_broken_visual_does_not_gate_ordinary_chat(hub):
    owner=meta(1);value=adapter(hub).before_device(owner,'今天心情不错',pcm(1),gallery_headers=['broken'])
    assert value['decision']['reply'] is None and value['decision']['route']=='ordinary_skip_speaker'
    assert not hub.speaker.encoder.calls and not hub.speaker.state(owner)['active']

def test_loopback_http_typed_transport_and_body_release_use_original_hub(hub):
    import http.client
    from http.server import ThreadingHTTPServer
    from tools.device_hub import Handler
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.hub=hub
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def transport(path,value,timeout=12,origin=None):
        connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=timeout)
        headers={'Content-Type':'application/json'}
        if origin is not None:headers['Origin']=origin
        try:
            connection.request('POST',path,json.dumps(value).encode(),headers)
            response=connection.getresponse();raw=response.read(16385)
            return response.status,json.loads(raw)
        finally:connection.close()
    try:
        bridge=BindingModelAdapter(call=lambda path,value,timeout=12:transport(path,value,timeout)[1])
        owner=meta(1);p=packet(owner)
        assert bridge.accept_gallery(dict(context=owner,packet=p))['accepted']
        result=bridge.before_device(owner,'记住我，我叫小明',pcm(1),visual=visual(owner),gallery_headers=[encode_gallery_header(p,owner)])
        assert result['decision']['route']=='face_exchange' and not hub.speaker.encoder.calls
        assert transport('/v1/binding/state',dict(context=owner),origin='http://outside')[0]==403
        assert transport('/v1/binding/sign',dict(payload={}))[0]==400
    finally:server.shutdown();server.server_close();thread.join(timeout=1)

def test_model_result_keeps_original_4096_bound_and_full_commit_is_small(hub):
    models=SimpleNamespace(meta_lock=threading.RLock(),identity_exchanges={},latest_generations={})
    with pytest.raises(ValueError,match='original bound'):
        accept_model_result(models,dict(context=meta(1),token='0'*48,reply=dict(code='registered',name=''),sequence=0,final=True,binding_receipt=dict(too_large='x'*5000)))
    # The complete original receipt used by the full-path fixture, including
    # origin, commit, guard and names, fits well under the unchanged route bound.
    before=packet(meta(1));assert len(json.dumps(dict(context=meta(1),packet=before)).encode())<24576
    activate(hub)
    with hub.binding.registry._db() as db:
        value=json.loads(db.execute('SELECT face_receipt FROM binding_attempts').fetchone()[0])
    envelope=dict(context=meta(2),token='0'*48,reply=dict(code='registered',name=''),sequence=1,final=True,binding_receipt=value)
    assert len(json.dumps(envelope,ensure_ascii=False).encode())<4096

def test_derived_expiry_clears_original_voice_session_before_returning_to_legacy(hub):
    bridge,first=route(hub,meta(1),'记住我，我叫小明');attempt=first['decision']['attempt_id']
    route(hub,meta(2),'确认登记')
    def original_voice_stage():
        row=hub.binding.registry.attempt(attempt,meta(2));hub.binding.speaker.start(meta(2),pcm(2),attempt_id=attempt,origin=meta(1),name='小明',
          gallery=json.loads(row['voice_gallery']),face_guard=json.loads(row['face_guard']))
        with hub.binding.registry._db(write=True) as db:db.execute("UPDATE binding_attempts SET state='SAMPLING_VOICE',expires=? WHERE attempt_id=?",(time.time()-1,attempt))
    hub.speaker_pool.submit(original_voice_stage).result()
    assert hub.speaker.state(meta(2))['active']
    result=adapter(hub).before_device(meta(3),'继续普通聊天',pcm(3))
    assert result['decision']['route']=='ordinary_skip_speaker' and not hub.speaker.state(meta(3))['active']
    assert not hub.binding.speaker.sessions

def test_private_key_survives_restart_and_rejects_source_tree_as_production_root(tmp_path):
    from tools.binding_hub_runtime import private_key,production_private_root
    root=tmp_path/'private';root.mkdir();first=private_key(root)
    assert len(first)==32 and private_key(root)==first
    with pytest.raises(ValueError):production_private_root(tmp_path)

def test_gallery_digest_and_receipt_owner_cannot_be_mixed_between_captures(hub):
    bridge=adapter(hub);p=packet(meta(1));bridge.accept_gallery(dict(context=meta(1),packet=p))
    result=bridge.before_device(meta(2),'今天聊什么',pcm(2),visual=visual(meta(2)),gallery_headers=[encode_gallery_header(p,meta(1))])
    assert result['decision']['route']=='ordinary_skip_speaker' and result['decision']['reply'] is None
    assert not hub.speaker.encoder.calls and not hub.binding.registry.health()['active_people']
