import json,os,time,http.client,hashlib
from pathlib import Path
GROUPS={394769:'audio_frontend',394740:'audio_capture',394720:'GUI',362659:'camera'}
def tids():
 out={}
 for pid,label in GROUPS.items():
  for p in (Path('/proc')/str(pid)/'task').iterdir():
   try:
    tid=int(p.name);v=(p/'stat').read_text().rsplit(')',1)[1].split();ss=[int(x) for x in (p/'schedstat').read_text().split()];out[(pid,tid)]={'group':label,'pid':pid,'tid':tid,'birth_ticks':v[19],'utime_ticks':int(v[11]),'stime_ticks':int(v[12]),'nice':int(v[16]),'priority_field':int(v[15]),'policy':os.sched_getscheduler(tid),'sched_priority':os.sched_getparam(tid).sched_priority,'affinity':sorted(os.sched_getaffinity(tid)),'run_ns':ss[0],'runqueue_ns':ss[1]}
   except (OSError,ValueError,IndexError,ProcessLookupError):pass
 return time.monotonic(),out
def status():
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
 try:c.request('GET','/api/state');r=c.getresponse();assert r.status==200;v=json.loads(r.read(2097152))
 finally:c.close()
 def numbers(v):
  if isinstance(v,dict):return {k:numbers(x) for k,x in v.items() if not any(w in k.lower() for w in ('score','probability','transcript','embedding')) and isinstance(x,(dict,int,float,bool,type(None)))}
  return v
 rec=v.get('local_recording') or {};return {'ui_page':v.get('ui_page'),'handsfree':{k:(v.get('handsfree_dialogue') or {}).get(k) for k in ('enabled','microphone_open','state')},'recording_state':rec.get('state'),'audio_frontend':numbers(rec.get('audio_frontend') or {}),'input_queue':numbers(rec.get('input_queue') or {}),'playing':v.get('playing'),'pending_job':bool(v.get('pending_job'))}
before=status();start,a=tids();time.sleep(2);end,b=tids();hz=os.sysconf('SC_CLK_TCK');rows=[]
for key,v in b.items():
 old=a.get(key)
 if not old or old['birth_ticks']!=v['birth_ticks']:continue
 x=dict(v);x['cpu_percent']=round(((v['utime_ticks']+v['stime_ticks'])-(old['utime_ticks']+old['stime_ticks']))/hz/(end-start)*100,2);x['runqueue_wait_percent']=round((v['runqueue_ns']-old['runqueue_ns'])/1e9/(end-start)*100,2);rows.append(x)
print(json.dumps({'schema':'aura-audio-all-TID-nice-readonly-1','actual_seconds':end-start,'before':before,'after':status(),'threads':sorted(rows,key=lambda x:-x['cpu_percent']),'nice_or_scheduler_or_source_changed':False,'audio_or_names_or_scores_or_private_args_exported':False}))
