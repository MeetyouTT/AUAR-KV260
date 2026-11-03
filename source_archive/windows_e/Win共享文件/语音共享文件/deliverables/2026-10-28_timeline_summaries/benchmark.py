"""Synthetic scale and concurrent writer benchmark; no production services/DB."""
import bootstrap
bootstrap.service_module()
import json,statistics,time,uuid
from pathlib import Path
from common.timeline import query
from common.timeline_conversations import TimelineConversationStore
from common.timeline_summaries import DigestWorker
from test_timeline import CID,owner
H=Path(__file__).resolve().parent;root=H/'test_tmp'/('benchmark-'+uuid.uuid4().hex);root.mkdir(parents=True)
now=time.time();store=TimelineConversationStore(root/'synthetic.db')
with store._connect() as db:
    db.execute('INSERT INTO conversations(id,created) VALUES(?,?)',(CID,now-30*86400))
    db.executemany('INSERT INTO turns(request_id,conversation_id,context,user,raw_user,status,created) VALUES(?,?,?,?,?,?,?)',
        [('scale-'+str(n),CID,json.dumps({'board_boot_id':'synthetic','request_id':'scale-'+str(n)}),
          '项目在进行第'+str(n)+'阶段；杯子放在左边','合成资料','submitted',now-29*86400+n*250) for n in range(10000)])
worker=DigestWorker(store.path,store._digest_sources,zone='America/Los_Angeles',clock=lambda:now,interval=.01)
report={'scope':'10000 synthetic turns; no production service, mic, model or camera'}
start=time.perf_counter();worker.step();report['build_ms']=(time.perf_counter()-start)*1000
with store._connect() as db:
    report['digest_rows']=db.execute('SELECT count(*) FROM timeline_digests').fetchone()[0]
    day=db.execute("SELECT day FROM timeline_digests WHERE kind='day' ORDER BY day DESC LIMIT 1").fetchone()[0]
times=[]
for _ in range(50):
    q=query('总结'+day+'聊了什么',now=now)
    start=time.perf_counter();rows=store.summary_events(CID,q);times.append((time.perf_counter()-start)*1000)
assert rows
report['cached_query_ms']={'median':statistics.median(times),'p95':sorted(times)[47],'max':max(times)}
worker.start();write_times=[]
try:
    for n in range(30):
        m=owner('concurrent-'+str(n),n)
        before=time.perf_counter();store.begin(CID,m,'新的普通聊天输入','新的普通聊天输入');write_times.append((time.perf_counter()-before)*1000)
        time.sleep(.01)
finally:worker.close()
report['concurrent_input_write_ms']={'median':statistics.median(write_times),'p95':sorted(write_times)[28],'max':max(write_times)}
report['worker_health']=worker.health();report['database_bytes']=store.path.stat().st_size
report['pass']=report['build_ms']<1000 and report['cached_query_ms']['max']<100 and report['concurrent_input_write_ms']['max']<150
(H/'benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report));assert report['pass']
