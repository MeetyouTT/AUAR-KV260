"""Source-grounded digests over synthetic data; no real personal records."""
from datetime import datetime,timezone
import json,sqlite3,time
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from common.timeline import query,event_id
from common.timeline_summaries import DigestWorker,build,summary_mode
from common.timeline_conversations import TimelineConversationStore
from common.timeline_observations import TimelineObservationStore
from common.profile_memory import ProfileConversationStore
from test_timeline import NOW,CID,OTHER,THIRD,DIGEST,add,frame
from tests.framework.test_voice_channel import owner

def worker(store,now=NOW):
    return DigestWorker(store.path,store._digest_sources,zone='America/Los_Angeles',clock=lambda:now)
def summaries(store,text='总结昨天聊了什么',*,cid=CID,profile=None,now=NOW,kind='day'):
    with patch('time.time',return_value=now):return store.summary_events(cid,query(text,now=now),profile=profile,kind=kind)

def test_background_daily_and_episode_cache_contains_eligible_sources(tmp_path):
    s=TimelineConversationStore(tmp_path/'s.db')
    add(s,1,'项目是海风',at=NOW-86400,played=True)
    add(s,2,'杯子放左侧',at=NOW-86400+600,played=False)
    w=worker(s);assert w.step()==1
    rows=summaries(s)
    assert rows and rows[0]['source']=='daily_digest' and rows[0]['source_count']==3
    assert '杯子放左侧' in rows[0]['text'] and '已回答：杯子放左侧' not in rows[0]['text']
    assert set(rows[0]['source_events'])=={event_id('user','timeline-1'),event_id('assistant','timeline-1'),event_id('user','timeline-2')}
    assert len(summaries(s,kind='episode'))==2
    assert w.step()==0

def test_current_day_input_does_not_destroy_yesterdays_digest(tmp_path):
    s=TimelineConversationStore(tmp_path/'s.db');add(s,1,'昨天的杯子在左侧',at=NOW-86400)
    w=worker(s);w.step();before=summaries(s)
    add(s,2,'总结昨天聊了什么',at=NOW,generated=False)
    assert summaries(s)==before

def test_unplayed_becomes_eligible_only_after_valid_ack_and_cache_refresh(tmp_path):
    s=TimelineConversationStore(tmp_path/'s.db');m=add(s,1,'问题',at=NOW-86400)
    w=worker(s);w.step();assert summaries(s)[0]['source_count']==1
    with pytest.raises(ValueError):s.played(m,479,DIGEST)
    assert summaries(s)[0]['source_count']==1
    with patch('time.time',return_value=NOW-86400+5):s.played(m,480,DIGEST)
    assert summaries(s)==[]
    w.step();assert summaries(s)[0]['source_count']==2

def test_correction_immediately_removes_digest_and_rejects_inflight_cache_write(tmp_path):
    s=TimelineConversationStore(tmp_path/'s.db');p=s.create_profile('Synthetic',consent=True)
    add(s,1,'项目是海风',profile=p,at=NOW-86400,played=True)
    w=worker(s);w.step();old=w.prepare('c:'+CID)
    assert '海风' in summaries(s,profile=p)[0]['text']
    m=add(s,2,'更正记忆：项目=晨光',profile=p,at=NOW,cid=OTHER,generated=False)
    s.memory_command(m,'更正记忆：项目=晨光',profile=p)
    assert summaries(s,profile=p)==[]
    assert w.commit('c:'+CID,old) is False
    w.step();assert '海风' not in json.dumps(summaries(s,profile=p),ensure_ascii=False)

def test_profile_and_guest_scopes_remain_separate(tmp_path):
    s=TimelineConversationStore(tmp_path/'s.db');a=s.create_profile('A',consent=True);b=s.create_profile('B',consent=True)
    add(s,1,'A私密话题',profile=a,at=NOW-86400)
    add(s,2,'B私密话题',profile=b,cid=OTHER,at=NOW-86400)
    add(s,3,'访客话题',cid=THIRD,at=NOW-86400)
    worker(s).step()
    assert 'B私密' not in json.dumps(summaries(s,profile=a),ensure_ascii=False)
    with pytest.raises(PermissionError):summaries(s)
    assert 'A私密' not in json.dumps(summaries(s,cid=THIRD),ensure_ascii=False)

def test_day_digest_never_expands_an_afternoon_request_to_morning(tmp_path):
    q=query('昨天下午',now=NOW);s=TimelineConversationStore(tmp_path/'s.db')
    add(s,1,'上午内容',at=q['start']-3600);add(s,2,'下午内容',at=q['start']+100)
    worker(s).step()
    assert not summaries(s,'总结昨天下午聊了什么')
    events=s.timeline_events(CID,query('昨天下午聊了什么',now=NOW))
    assert all('下午内容' in r['text'] for r in events)

def test_visual_daily_forget_cascades_and_stale_publish_is_rejected(tmp_path):
    now=[NOW-86400];s=TimelineObservationStore(tmp_path/'s.db',device_id='one',clock=lambda:now[0])
    s.add(frame(1),'左侧可见杯子',now[0]);now[0]=NOW
    w=worker(s);w.step();prepared=w.prepare('v:one')
    q=query('总结昨天看到了什么',now=NOW);assert s.summary_events(q)
    s.forget_timeline(query('昨天',now=NOW))
    assert not s.summary_events(q) and w.commit('v:one',prepared) is False
    with s.lock:assert s.db.execute('SELECT count(*) FROM timeline_digests').fetchone()[0]==0
    s.close()

def test_merged_observation_span_crossing_midnight_invalidates_both_days(tmp_path):
    today=query('今天',now=NOW)['start'];now=[today-5]
    s=TimelineObservationStore(tmp_path/'s.db',device_id='one',clock=lambda:now[0])
    s.add(frame(1),'杯子在左侧',now[0]);now[0]=today+5;s.add(frame(2),'杯子在左侧',now[0])
    w=worker(s);w.step()
    with s.lock:assert s.db.execute("SELECT count(*) FROM timeline_digests WHERE kind='day'").fetchone()[0]==2
    now[0]=today+10;s.add(frame(3),'杯子在左侧',now[0])
    with s.lock:assert s.db.execute('SELECT count(*) FROM timeline_digests').fetchone()[0]==0
    s.close()

def test_summary_retention_never_extends_source_retention(tmp_path):
    now=[NOW];s=TimelineObservationStore(tmp_path/'s.db',device_id='one',clock=lambda:now[0],history_days=1)
    s.add(frame(1),'旧杯子',now[0]);w=DigestWorker(s.path,s._digest_sources,zone='America/Los_Angeles',clock=lambda:now[0],retention_days=1)
    w.step();assert s.summary_events(query('今天',now=now[0]))
    now[0]+=86401
    assert not s.summary_events(query('昨天',now=now[0]))
    s.close()

def test_worker_thread_is_explicit_background_and_closes_cleanly(tmp_path):
    s=TimelineConversationStore(tmp_path/'s.db');add(s,1,'后台内容',at=time.time()-86400)
    s.start_summaries(interval=.02)
    until=time.monotonic()+2
    while time.monotonic()<until and s.digest_worker.completed==0:time.sleep(.01)
    assert s.digest_worker.health()['running'] and s.digest_worker.completed>0
    s.digest_worker.close();assert not s.digest_worker.health()['running']

def test_old_profile_writer_still_works_after_code_rollback(tmp_path):
    path=tmp_path/'s.db';s=TimelineConversationStore(path);add(s,1,'旧输入',at=NOW-86400)
    worker(s).step();assert summaries(s)
    old=ProfileConversationStore(path)
    m=owner('legacy-write',2);old.begin(CID,m,'清空本次对话记忆','清空本次对话记忆')
    old.memory_command(m,'清空本次对话记忆')
    assert summaries(s)==[]
    add(s,3,'新输入',at=NOW);worker(s).step()

def test_source_mutation_during_background_build_is_discarded(tmp_path):
    s=TimelineConversationStore(tmp_path/'s.db');add(s,1,'杯子',at=NOW-86400)
    w=worker(s);prepared=w.prepare('c:'+CID)
    add(s,2,'新内容',at=NOW-86400+1)
    assert w.commit('c:'+CID,prepared) is False
    assert not summaries(s)
    w.step();assert summaries(s)[0]['source_count']==2

def test_separate_visual_devices_do_not_share_digests(tmp_path):
    path=tmp_path/'s.db';a=TimelineObservationStore(path,device_id='one',clock=lambda:NOW-86400)
    b=TimelineObservationStore(path,device_id='two',clock=lambda:NOW-86400)
    a.add(frame(1),'设备一',NOW-86400);b.add(frame(2),'设备二',NOW-86400)
    wa=DigestWorker(path,a._digest_sources,zone='America/Los_Angeles',clock=lambda:NOW,owner='v:one')
    wb=DigestWorker(path,b._digest_sources,zone='America/Los_Angeles',clock=lambda:NOW,owner='v:two')
    wa.step();wb.step();q=query('昨天',now=NOW)
    assert '设备二' not in json.dumps(a.summary_events(q),ensure_ascii=False)
    assert '设备一' not in json.dumps(b.summary_events(q),ensure_ascii=False)
    a.close();b.close()

def test_dst_day_boundaries_and_exact_source_references():
    at=datetime(2026,11,1,12,tzinfo=timezone.utc).timestamp()
    rows=build('c:'+CID,[{'event_id':'original','source':'user_said','text':'合成输入','start_utc':at,'end_utc':at,'conversation_id':CID}],
               zone='America/Los_Angeles',now=at+86400)
    day=next(r for r in rows if r[2]=='day')
    assert day[5]-day[4]==25*3600 and json.loads(day[9])==['original']

def test_visual_dependency_change_invalidates_an_existing_digest(tmp_path):
    s=TimelineConversationStore(tmp_path/'s.db');m=add(s,1,'视觉派生',at=NOW-86400,played=True)
    w=worker(s);w.step();assert summaries(s)
    s.attach_visual(m,4);assert not summaries(s)
    w.step();assert summaries(s)[0]['visual_revision']==4
    s.invalidate_visual(5);assert not summaries(s)

def test_cross_conversation_visual_dependency_is_carried_into_next_answer(tmp_path):
    from tools.memory_timeline_host import memory_context
    from common.profile_access import ProfileAccess
    from tools.profile_control import turn_profile
    s=TimelineConversationStore(tmp_path/'s.db');p=s.create_profile('Synthetic',consent=True)
    old=add(s,1,'相机看到杯子在左边',profile=p,at=NOW-86400,played=True);s.attach_visual(old,4)
    w=worker(s);w.step()
    meta=add(s,2,'总结昨天聊了什么',profile=p,cid=OTHER,generated=False,at=NOW)
    access=ProfileAccess('9'*64);token,grant=access.issue(p,meta)
    model=SimpleNamespace(conversations=s,conversation_turns={meta['request_id']:OTHER},
        profile_turns={meta['request_id']:{'context':meta,'grant':grant}},profile_access=access)
    with patch('time.time',return_value=NOW),patch('tools.device_client.call',return_value={'version':1,'events':[],'revision':4}):
        context=memory_context(model,meta,'总结昨天聊了什么')
    assert context and '日摘要摘录' in context['content']
    assert s.visual_revision_for_records(s.records(OTHER,profile=p))==4

def test_source_limit_and_digest_cap_are_explicit(tmp_path):
    s=TimelineConversationStore(tmp_path/'s.db')
    for n in range(12):add(s,n+1,'来源'+str(n),at=NOW-86400+n)
    w=DigestWorker(s.path,s._digest_sources,zone='America/Los_Angeles',clock=lambda:NOW,source_limit=5)
    w.step();rows=summaries(s)
    assert rows and rows[0]['limited'] is True and rows[0]['source_count']==5
    assert len(rows[0]['text'])<=460

def test_digest_global_cap_does_not_remove_original_sources(tmp_path):
    s=TimelineConversationStore(tmp_path/'s.db')
    for n in range(4):add(s,n+1,'原始资料'+str(n),cid=str(n+1)*32,at=NOW-86400)
    w=DigestWorker(s.path,s._digest_sources,zone='America/Los_Angeles',clock=lambda:NOW,cache_limit=4)
    w.step()
    with s._connect() as db:
        assert db.execute('SELECT count(*) FROM timeline_digests').fetchone()[0]<=4
        assert db.execute('SELECT count(*) FROM turns').fetchone()[0]==4

def test_local_http_overview_uses_cached_digest_then_forget_invalidates_it(tmp_path):
    import http.client,threading
    from http.server import ThreadingHTTPServer
    from tools.device_hub import Handler
    now=[NOW-86400];s=TimelineObservationStore(tmp_path/'http.db',device_id='synthetic',clock=lambda:now[0])
    s.add(frame(1),'左侧可见杯子',now[0]);now[0]=NOW;worker(s).step()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    server.hub=SimpleNamespace(timeline={'timezone':'America/Los_Angeles'},observations=s)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def post(path,text):
        connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2)
        try:
            connection.request('POST',path,json.dumps({'boot':'another-boot','text':text}),{'Content-Type':'application/json'})
            response=connection.getresponse();raw=response.read();assert response.status==200 and len(raw)<=16384
            return json.loads(raw)
        finally:connection.close()
    try:
        with patch('time.time',return_value=NOW):
            result=post('/v1/memory/timeline','回顾昨天看到了什么')
            assert result['background_digest_used'] and result['events'][0]['source']=='daily_digest'
            assert result['events'][0]['source_events'] and result['events'][0]['identity_verified'] is False
            post('/v1/memory/timeline/forget','昨天')
            after=post('/v1/memory/timeline','回顾昨天看到了什么')
            assert not after['events'] and after['revision']>result['revision']
    finally:server.shutdown();server.server_close();thread.join();s.close()

def test_cached_visual_summary_does_not_become_an_untracked_personal_fact(tmp_path):
    from tools.memory_timeline_host import memory_context,validate_visual_memory
    now=[NOW-86400];visual=TimelineObservationStore(tmp_path/'visual.db',device_id='one',clock=lambda:now[0])
    visual.add(frame(1),'观察到杯子',now[0]);now[0]=NOW;worker(visual).step()
    events=visual.summary_events(query('回顾昨天看到了什么',now=NOW))
    chat=TimelineConversationStore(tmp_path/'chat.db');meta=add(chat,1,'回顾昨天看到了什么',generated=False,at=NOW)
    model=SimpleNamespace(conversations=chat,conversation_turns={meta['request_id']:CID})
    with patch('time.time',return_value=NOW),patch('tools.device_client.call',return_value={'version':1,'events':events,'revision':0}):
        assert '日摘要摘录' in memory_context(model,meta,'回顾昨天看到了什么')['content']
    assert chat.facts(CID)==[] and chat.has_visual_dependencies()
    visual.forget_timeline(query('昨天',now=NOW))
    with patch('tools.device_client.call',return_value={'version':1,'revision':1}):
        with pytest.raises(ValueError):validate_visual_memory(model,meta,force=True)
    visual.close()

def test_unavailable_digest_cache_falls_back_to_authoritative_sources(tmp_path):
    from tools.memory_timeline_host import memory_context
    s=TimelineConversationStore(tmp_path/'fallback.db');add(s,1,'项目是海风',at=NOW-86400)
    meta=add(s,2,'总结昨天聊了什么',at=NOW,generated=False)
    model=SimpleNamespace(conversations=s,conversation_turns={meta['request_id']:CID})
    with patch('time.time',return_value=NOW),patch.object(s,'summary_events',side_effect=sqlite3.OperationalError('cache busy')):
        with patch('tools.device_client.call',return_value={'version':1,'events':[],'revision':0}):
            context=memory_context(model,meta,'总结昨天聊了什么')
    assert '项目是海风' in context['content'] and 'digest_unavailable' in context['content']

@pytest.mark.parametrize('text,mode',[('总结昨天聊了什么','day'),('回顾昨天看到了什么','day'),('刚才这段聊到哪里','episode'),('昨天杯子在哪',None)])
def test_summary_intent_is_distinct_from_specific_fact_search(text,mode):
    assert summary_mode(text)==mode
