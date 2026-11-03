"""Finite read-only face-source audit; never opens MMIO or issues commands."""
import collections,http.client,json,math,statistics,time,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
def manual():return get(8783,'/api/state')['manual_pan']
before=manual();assert not before['automatic_following'] and before['state']=='READY'
assert before['readback']['flags']==0 and before['readback']['lease_left_ms']==0
h0=get(8790,'/health');assert not h0['dpu_schedule']['owner_fenced']
connection=http.client.HTTPConnection('127.0.0.1',8790,timeout=.5)
rows=[];began=time.monotonic()
connection.request('GET','/v1/motion/face-stream?duration_ms=10000');response=connection.getresponse()
assert response.status==200,('Single-reader source busy',response.status)
while time.monotonic()-began<11:
 raw=response.readline(8193)
 if not raw:break
 assert len(raw)<=8192 and raw.endswith(b'\n')
 p=json.loads(raw);now=round(time.monotonic()*1000);track=p.get('face_tracking') or {}
 rows.append(dict(arrival_mono_ms=now,state=p['state'],fid=p.get('source_frame_id'),stamp=p.get('source_mono_ms'),
  reason=track.get('reason'),elapsed_ms=track.get('elapsed_ms'),snapshot_wait_ms=track.get('snapshot_wait_ms'),
  anchor_age_ms=p.get('face_detection_age_ms'),tracking_version=track.get('version')))
connection.close();after=manual();h1=get(8790,'/health')
fields=('flags','lease_left_ms','width_us','target_us','ack_seq','epoch','session')
unchanged=(not after['automatic_following'] and after['state']=='READY' and all(before['readback'][k]==after['readback'][k] for k in fields))
assert unchanged,'Read-only audit observed an external motor state change'
ready=[r for r in rows if r['state']=='READY' and type(r['stamp']) is int]
unique=[]
for row in ready:
 if not unique or (row['fid'],row['stamp'])!=(unique[-1]['fid'],unique[-1]['stamp']):unique.append(row)
def stats(values):
 return dict(count=len(values),median=round(statistics.median(values),3),p95=round(sorted(values)[max(0,math.ceil(.95*len(values))-1)],3),maximum=max(values)) if values else dict(count=0)
gaps=[b['arrival_mono_ms']-a['arrival_mono_ms'] for a,b in zip(unique,unique[1:])]
summary=dict(status='READ_ONLY_FACE_SOURCE_AUDIT',duration_s=round(time.monotonic()-began,3),packets=len(rows),distinct_ready_sources=len(unique),
 states=dict(collections.Counter(r['state'] for r in rows)),tracking_reasons=dict(collections.Counter(r['reason'] for r in rows)),
 ready_source_age_ms=stats([r['arrival_mono_ms']-r['stamp'] for r in ready]),ready_arrival_gap_ms=stats(gaps),
 ready_gaps_over_200ms=sum(g>200 for g in gaps),ready_gaps_at_least_250ms=sum(g>=250 for g in gaps),
 tracking_compute_ms=stats([r['elapsed_ms'] for r in rows if type(r['elapsed_ms']) in (int,float)]),
 camera_pid=h1['pid'],identity_ready=h1['identity']['ready'],motor_stopped_unchanged=unchanged,ARM=0,COMMIT=0,MMIO_opened=False,
 primary_overruns_before=h0['dpu_schedule']['primary_period_overruns'],primary_overruns_after=h1['dpu_schedule']['primary_period_overruns'])
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/read-only-input-audits');root.mkdir(exist_ok=True)
path=root/('input-'+str(time.monotonic_ns())+'.json')
with path.open('x') as f:json.dump(dict(summary=summary,rows=rows),f)
summary['board_evidence']=str(path);print(json.dumps(summary))
