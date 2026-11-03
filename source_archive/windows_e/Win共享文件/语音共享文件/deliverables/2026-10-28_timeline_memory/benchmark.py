"""Synthetic bounded-history benchmark; contains no user's actual recordings/data."""
import bootstrap
from common.timeline import query,context_message
from common.timeline_conversations import TimelineConversationStore
from common.timeline_observations import TimelineObservationStore
from common.conversation_context import request_cost
from pathlib import Path
import json,statistics,time,uuid
H=Path(__file__).resolve().parent;root=H/'test_tmp'/('benchmark-'+uuid.uuid4().hex);root.mkdir(parents=True)
now=time.time();cid='a'*32
chat=TimelineConversationStore(root/'chat.db')
with chat._connect() as db:
    db.execute('INSERT INTO conversations(id,created) VALUES(?,?)',(cid,now-30*86400))
    db.executemany('INSERT INTO turns(request_id,conversation_id,context,user,raw_user,status,created) VALUES(?,?,?,?,?,?,?)',
        [('synthetic-'+str(n),cid,json.dumps({'board_boot_id':'synthetic-boot','request_id':'synthetic-'+str(n)}),
          '红色杯子在左边' if n%197==0 else '键盘在桌面右侧','合成输入','submitted',now-30*86400+n*259) for n in range(10000)])
visual=TimelineObservationStore(root/'visual.db',device_id='synthetic',clock=lambda:now)
with visual.db:
    visual.db.executemany('INSERT INTO visual_timeline VALUES(?,?,?,?,?,?,?,?,?,?,?)',
        [('visual-'+str(n),'synthetic','boot-'+str(n//1000),'epoch',n,n,now-30*86400+n*259,now-30*86400+n*259,1,
          '桌左侧可见杯子' if n%199==0 else '桌面上有键盘','{}') for n in range(10000)])
def measure(fn):
    durations=[];results=[]
    for _ in range(30):
        start=time.perf_counter();results=fn();durations.append((time.perf_counter()-start)*1000)
    ordered=sorted(durations)
    return {'median_ms':statistics.median(durations),'p95_ms':ordered[28],'max_ms':max(durations),'result_count':len(results)}
report={'scope':'10000 synthetic turns and 10000 synthetic visual events; no production DB',
        'conversation_topic':measure(lambda:chat.timeline_events(cid,query('上次杯子放哪了',now=now))),
        'visual_topic':measure(lambda:visual.timeline_events(query('上次杯子在哪',now=now))),
        'conversation_day':measure(lambda:chat.timeline_events(cid,query('昨天说了什么',now=now))),
        'visual_day':measure(lambda:visual.timeline_events(query('昨天看到了什么',now=now)))}
q=query('上次杯子放哪了',now=now);rows=chat.timeline_events(cid,q)+visual.timeline_events(q)
base,maximum=request_cost('same',[],'上次杯子放哪了')
message=context_message(rows,q,max_bytes=maximum-base-32)
cost,_=request_cost('same',[message],'上次杯子放哪了')
assert message and '杯子' in message['content'] and cost<=maximum
report['context']={'upper_bound':cost,'limit':maximum,'bytes':len(message['content'].encode()),'contains_cup':True}
report['passed']=all(report[name]['max_ms']<150 for name in ('conversation_topic','visual_topic','conversation_day','visual_day'))
visual.close();(H/'benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report));assert report['passed']
