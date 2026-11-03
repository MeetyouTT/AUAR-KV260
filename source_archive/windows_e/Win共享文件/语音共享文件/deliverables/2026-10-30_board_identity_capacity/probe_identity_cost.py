"""Bounded synthetic SQLite/lookup costs in RAM; no real identity reads."""
import ast,datetime,hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
sys.path[:0]=[str(P/'deliverables/2026-10-18_board_dialogue'),str(P/'deliverables/2026-10-29_audio_animation_polish')]
from board_ssh import ssh
from board_guard import capture,same
def schema(path):
 tree=ast.parse(path.read_text(encoding='utf-8'))
 values=[node.args[0].value for node in ast.walk(tree) if isinstance(node,ast.Call)
  and isinstance(node.func,ast.Attribute) and node.func.attr=='executescript' and node.args
  and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str)]
 assert len(values)==1
 return values[0]
payload=dict(links=schema(A/'common/identity_links.py'),anonymous=schema(A/'common/anonymous_voice.py'))
REMOTE=r'''
import hashlib,importlib.metadata,json,math,os,resource,sqlite3,statistics,time
os.nice(19)
payload=json.loads(PAYLOAD_JSON)
deadline=time.monotonic()+6
def limit():
 if time.monotonic()>deadline:raise TimeoutError('Synthetic microprobe exceeded its six-second work budget')
def pct(values,fraction):return sorted(values)[min(len(values)-1,int((len(values)-1)*fraction))]
def pages(db):return db.execute('PRAGMA page_count').fetchone()[0]*db.execute('PRAGMA page_size').fetchone()[0]
baseline_rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
links=sqlite3.connect(':memory:');links.executescript(payload['links'])
anonymous=sqlite3.connect(':memory:');anonymous.executescript(payload['anonymous'])
now=time.time();people=32;aliases=32
for i in range(people):
 person=('%032x'%(i+1));name='public_person_%02d'%i
 links.execute('INSERT INTO linked_people VALUES(?,?,?,?,?)',(person,name,name,'ACTIVE',now))
 for modality in ('face','voice'):
  identity='public_%s_%02d'%(modality,i)
  links.execute('INSERT INTO modality_links VALUES(?,?,?,?,?,?,?,?)',
   (person,modality,'public_store_'+modality,identity,'public_model',1,'0'*64,'ACTIVE'))
vector=[math.sin(i+1)/10 for i in range(192)];norm=math.sqrt(sum(v*v for v in vector));vector=[v/norm for v in vector]
meta=dict(protocol='aura-asr-1',board_boot_id='public-capacity',session_id='s'*32,request_id='r'*32,
 generation=1,capture_id='public-capacity',sample_count=48000,pcm_sha256='0'*64,budget_ms=120000)
for i in range(aliases):
 cluster='%032x'%(i+1)
 anonymous.execute('INSERT INTO anonymous_labels(cluster_id,boot,created,expires,state) VALUES(?,?,?,?,?)',
  (cluster,'public-capacity',now,now+86400,'ACTIVE'))
 anonymous.execute('INSERT INTO anonymous_anchors VALUES(?,?)',(cluster,json.dumps(vector,separators=(',',':'))))
 for n in range(3):anonymous.execute('INSERT INTO anonymous_samples VALUES(?,?,?)',(cluster,'public_%s'%n,('%064x'%(n+1))))
links.commit();anonymous.commit();base_alias_bytes=pages(anonymous)
for i in range(4096):
 if i%256==0:limit()
 index=i%aliases;cluster='%032x'%(index+1)
 owner=dict(meta,request_id='%032x'%(i+1),capture_id='public_%d'%i)
 descriptor=dict(version=1,context=owner,state='PROVISIONAL',reason='SYNTHETIC_CAPACITY',registry_epoch='0'*32,
  cluster_id=cluster,code='a%d'%(index+1),model_id='public_ecapa_model',distinct_captures=3,provisional=True,
  identity_verified=False,personal_memory_allowed=False)
 anonymous.execute('INSERT INTO anonymous_observations VALUES(?,?,?,?,?)',
  (owner['request_id'],json.dumps(owner,separators=(',',':')),json.dumps(descriptor,separators=(',',':')),now,cluster))
anonymous.commit();limit()
latencies=[]
for i in range(100):
 start=time.perf_counter()
 row=links.execute("SELECT p.person_id,p.name,p.state FROM modality_links l JOIN linked_people p USING(person_id) "
  "WHERE l.modality=? AND l.store_id=? AND l.identity_id=? AND l.model_id=? AND l.state='ACTIVE' AND p.state='ACTIVE'",
  ('face','public_store_face','public_face_%02d'%(i%people),'public_model')).fetchone()
 assert row is not None
 latencies.append((time.perf_counter()-start)*1000)
 if i%20==0:limit();time.sleep(.01)
cosines={}
for count in (32,128):
 gallery=[tuple(vector) for _ in range(count)];times=[]
 for repeat in range(8):
  start=time.perf_counter();scores=[sum(a*b for a,b in zip(vector,anchor)) for anchor in gallery]
  assert len(scores)==count
  times.append((time.perf_counter()-start)*1000)
  limit();time.sleep(.02)
 cosines[str(count)]=dict(p50_ms=statistics.median(times),p95_ms=pct(times,.95),max_ms=max(times),repeats=len(times))
report=dict(status='PASS',scope='SYNTHETIC_IN_MEMORY_SQL_AND_PRECOMPUTED_VECTOR_COMPARISON_NOT_MODEL_INFERENCE',
 people=people,anonymous_clusters=aliases,anonymous_observations=4096,voice_dimensions=192,
 link_database_page_bytes=pages(links),anonymous_base_page_bytes=base_alias_bytes,
 anonymous_full_observations_page_bytes=pages(anonymous),
 lookup_ms=dict(p50=statistics.median(latencies),p95=pct(latencies,.95),max=max(latencies),repeats=len(latencies)),
 precomputed_vector_comparison=cosines,process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
 process_peak_rss_before_work_bytes=baseline_rss,source_schema_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in payload.items()},
 storage_written=False,biometric_data_used=False,actual_enrollment_exercised=False,model_loaded=False,
 limitations=['RAM database excludes SD-card writes/fsync/WAL/backup overhead',
 'Fixed synthetic JSON descriptors, not a future maximum byte guarantee',
 'Vector comparison excludes waveform preprocessing and neural ECAPA embedding',
 '128 anchors is a synthetic scale check, not a changed production limit'])
print(json.dumps(report))
'''
report=dict(status='CHECKING',host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
try:
 before=capture();assert before['safe'] and not before['mismatches']
 report.update(json.loads(ssh('python3 -B -',REMOTE.replace('PAYLOAD_JSON',repr(json.dumps(payload))),timeout=16)))
 after=capture();same(before,after)
 report['board_safe_unchanged']=True
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'identity_microprobe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)
