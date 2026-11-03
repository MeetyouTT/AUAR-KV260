"""Only synthetic events; production identity and observation databases are unused."""
from datetime import datetime,timezone
import io,json,sqlite3,threading,time
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from common.timeline import query,select,episode_excerpts,context_message
from common.timeline_conversations import TimelineConversationStore
from common.timeline_observations import TimelineObservationStore
from common.profile_memory import ProfileConversationStore
from common.timeline_config import visual_forget_command
from tests.framework.test_voice_channel import owner

NOW=datetime(2026,10,29,4,tzinfo=timezone.utc).timestamp()
CID='a'*32;OTHER='b'*32;THIRD='c'*32;DIGEST='d'*64

def frame(n=1,boot='boot-one',epoch='epoch-one'):
    return dict(board_boot_id=boot,camera_epoch=epoch,frame_id=n,captured_mono_ms=1000+n*10,observed_mono_ms=1100+n*10)

def add(store,n,text,*,cid=CID,profile=None,at=NOW-60,played=False,boot='boot-one',generated=True):
    meta=dict(owner('timeline-'+str(n),n),board_boot_id=boot)
    with patch('time.time',return_value=at):
        store.begin(cid,meta,text,text,profile=profile)
        if generated:store.generated(meta,'已回答：'+text,480,DIGEST)
        if played:store.played(meta,480,DIGEST)
    return meta

@pytest.mark.parametrize('word,hours', [('昨天下午',(12,18)),('昨天晚上',(18,24)),('昨天上午',(6,12))])
def test_calendar_range_uses_configured_zone(word,hours):
    q=query(word+'我们聊了什么',now=NOW)
    start=datetime(2026,10,27,hours[0]+7,tzinfo=timezone.utc).timestamp() if hours[0]+7<24 else datetime(2026,10,28,hours[0]+7-24,tzinfo=timezone.utc).timestamp()
    assert q['start']==start and q['end']-q['start']==(hours[1]-hours[0])*3600
    assert q['topic']=='' and q['error'] is None

def test_daylight_saving_day_is_not_hardcoded_24_hours():
    now=datetime(2026,11,3,4,tzinfo=timezone.utc).timestamp()
    q=query('昨天聊了什么',now=now)
    assert q['end']-q['start']==25*3600

@pytest.mark.parametrize('text',['2026-02-30看到了什么','上个月看到了什么','下午看到了什么'])
def test_ambiguous_date_does_not_search_all_history(text):
    q=query(text,now=NOW)
    assert q['error'] and select([],q)==[]

def test_ack_time_and_cross_boot_profile_history(tmp_path):
    path=tmp_path/'chat.db';store=TimelineConversationStore(path)
    profile=store.create_profile('Synthetic A',consent=True)
    old=add(store,1,'红色杯子在左边',profile=profile,at=NOW-86400,played=True)
    add(store,2,'未播放的机密回答',profile=profile,at=NOW-80000)
    new=dict(owner('new-request',3),board_boot_id='boot-two')
    store.begin(OTHER,new,'昨天杯子在哪','昨天杯子在哪',profile=profile)
    reopened=TimelineConversationStore(path)
    rows=reopened.timeline_events(OTHER,query('昨天杯子在哪',now=NOW),profile=profile,exclude=new['request_id'])
    assert {r['source'] for r in rows}=={'user_said','assistant_played'}
    assert all('左边' in r['text'] for r in rows)
    assert len({r['event_id'] for r in rows})==2
    assert reopened.played(old,480,DIGEST) is False
    assert not reopened.timeline_events(THIRD,query('昨天杯子在哪',now=NOW))
    with pytest.raises(PermissionError):reopened.timeline_events(OTHER,query('昨天杯子在哪',now=NOW))

def test_unplayed_cannot_be_recalled_or_upgraded_by_wrong_ack(tmp_path):
    store=TimelineConversationStore(tmp_path/'chat.db');m=add(store,1,'用户输入',played=False)
    with pytest.raises(ValueError):store.played(m,479,DIGEST)
    store.failed(m)
    with pytest.raises(ValueError):store.played(m,480,DIGEST)
    rows=store.timeline_events(CID,query('上次说了什么',now=NOW))
    assert [r['source'] for r in rows]==['user_said']

def test_legacy_migration_preserves_archive_and_does_not_invent_playback_time(tmp_path):
    path=tmp_path/'chat.db';old=ProfileConversationStore(path)
    add(old,1,'历史输入',played=True)
    before=old.records(CID)
    upgraded=TimelineConversationStore(path)
    assert upgraded.records(CID)==before
    rows=upgraded.timeline_events(CID,query('上次说了什么',now=NOW))
    assert next(r for r in rows if r['source']=='assistant_played')['time_basis']=='legacy_turn_received_playback_time_unknown'

def test_correction_forget_and_rebuilt_episode_do_not_resurrect_sources(tmp_path):
    store=TimelineConversationStore(tmp_path/'chat.db');p=store.create_profile('Synthetic',consent=True)
    add(store,1,'项目是海风',profile=p,played=True)
    m=add(store,2,'记住：项目=海风',profile=p,generated=False)
    store.memory_command(m,'记住：项目=海风',profile=p)
    m=add(store,3,'更正记忆：项目=晨光',profile=p,cid=OTHER,generated=False)
    store.memory_command(m,'更正记忆：项目=晨光',profile=p)
    # A later query must see neither the old user turn nor its played paraphrase.
    q=query('上次项目说了什么',now=NOW+5)
    rows=store.timeline_events(OTHER,q,profile=p)
    assert '海风' not in json.dumps([rows,episode_excerpts(rows)],ensure_ascii=False)
    m=add(store,4,'清空我的长期记忆',profile=p,cid=OTHER,generated=False)
    store.memory_command(m,'清空我的长期记忆',profile=p)
    assert store.timeline_events(CID,query('上次说了什么',now=NOW+5),profile=p)==[]
    with pytest.raises(ValueError):store.played(dict(owner('timeline-1',1),board_boot_id='boot-one'),480,DIGEST)

def test_other_profiles_and_guest_are_never_adopted(tmp_path):
    store=TimelineConversationStore(tmp_path/'chat.db');a=store.create_profile('A',consent=True);b=store.create_profile('B',consent=True)
    add(store,1,'A秘密',profile=a);add(store,2,'B秘密',profile=b,cid=OTHER);add(store,3,'访客内容',cid=THIRD)
    q=query('上次说了什么',now=NOW)
    assert 'B秘密' not in json.dumps(store.timeline_events(CID,q,profile=a),ensure_ascii=False)
    assert 'A秘密' not in json.dumps(store.timeline_events(THIRD,q),ensure_ascii=False)
    with pytest.raises(PermissionError):store.timeline_events(THIRD,q,profile=a)

def test_held_writer_lock_has_bounded_read_failure(tmp_path):
    store=TimelineConversationStore(tmp_path/'chat.db')
    acquired=threading.Event();release=threading.Event()
    def block():
        with store.lock:acquired.set();release.wait(1)
    thread=threading.Thread(target=block);thread.start();acquired.wait()
    started=time.monotonic()
    try:
        with pytest.raises(TimeoutError):store.timeline_events(CID,query('上次说了什么',now=NOW))
        assert time.monotonic()-started<.2
    finally:release.set();thread.join()

def test_visual_cross_boot_dedup_source_and_real_calendar(tmp_path):
    now=[NOW-86400];path=tmp_path/'obs.db'
    store=TimelineObservationStore(path,device_id='test-board',clock=lambda:now[0])
    for n in range(1,4):
        store.add(frame(n),'桌左侧可见杯子',now[0]);now[0]+=15
    store.add(frame(1,boot='boot-two'),'桌左侧可见杯子',now[0]);store.close()
    now[0]=NOW;store=TimelineObservationStore(path,device_id='test-board',clock=lambda:now[0])
    rows=store.timeline_events(query('昨天杯子在哪',now=NOW))
    assert len(rows)==2 and sorted(r['observation_count'] for r in rows)==[1,3]
    assert all(r['time_basis']=='host_received' and r['current'] is False and r['identity_verified'] is False for r in rows)
    assert {r['boot'] for r in rows}=={'boot-one','boot-two'}
    assert not store.recall('boot-two') # Short live cache never calls an old event current.
    store.close()

def test_changed_scene_gap_or_clock_rollback_never_merge(tmp_path):
    now=[NOW];s=TimelineObservationStore(tmp_path/'o.db',device_id='device',clock=lambda:now[0])
    s.add(frame(1),'杯子左侧',now[0]);now[0]+=15;s.add(frame(2),'杯子右侧',now[0])
    now[0]+=60;s.add(frame(3),'杯子右侧',now[0]);now[0]-=5;s.add(frame(4),'杯子右侧',now[0])
    assert s.db.execute('SELECT count(*) FROM visual_timeline').fetchone()[0]==4
    s.close()

def test_visual_delete_generation_survives_restart_and_blocks_replay(tmp_path):
    path=tmp_path/'o.db';s=TimelineObservationStore(path,device_id='d',clock=lambda:NOW)
    generation=s.generation('boot-one');s.add(frame(1),'杯子左侧',NOW,generation=generation)
    assert s.forget_timeline(query('',now=NOW))==1
    assert not s.timeline_events(query('上次杯子在哪',now=NOW)) and not s.recall('boot-one',history=True)
    s.close();s=TimelineObservationStore(path,device_id='d',clock=lambda:NOW)
    assert s.add(frame(2),'迟到摘要',NOW,generation=generation) is False
    assert s.add(frame(1),'重放帧',NOW,generation=s.generation('boot-one')) is False
    assert s.add(frame(2),'新观察',NOW,generation=s.generation('boot-one')) is True
    s.close()

def test_delete_range_keeps_other_days_and_devices(tmp_path):
    now=[NOW-86400];path=tmp_path/'o.db';s=TimelineObservationStore(path,device_id='one',clock=lambda:now[0])
    s.add(frame(1),'昨天的杯子',now[0]);now[0]=NOW;s.add(frame(2),'今天的杯子',now[0])
    # Reusing storage under a different configured device never exposes old history.
    other=TimelineObservationStore(path,device_id='two',clock=lambda:now[0])
    assert other.timeline_events(query('上次杯子在哪',now=NOW))==[]
    assert s.forget_timeline(query('昨天',now=NOW))==1
    assert [r['text'] for r in s.timeline_events(query('上次杯子在哪',now=NOW))]==['今天的杯子']
    other.close();s.close()

def test_retention_capacity_and_query_budget(tmp_path):
    now=[NOW];s=TimelineObservationStore(tmp_path/'o.db',device_id='d',clock=lambda:now[0],history_limit=3,history_days=2)
    for n in range(5):s.add(frame(n),'物体'+str(n),now[0]);now[0]+=10
    assert s.db.execute('SELECT count(*) FROM visual_timeline').fetchone()[0]==3
    now[0]+=3*86400
    assert not s.timeline_events(query('上次看到了什么',now=now[0]))
    s.close()
    q=query('上次说了什么',now=NOW)
    rows=[dict(event_id=str(n),source='user_said',text='甲'*400,start_utc=NOW-n,end_utc=NOW-n) for n in range(8)]
    msg=context_message(rows,q,max_bytes=1600)
    assert len(msg['content'].encode())<=1600
    data=json.loads(msg['content'].split('\n',1)[1]);assert data['events']
    assert all(r['partial'] and set(r['text'])=={'甲'} for r in data['events'])

@pytest.mark.parametrize('text,expected',[('清除所有视觉记忆',''),('删除昨天的画面记录','昨天'),('请清除昨天下午的视觉记录','昨天下午'),
    ('不要删除昨天的视觉记录',None),('他说删除昨天的视觉记录',None),('删除视觉记录',None),('清除画面记忆',None)])
def test_destructive_commands_have_explicit_scope(text,expected):
    assert visual_forget_command(text)==expected

def test_missing_hub_is_a_bounded_unavailable_context_not_a_voice_gate(tmp_path):
    from tools.memory_timeline_host import memory_context
    s=TimelineConversationStore(tmp_path/'c.db');add(s,1,'杯子在左边',played=True)
    m=owner('query',4);model=SimpleNamespace(conversation_turns={'query':CID},conversations=s)
    with patch('tools.device_client.call',side_effect=OSError('offline')),patch('time.time',return_value=NOW):
        msg=memory_context(model,m,'上次杯子在哪')
    assert '杯子在左边' in msg['content'] and 'visual_unavailable' in msg['content']

def test_visual_revision_cancels_old_output_after_forget():
    from tools.memory_timeline_host import memory_context,validate_visual_memory
    m=owner('query',4);model=SimpleNamespace()
    event=dict(event_id='v',source='camera_observed',scope='configured_device',start_utc=NOW-10,end_utc=NOW-10,text='杯子左侧')
    with patch('time.time',return_value=NOW),patch('tools.device_client.call',return_value={'version':1,'events':[event],'revision':4}):
        assert '杯子左侧' in memory_context(model,m,'上次杯子在哪')['content']
    with patch('tools.device_client.call',return_value={'version':1,'revision':5}):
        with pytest.raises(ValueError,match='changed'):validate_visual_memory(model,m,force=True)

def test_query_topic_ranks_relevant_older_event_over_newest():
    q=query('上次把杯子放哪了',now=NOW)
    rows=[dict(event_id='old',start_utc=NOW-100,end_utc=NOW-100,text='杯子放在左边'),
          dict(event_id='new',start_utc=NOW-1,end_utc=NOW-1,text='键盘在右边')]
    assert [r['event_id'] for r in select(rows,q)]==['old']

def test_new_http_timeline_read_delete_and_revision_are_consistent(tmp_path):
    import http.client
    from http.server import ThreadingHTTPServer
    from tools.device_hub import Handler
    now=[NOW-86400];store=TimelineObservationStore(tmp_path/'hub.db',device_id='synthetic-device',clock=lambda:now[0])
    store.add(frame(1),'杯子在桌左侧',now[0]);now[0]=NOW
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    server.hub=SimpleNamespace(observations=store,timeline={'timezone':'America/Los_Angeles'})
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def post(path,value,origin=None):
        connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2)
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        try:
            connection.request('POST',path,json.dumps(value),headers)
            response=connection.getresponse();raw=response.read()
            assert len(raw)<=16384
            return response.status,json.loads(raw)
        finally:connection.close()
    try:
        with patch('time.time',return_value=NOW):
            status,body=post('/v1/memory/timeline',{'text':'昨天杯子在哪','boot':'new-boot'})
            assert status==200 and body['events'][0]['text']=='杯子在桌左侧' and body['episodes']
            before=body['revision']
            assert post('/v1/memory/timeline',{'text':'昨天','boot':'new-boot'},origin='https://untrusted.test')[0]==403
            assert post('/v1/memory/timeline',{'text':'昨天','boot':'new-boot','profile':'forged'})[0]==400
            status,deleted=post('/v1/memory/timeline/forget',{'text':'昨天','boot':'new-boot'})
            assert status==200 and deleted['deleted_events']==1 and deleted['revision']==before+1
            assert post('/v1/memory/timeline',{'text':'昨天','boot':'new-boot'})[1]['events']==[]
            assert post('/v1/memory/revision',{'boot':'new-boot'})[1]['revision']==before+1
    finally:server.shutdown();server.server_close();thread.join();store.close()

def test_compressed_span_overlapping_day_range_remains_visible(tmp_path):
    q=query('昨天下午杯子在哪',now=NOW)
    row=dict(event_id='span',source='camera_observed',start_utc=q['end']-10,end_utc=q['end']+10,text='杯子在左侧')
    assert select([row],q)==[row]

def test_new_ack_rejects_changed_visual_history(tmp_path):
    from tests.framework.test_long_conversation import host
    from tools.memory_timeline_host import memory_context
    model=host(tmp_path);meta=owner('fenced',2)
    model.register_stream(meta)
    event=dict(event_id='v',source='camera_observed',scope='configured_device',start_utc=NOW-10,end_utc=NOW-10,text='杯子左侧')
    with patch('time.time',return_value=NOW),patch('tools.device_client.call',return_value={'version':1,'events':[event],'revision':1}):
        memory_context(model,meta,'上次杯子在哪')
        model.complete_stream(meta,'上次杯子在哪','刚才在左侧',480,DIGEST)
    with patch('tools.device_client.call',return_value={'version':1,'revision':2}):
        with pytest.raises(ValueError,match='changed'):
            model.acknowledge_stream({'context':meta,'voice_sample_count':480,'pcm_sha256':DIGEST})

def test_historical_pipeline_injects_scoped_timeline_without_second_camera(tmp_path):
    from tools.voice_channel_source import channel_frames
    from common.voice_channel import read_frame
    from tests.framework.test_voice_channel import VoiceChannelTests
    from tests.framework.test_long_conversation import host
    model=host(tmp_path);model.conversations=TimelineConversationStore(tmp_path/'timeline.db')
    model.voice=VoiceChannelTests().fixture_models(tmp_path).voice;model.latency_options={}
    add(model.conversations,1,'杯子放左边',at=NOW-86400,played=True)
    received=[]
    class Stream:
        def __init__(self,host,model,history,*args,**kwargs):received.extend(history)
        def __iter__(self):
            yield 'text','完整回答。'
            yield 'complete',{'reply_text':'完整回答。','emotion':'neutral','avatar_action':''}
        def cancel(self):pass
    with patch('time.time',return_value=NOW),patch('tools.device_client.call',return_value={'version':1,'events':[],'revision':0}):
        packets=list(channel_frames(model,owner('actual-pipeline',2),'昨天杯子放在哪',5,model='same',host='unused',
                    stream_factory=Stream,conversation=CID))
    headers=[read_frame(io.BytesIO(p))[0] for p in packets]
    assert headers[-1]['kind']=='end'
    assert any('时间轴资料' in h['content'] and '杯子放左边' in h['content'] for h in received),received

def test_topic_filter_finds_an_older_event_beyond_recent_scan_window(tmp_path):
    s=TimelineConversationStore(tmp_path/'archive.db');add(s,1,'杯子放左边',at=NOW-10000)
    # Bulk synthetic archive avoids making the fixture a disk-write benchmark.
    with s._connect() as db:
        db.executemany("INSERT INTO turns(request_id,conversation_id,context,user,raw_user,status,created) VALUES(?,?,?,?,?,'submitted',?)",
            [('filler-'+str(n),CID,json.dumps(owner('filler-'+str(n),n)),'键盘在右侧','键盘在右侧',NOW-9000+n) for n in range(800)])
    assert [r['text'] for r in s.timeline_events(CID,query('上次杯子放哪了',now=NOW))]==['杯子放左边']

def test_two_dates_are_not_silently_treated_as_the_first_date():
    assert query('2026-10-20到2026-10-27看到了什么',now=NOW)['error']
    assert query('昨天到今天说了什么',now=NOW)['error']

def test_forgotten_visual_source_invalidates_played_paraphrases_and_followups(tmp_path):
    from tools.memory_timeline_host import sync_visual_archive,use_visual_revision
    from tests.framework.test_long_conversation import host
    model=host(tmp_path);s=TimelineConversationStore(tmp_path/'derived.db');model.conversations=s
    p=s.create_profile('Synthetic',consent=True)
    m=add(s,1,'杯子在哪里',profile=p,played=True)
    s.attach_visual(m,7)
    followup=add(s,2,'再说一遍',profile=p,cid=OTHER,played=True)
    s.attach_visual(followup,7)  # The source dependency propagates to a follow-up.
    add(s,3,'这是用户独立告知的事实',profile=p,cid=OTHER,played=True)
    with patch('tools.device_client.call',return_value={'version':1,'revision':8}):
        sync_visual_archive(model,owner('query',4))
    restored=TimelineConversationStore(s.path)
    q=query('上次说了什么',now=NOW+1)
    rows=restored.timeline_events(OTHER,q,profile=p)
    assert rows and all('独立告知' in r['text'] for r in rows)
    assert restored.records(CID,profile=p)==[]
    with pytest.raises(ValueError):restored.played(m,480,DIGEST)
    assert '杯子在哪里' not in json.dumps(episode_excerpts(rows),ensure_ascii=False)

def test_unavailable_visual_revision_fail_closed_for_derived_archive_only(tmp_path):
    from tools.memory_timeline_host import sync_visual_archive
    s=TimelineConversationStore(tmp_path/'derived.db');m=add(s,1,'视觉回答',played=True)
    s.attach_visual(m,1);add(s,2,'独立语音',played=True)
    model=SimpleNamespace(conversations=s)
    with patch('tools.device_client.call',side_effect=OSError('offline')):sync_visual_archive(model,owner('later',3))
    assert all('独立语音' in r['user'] for r in s.records(CID))

def test_authorization_failure_is_never_converted_to_unavailable_visual_context(tmp_path):
    from tools.memory_timeline_host import memory_context
    s=TimelineConversationStore(tmp_path/'private.db');p=s.create_profile('Synthetic',consent=True)
    add(s,1,'档案私密',profile=p)
    model=SimpleNamespace(conversations=s,conversation_turns={'query':CID})
    with patch('tools.device_client.call',return_value={'version':1,'events':[],'revision':0}):
        with pytest.raises(PermissionError):memory_context(model,owner('query',2),'上次说了什么')

def test_live_visual_context_registers_revision_and_derived_turn(tmp_path):
    from tools.memory_timeline_host import live_context,validate_visual_memory
    store=TimelineConversationStore(tmp_path/'derived.db');meta=add(store,1,'你好',generated=False)
    model=SimpleNamespace(conversations=store,conversation_turns={meta['request_id']:CID})
    with patch('tools.device_client.call',return_value={'revision':2,'observations':[{'summary':'相机观察到杯子','current':True}]}):
        assert '杯子' in live_context(model,meta,'你好')['content']
    assert store.has_visual_dependencies()
    with patch('tools.device_client.call',return_value={'version':1,'revision':3}):
        with pytest.raises(ValueError):validate_visual_memory(model,meta,force=True)

def test_explicit_clear_includes_legacy_cache_and_future_rows_after_clock_rollback(tmp_path):
    now=[NOW];s=TimelineObservationStore(tmp_path/'legacy.db',device_id='one',clock=lambda:now[0])
    s.add(frame(1),'回拨前的观察',now[0])
    with s.db:s.db.execute('INSERT INTO observations(boot,epoch,frame,received,summary) VALUES(?,?,?,?,?)',
                          ('legacy','legacy',99,NOW-30,'旧版缓存'))
    now[0]-=60
    assert s.forget_timeline(query('',now=now[0]))==1
    assert s.db.execute('SELECT count(*) FROM observations').fetchone()[0]==0
    assert s.db.execute('SELECT count(*) FROM visual_timeline').fetchone()[0]==0
    s.close()
