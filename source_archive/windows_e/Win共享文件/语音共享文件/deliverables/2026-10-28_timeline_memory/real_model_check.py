"""Actual existing 27B reads synthetic timeline fixtures; no production DB edits."""
import bootstrap
bootstrap.service_module()
import json,time,uuid
from pathlib import Path
from common.timeline import query,context_message
from common.timeline_conversations import TimelineConversationStore
from common.timeline_observations import TimelineObservationStore
from common.conversation_context import request_cost
from tools.dialogue_stream import OllamaReplyStream
from tools.board_model_host import MODEL,OLLAMA_HOST
H=Path(__file__).resolve().parent;root=H/'test_tmp'/('real-model-'+uuid.uuid4().hex);root.mkdir(parents=True)
now=time.time();old=now-86400;cid='a'*32
store=TimelineConversationStore(root/'dialogue.db')
meta={'board_boot_id':'synthetic-old-boot','session_id':'synthetic','request_id':'synthetic-turn','generation':1}
store.begin(cid,meta,'我把红色杯子放在桌子左边了。','我把红色杯子放在桌子左边了。')
with store._connect() as db:db.execute('UPDATE turns SET created=?',(old,))
visual=TimelineObservationStore(root/'visual.db',device_id='synthetic',clock=lambda:old)
visual.add({'board_boot_id':'synthetic-old-boot','camera_epoch':'synthetic-camera','frame_id':1},'桌子左侧可见一个红色杯子。',old)
visual.close();visual=TimelineObservationStore(root/'visual.db',device_id='synthetic',clock=lambda:now)
report={'scope':'synthetic source fixtures and actual current 27B inference; no actual microphone, image, playback or production DB',
        'model':MODEL,'checks':[]}
def check(name,text,rows,expected):
    q=query(text,now=now);base,maximum=request_cost(MODEL,[],text)
    msg=context_message(rows,q,max_bytes=maximum-base-32);assert msg
    cost,_=request_cost(MODEL,[msg],text);assert cost<=maximum
    began=time.monotonic();stream=OllamaReplyStream(OLLAMA_HOST,MODEL,[msg],text,60,reply_first=True,compact_grammar=True)
    reply=None
    try:
        for kind,value in stream:
            if kind=='complete':reply=value['reply_text']
    finally:stream.cancel()
    assert reply
    passed=('左' in reply if expected=='left' else any(w in reply for w in ('没有','没记','不知','不确定','不清楚','没看到','未记录','记录不足','没有记录')))
    result={'name':name,'reply':reply,'expected':expected,'passed':passed,'seconds':round(time.monotonic()-began,3),
            'source_count':len(rows),'context_upper_bound':cost,'context_limit':maximum,'model_metrics':getattr(stream,'metrics',{})}
    report['checks'].append(result);save();print(json.dumps(result,ensure_ascii=True),flush=True)
def save():(H/'real_model_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
text='昨天我把杯子放在哪了？';q=query(text,now=now)
check('cross_boot_dialogue_and_visual',text,store.timeline_events(cid,q)+visual.timeline_events(q),'left')
check('no_visual_dialogue_still_recalls',text,store.timeline_events(cid,q),'left')
visual.forget_timeline(query('',now=now))
check('forgotten_visual_has_no_retrievable_event','昨天看到了什么？',visual.timeline_events(query('昨天看到了什么',now=now)),'unknown')
report['status']='PASS' if all(r['passed'] for r in report['checks']) else 'FAIL'
visual.close();save();assert report['status']=='PASS'
