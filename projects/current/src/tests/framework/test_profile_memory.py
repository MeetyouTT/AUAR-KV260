"""Synthetic profiles only: isolation, durable facts and revocation barriers."""
import io
import json
import sqlite3
import threading
from unittest.mock import patch

import pytest

from common.profile_access import ProfileAccess,ProfileGrant
from common.profile_memory import ProfileConversationStore
from common.voice_channel import read_frame
from common.conversation_store import ConversationStore
from tools.profile_control import validate_request
from tools.voice_channel_source import channel_frames
from tests.framework.test_long_conversation import host,DIGEST
from tests.framework.test_voice_channel import owner,PCM,VoiceChannelTests

CID='a'*32
OTHER='b'*32
THIRD='c'*32
KEY='9'*64


@pytest.fixture
def store(tmp_path):
    return ProfileConversationStore(tmp_path/'profiles.sqlite3')


def command(store,pid,n,text,*,cid=CID):
    meta=owner('profile-command-'+str(n),n)
    store.begin(cid,meta,text,text,profile=pid)
    return meta,store.memory_command(meta,text,profile=pid)


def prepared(tmp_path):
    model=host(tmp_path)
    model.conversations=ProfileConversationStore(tmp_path/'conversations.sqlite3')
    model.profile_access=ProfileAccess(KEY)
    model.profile_turns={};model.lock=threading.Lock();model.latency_options={}
    model.voice=VoiceChannelTests().fixture_models(tmp_path).voice
    pid=model.conversations.create_profile('Synthetic A',consent=True)
    meta=owner('profile-main',1)
    token,_=model.profile_access.issue(pid,meta)
    return model,pid,meta,token


def test_new_session_and_reopened_store_recall_only_explicit_personal_fact(store):
    pid=store.create_profile('Synthetic A',consent=True)
    command(store,pid,1,'记住：项目=海风')
    fresh=owner('new-session',1);fresh['session_id']='new-session'
    reopened=ProfileConversationStore(store.path)
    reopened.begin(OTHER,fresh,'项目叫什么','项目叫什么',profile=pid)
    records,facts=reopened.context_snapshot(OTHER,exclude=fresh['request_id'],profile=pid)
    assert records==[] and [(f['key'],f['value'],f['scope']) for f in facts]==[('项目','海风','personal')]
    assert '海风' not in json.dumps(reopened.context_snapshot(THIRD),ensure_ascii=False)


@pytest.mark.parametrize('profile_mode',['guest','other'])
def test_guest_or_other_profile_cannot_read_or_submit_to_owned_conversation(store,profile_mode):
    pid=store.create_profile('A',consent=True);command(store,pid,1,'记住：项目=独立事实')
    wrong=None if profile_mode=='guest' else store.create_profile('B',consent=True)
    for read in (store.records,store.facts,store.context_snapshot,store.check_scope):
        with pytest.raises(PermissionError):read(CID,profile=wrong)
    with pytest.raises(PermissionError):store.begin(CID,owner('intruder',2),'问题','问题',profile=wrong)
    with sqlite3.connect(store.path) as db:assert db.execute("SELECT count(*) FROM turns WHERE request_id='intruder'").fetchone()[0]==0


def test_existing_anonymous_conversation_is_never_automatically_adopted(store):
    store.begin(CID,owner('anonymous',1),'旧匿名原话','旧匿名原话')
    pid=store.create_profile('A',consent=True)
    with pytest.raises(PermissionError):store.begin(CID,owner('adopt',2),'继续','继续',profile=pid)
    assert store.records(CID)[0]['user']=='旧匿名原话'
    with sqlite3.connect(store.path) as db:assert db.execute('SELECT count(*) FROM conversation_profiles').fetchone()[0]==0


def test_personal_correction_and_forget_suppress_old_sources_across_owned_sessions(store):
    pid=store.create_profile('A',consent=True)
    command(store,pid,1,'记住：项目=海风')
    m=owner('old-explanation',2);store.begin(CID,m,'继续说明','继续说明',profile=pid)
    store.generated(m,'海风的建议。',480,DIGEST);store.played(m,480,DIGEST)
    command(store,pid,3,'更正记忆：项目=晨光',cid=OTHER)
    history,facts=store.context_snapshot(CID,profile=pid)
    assert '海风' not in json.dumps([history,facts],ensure_ascii=False)
    assert facts[0]['value']=='晨光'
    command(store,pid,4,'忘记我的项目',cid=OTHER)
    assert store.context_snapshot(CID,profile=pid)==([],[])
    with sqlite3.connect(store.path) as db:
        assert '海风' in str(db.execute('SELECT user,assistant FROM turns').fetchall())
        assert '海风' not in str(db.execute('SELECT * FROM profile_changes').fetchall())
        assert '晨光' not in str(db.execute('SELECT * FROM recall_exclusions').fetchall())


def test_personal_clear_keeps_other_profile_and_anonymous_memory(store):
    a=store.create_profile('A',consent=True);b=store.create_profile('B',consent=True)
    command(store,a,1,'记住：项目=A项目')
    command(store,b,2,'记住：项目=B项目',cid=OTHER)
    command(store,None,3,'记住：项目=访客项目',cid=THIRD)
    command(store,a,4,'清空我的长期记忆')
    assert store.context_snapshot(CID,profile=a)==([],[])
    assert store.facts(OTHER,profile=b)[0]['value']=='B项目'
    assert store.facts(THIRD)[0]['value']=='访客项目'


def test_clear_current_conversation_preserves_authorized_personal_facts(store):
    pid=store.create_profile('A',consent=True)
    command(store,pid,1,'记住：项目=海风')
    command(store,pid,2,'记住本次对话：阶段=开发')
    assert len(store.facts(CID,profile=pid))==2
    command(store,pid,3,'清空本次对话记忆')
    assert [(f['key'],f['value']) for f in store.facts(CID,profile=pid)]==[('项目','海风')]


def test_personal_update_removes_stale_conversation_override(store):
    pid=store.create_profile('A',consent=True)
    command(store,pid,1,'记住本次对话：项目=旧项目')
    command(store,pid,2,'记住：项目=新项目',cid=OTHER)
    assert [(f['key'],f['value']) for f in store.facts(CID,profile=pid)]==[('项目','新项目')]


@pytest.mark.parametrize('completion',['generated','played'])
def test_cross_connection_personal_change_rejects_old_generation_or_ack(store,completion):
    pid=store.create_profile('A',consent=True)
    old=owner('old',1);store.begin(CID,old,'旧请求','旧请求',profile=pid)
    if completion=='played':store.generated(old,'旧答案',480,DIGEST)
    second=ProfileConversationStore(store.path)
    command(second,pid,2,'记住：项目=新值',cid=OTHER)
    with pytest.raises(ValueError,match='Personal memory changed'):
        if completion=='generated':store.generated(old,'迟到答案',480,DIGEST)
        else:store.played(old,480,DIGEST)
    with sqlite3.connect(store.path) as db:
        row=db.execute("SELECT status,assistant FROM turns WHERE request_id='old'").fetchone()
        assert row[0]!='played'
        if completion=='generated':assert row[1] is None


def test_unselected_guest_personal_request_never_mutates_personal_facts(store):
    meta,reply=command(store,None,1,'长期记住：项目=不应保存')
    assert '选择个人档案' in reply and store.context_snapshot(CID)==([],[])
    with sqlite3.connect(store.path) as db:assert db.execute('SELECT count(*) FROM profile_facts').fetchone()[0]==0


def test_profile_consent_and_fact_capacity_are_explicit(store):
    with pytest.raises(ValueError):store.create_profile('A')
    pid=store.create_profile('A',consent=True)
    for n in range(1,13):command(store,pid,n,'记住：事项%d=值%d'%(n,n))
    _,reply=command(store,pid,13,'记住：事项13=未写入')
    assert '12项' in reply and len(store.facts(CID,profile=pid))==12


def test_ordinary_chat_does_not_create_personal_fact(store):
    pid=store.create_profile('A',consent=True)
    _,reply=command(store,pid,1,'如果我说记住项目是海风，会怎样？')
    assert reply is None and store.facts(CID,profile=pid)==[]


def test_legacy_schema_history_remains_anonymous_after_additive_upgrade(tmp_path):
    path=tmp_path/'legacy.sqlite3';old=ConversationStore(path)
    old.begin(CID,owner('legacy',1),'旧原话','旧原话')
    upgraded=ProfileConversationStore(path)
    assert upgraded.records(CID)[0]['user']=='旧原话'
    assert upgraded.health()['personal_identity_memory'] is True


def test_grants_expire_revoke_and_cannot_be_forged_or_reused_for_another_actor():
    now=[1.];access=ProfileAccess(KEY,clock=lambda:now[0]);meta=owner('q',1)
    token,grant=access.issue('a'*32,meta,ttl=30)
    assert access.resolve(token,meta) is grant
    with pytest.raises(PermissionError):access.resolve(token,dict(meta,session_id='other'))
    with pytest.raises(PermissionError):
        with access.use(ProfileGrant(grant.profile_id,grant.actor,grant.nonce,grant.until)):pass
    now[0]=31
    with pytest.raises(PermissionError):access.resolve(token,meta)
    now[0]=32;fresh,new=access.issue('b'*32,meta,ttl=30)
    with pytest.raises(PermissionError):
        with access.use(grant):pass
    access.revoke(meta)
    with pytest.raises(PermissionError):access.resolve(fresh,meta)
    with pytest.raises(PermissionError):ProfileAccess(KEY).resolve(token,meta)


@pytest.mark.parametrize('ttl',[0,29,1801,True,float('inf')])
def test_invalid_grant_duration_is_rejected(ttl):
    with pytest.raises(ValueError):ProfileAccess(KEY).issue('a'*32,owner(),ttl=ttl)


def test_restart_requires_reselection_but_context_facts_survive(tmp_path):
    models,pid,meta,token=prepared(tmp_path)
    models.register_stream(meta);models.begin_conversation(meta,CID,'记住：项目=海风','记住：项目=海风',profile_token=token)
    other=host(tmp_path);other.conversations=ProfileConversationStore(models.conversations.path)
    other.profile_access=ProfileAccess(KEY);other.profile_turns={}
    newer=owner('after-restart',2)
    with pytest.raises(PermissionError):validate_request(other,newer,OTHER,token)
    fresh,_=other.profile_access.issue(pid,newer)
    other.register_stream(newer);other.begin_conversation(newer,OTHER,'项目叫什么','项目叫什么',profile_token=fresh)
    history,metrics=other.conversation_context(newer,'项目叫什么')
    assert '海风' in json.dumps(history,ensure_ascii=False)
    assert metrics['explicit_facts']==1


def test_profile_command_pipeline_uses_actual_store_and_keeps_token_out_of_archive(tmp_path):
    model,pid,meta,token=prepared(tmp_path)
    def forbidden(*args,**kwargs):raise AssertionError('Command must not call the LLM')
    packets=list(channel_frames(model,meta,'记住：项目=海风',5,model='fake',host='fake',conversation=CID,
                               profile_token=token,stream_factory=forbidden))
    end=read_frame(io.BytesIO(packets[-1]))[0]
    assert end['kind']=='end' and '长期记忆' in end['reply_text']
    ack={'context':meta,'voice_sample_count':end['sample_count'],'pcm_sha256':end['pcm_sha256']}
    assert model.acknowledge_stream(ack)=={'committed':True}
    assert model.conversations.facts(CID,profile=pid)[0]['value']=='海风'
    with sqlite3.connect(model.conversations.path) as db:
        assert token not in str(db.execute('SELECT * FROM turns').fetchall())


def test_revocation_between_audio_packets_stops_delivery_and_prevents_old_ack(tmp_path):
    model,pid,meta,token=prepared(tmp_path)
    frames=channel_frames(model,meta,'记住：项目=海风',5,model='fake',host='fake',conversation=CID,profile_token=token)
    try:
        for packet in frames:
            if read_frame(io.BytesIO(packet))[0]['kind']=='audio':break
        else:raise AssertionError('No audio packet before revoke')
        model.profile_access.revoke(meta)
        remaining=[read_frame(io.BytesIO(p))[0] for p in frames]
        assert remaining[-1]['kind']=='error'
        assert not any(r['kind']=='audio' for r in remaining)
        assert model.conversations.records(CID,profile=pid)==[]
    finally:frames.close()


def test_switch_profile_invalidates_generated_receipt(tmp_path):
    model,pid,meta,token=prepared(tmp_path)
    model.register_stream(meta);model.begin_conversation(meta,CID,'普通问题','普通问题',profile_token=token)
    model.complete_stream(meta,'普通问题','旧回答',480,DIGEST)
    other=model.conversations.create_profile('B',consent=True)
    model.profile_access.issue(other,meta)
    with pytest.raises(PermissionError):model.acknowledge_stream({'context':meta,'voice_sample_count':480,'pcm_sha256':DIGEST})
    assert model.conversations.records(CID,profile=pid)[0]['status']=='generated'


def test_http_control_and_voice_share_authorization_boundary(tmp_path):
    from tools.asr_server import AsrServer
    from tools.board_model_host import ModelHandler
    from tools.profile_cli import control
    from board.runtime.audio.voice_channel import VoiceChannel
    model,pid,meta,unused=prepared(tmp_path)
    class Engine:
        model_id='fixture';calls=0
        def transcribe(self,pcm):self.calls+=1;return '记住：项目=海风'
    engine=Engine();server=AsrServer(('127.0.0.1',0),engine,handler=ModelHandler);server.models=model
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    channel=VoiceChannel('127.0.0.1',server.server_port)
    try:
        with pytest.raises(RuntimeError):control('127.0.0.1',server.server_port,'0'*64,{'action':'list'})
        chosen=control('127.0.0.1',server.server_port,KEY,{'action':'select','profile_id':pid,
                       'board_boot_id':meta['board_boot_id'],'session_id':meta['session_id']})
        result=channel.exchange(meta,PCM,lambda h,p:None,conversation=chosen['conversation_id'],profile_token=chosen['access_token'])
        assert '长期记忆' in result['reply_text'] and engine.calls==1
        with pytest.raises(RuntimeError,match='403'):
            channel.exchange(owner('guest-attempt',2),PCM,lambda h,p:None,conversation=chosen['conversation_id'])
        assert engine.calls==1
        control('127.0.0.1',server.server_port,KEY,{'action':'guest','board_boot_id':meta['board_boot_id'],'session_id':meta['session_id']})
        with pytest.raises(RuntimeError,match='403'):
            channel.exchange(owner('old-token',3),PCM,lambda h,p:None,conversation=chosen['conversation_id'],profile_token=chosen['access_token'])
        assert engine.calls==1
    finally:channel.close();server.shutdown();server.server_close();thread.join(2)


def test_configured_absolute_credential_path_works_without_launcher_environment(tmp_path,monkeypatch):
    from tools.profile_control import access_from_config
    config=tmp_path/'config';config.mkdir()
    key=tmp_path/'synthetic.key';key.write_text(KEY)
    (config/'profile_access.local.json').write_text(json.dumps({'control_key_file':str(key)}))
    monkeypatch.delenv('LOCALAPPDATA',raising=False)
    access=access_from_config(tmp_path)
    access.authenticate(KEY)
    assert access.health()['configured']


def test_server_verifier_never_requires_private_file_or_accepts_digest_as_credential(tmp_path):
    import hashlib
    from tools.profile_control import access_from_config
    config=tmp_path/'config';config.mkdir()
    digest=hashlib.sha256(KEY.encode()).hexdigest()
    (config/'profile_access.local.json').write_text(json.dumps(
        {'control_key_file':str(tmp_path/'intentionally-unavailable.key'),'control_key_sha256':digest}))
    access=access_from_config(tmp_path)
    access.authenticate(KEY)
    with pytest.raises(PermissionError):access.authenticate(digest)
    assert KEY not in json.dumps(access.health())
