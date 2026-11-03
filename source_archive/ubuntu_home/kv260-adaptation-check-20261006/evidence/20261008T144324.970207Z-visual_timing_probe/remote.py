"""No ARM or COMMIT: measure coordinate ages, register overhead and CPU inference."""
import json,time,statistics,sys
from pathlib import Path
sys.path.insert(0,'/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
from common import *
from vsrv_driver import VSRVDriver
def stats(v):
 s=sorted(v);return {'n':len(v),'median_ms':statistics.median(s),'p95_ms':s[min(len(s)-1,int(.95*len(s)))],'max_ms':max(s)}
guard();check_runtime();assert active()==[APP]
root=Path('/home/root/aura-realtime-vision-20261007');current=json.loads((root/'current.json').read_text())
status_path=Path(current['run_root'])/'status.json';meta=json.loads(status_path.read_text())
assert meta['boot_id']==BOOT and not meta['stopped'] and not meta['error']
with open_registers() as io:
 d=VSRVDriver(io,0x14da0e60,BOOT);before=d.status();assert before['flags']==0 and before['lease_left_ms']==0
 reads=[];statuses=[]
 for _ in range(20):
  t=time.monotonic();io.read(0x0c);reads.append((time.monotonic()-t)*1000)
  t=time.monotonic();d.status();statuses.append((time.monotonic()-t)*1000)
 after=d.status();assert after['flags']==0 and after['lease_left_ms']==0
p=Path(meta['control_observation_path']);ages=[];at_publish=[];gaps=[];previous=None;last=None;start=time.monotonic()
while time.monotonic()-start<5:
 s=json.loads(p.read_text());now=time.monotonic();snap=s.get('snapshot')
 if snap:
  ages.append((now-snap['observed_time'])*1000)
  if snap['frame_id']!=last:
   at_publish.append((s['publication_time']-snap['observed_time'])*1000)
   if previous is not None:gaps.append((s['publication_time']-previous)*1000)
   previous=s['publication_time'];last=snap['frame_id']
 time.sleep(.005)
sys.path.insert(0,'/home/root/aura-adaptation-check-20261006') if False else None
sys.path.insert(0,str(Path(current['release'])))
from realtime_vision import detector
import cv2
model=Path('/home/root/aura-adaptation-20261006/identity');net=detector(model)
image=cv2.imread(str(model/'reference/lena.jpg'));bench=[]
for threads in (1,2,4):
 cv2.setNumThreads(threads);net.detect(image);times=[];counts=[]
 for _ in range(8):
  t=time.monotonic();faces=net.detect(image);times.append((time.monotonic()-t)*1000);counts.append(len(faces))
 bench.append({'threads':threads,'timing':stats(times),'face_counts':counts})
latest=json.loads(status_path.read_text())
print(json.dumps({'scope':'TIMING_PROBE_NO_PWM_COMMANDS','pid':current['pid'],'epoch':meta['epoch'],
 'native_read':stats(reads),'driver_status':stats(statuses),'source_age':stats(ages),'age_at_publication':stats(at_publish),'publication_gap':stats(gaps),'over250':sum(a>250 for a in ages),'cpu_thread_trials':bench,'last_error':latest['error'],'last_stopped':latest['stopped'],'stop_status':after}))
