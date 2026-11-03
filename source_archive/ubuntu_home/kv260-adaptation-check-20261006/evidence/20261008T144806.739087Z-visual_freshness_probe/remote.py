"""Read-only end-to-end freshness qualification; no register writes."""
import json,time,statistics
from pathlib import Path
root=Path('/home/root/aura-realtime-vision-20261007');c=json.loads((root/'current.json').read_text())
status=Path(c['run_root'])/'status.json';before=json.loads(status.read_text());p=Path(before['control_observation_path'])
assert before['boot_id']=='f7a3ff07-fc20-4804-af12-c314a7a1847a' and before['mirror_horizontal'] and not before['stopped'] and not before['error']
ages=[];pubages=[];queue=[];infer=[];gaps=[];last=None;previous=None;start=time.monotonic()
while time.monotonic()-start<20:
 s=json.loads(p.read_text());now=time.monotonic();snap=s.get('snapshot')
 assert s['epoch']==before['epoch'] and not s['error'] and not s['stopped']
 if snap:
  source=snap['observed_time'];ages.append((now-source)*1000)
  if last!=snap['frame_id']:
   last=snap['frame_id'];pubages.append((s['publication_time']-source)*1000)
   if previous is not None:gaps.append((s['publication_time']-previous)*1000)
   previous=s['publication_time']
   if s.get('inference_started') is not None:
    queue.append((s['inference_started']-source)*1000);infer.append((s['inference_completed']-s['inference_started'])*1000)
 time.sleep(.005)
def stats(v):
 s=sorted(v);return {'n':len(v),'median_ms':statistics.median(v),'p95_ms':s[min(len(s)-1,int(.95*len(s)))],'max_ms':max(v)} if v else None
after=json.loads(status.read_text());assert not after['error'] and not after['stopped']
print(json.dumps({'scope':'READ_ONLY_20S_FRESHNESS_QUALIFICATION','pid':c['pid'],'epoch':before['epoch'],'source_age':stats(ages),
 'age_at_publication':stats(pubages),'capture_to_inference':stats(queue),'inference':stats(infer),'publication_gap':stats(gaps),
 'over230':sum(a>230 for a in ages),'over250':sum(a>250 for a in ages),'passed':max(ages)<230,
 'before_frames':before['detected_frames'],'after_frames':after['detected_frames'],'last_error':after['error']}))
