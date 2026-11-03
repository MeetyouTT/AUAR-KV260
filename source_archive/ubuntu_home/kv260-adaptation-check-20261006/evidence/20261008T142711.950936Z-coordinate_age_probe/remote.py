import json,time,statistics
from pathlib import Path
root=Path('/home/root/aura-realtime-vision-20261007')
c=json.loads((root/'current.json').read_text());p=Path(c['run_root'])/'status.json'
ages=[];updates=[];frames=[];last=None;t0=time.monotonic();worst=None
while time.monotonic()-t0<5:
 s=json.loads(p.read_text());now=time.monotonic();snapshot=s.get('snapshot')
 if snapshot:
  age=(now-snapshot['observed_time'])*1000;ages.append(age)
  if worst is None or age>worst['age_ms']:
   worst={'age_ms':age,'status_observation':s.get('observation'),'capture_age_ms':s.get('capture_age_ms'),'capture_hz':s.get('capture_hz'),'detection_hz':s.get('detection_hz'),'detection_median_ms':s.get('detection_median_ms'),'detection_age_p95_ms':s.get('observation_age_p95_ms')}
  fid=snapshot['frame_id']
  if last!=fid:updates.append(now);frames.append(fid);last=fid
 time.sleep(.02)
gaps=[(b-a)*1000 for a,b in zip(updates,updates[1:])]
print(json.dumps({'scope':'READ_ONLY_COORDINATE_AGE_PROBE','pid':c['pid'],'epoch':s['epoch'],
 'samples':len(ages),'age_median_ms':statistics.median(ages),'age_max_ms':max(ages),
 'samples_above_250ms':sum(x>250 for x in ages),'samples_above_400ms':sum(x>400 for x in ages),
 'detection_update_gap_max_ms':max(gaps),'detection_updates':len(updates),'worst':worst,
 'last_error':s['error'],'last_stopped':s['stopped']}))
