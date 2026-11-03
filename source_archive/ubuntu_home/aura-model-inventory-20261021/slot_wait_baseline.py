import hashlib,json,subprocess,sys,time,urllib.request
from pathlib import Path
BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
UNIT_SHA='e893930d9f51540223e849c36409fdc225fe7cbb347cdc1cb75166d8271e83f7'
ROOT=Path('/home/root/aura-yunet-slot-wait-20261023/baseline')
def health():
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with op.open('http://127.0.0.1:8790/health',timeout=3) as response:return json.load(response)
def cpu():
 a=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));return sum(a),a[3]+a[4]
def save(d):
 tmp=ROOT/'report.tmp';tmp.write_text(json.dumps(d));tmp.replace(ROOT/'report.json')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()==UNIT_SHA
ROOT.mkdir(parents=True,exist_ok=True)
if sys.argv[1:]==['--run']:
 d={'scope':'READ_ONLY_SLOT_WAIT_BASELINE_60S','complete':False,'passed':False,'samples':[]}
 save(d)
 try:
  first=health();face=first['identity']['face_targets'];started=time.monotonic();c1=cpu()
  for index in range(13):
   h=health();f=h['identity']['face_targets'];s=h['dpu_schedule']
   assert h['pid']==first['pid'] and not h['camera_error'] and not h['detector_error']
   assert f['backend']=='DPU_YUNET_INT8' and not s['optional']['yunet']['disabled']
   assert s['optional']['yunet']['overruns']==first['dpu_schedule']['optional']['yunet']['overruns']
   d['samples'].append({'elapsed_s':time.monotonic()-started,'detected_frames':h['detected_frames'],
    'face_processed':f['processed'],'source_age_ms':f['source_age_ms'],
    'skipped':s['optional']['yunet']['skipped'],
    'native_completed':s['optional_diagnostics']['counters']['yunet']['native_completed'],
    'freshness_counters':f['freshness_metrics']['counters']})
   save(d)
   if index<12:time.sleep(max(0,started+(index+1)*5-time.monotonic()))
  last=health();end=time.monotonic();c2=cpu();dt=end-started;lf=last['identity']['face_targets']
  total=c2[0]-c1[0]
  d.update(passed=True,camera_pid=first['pid'],observed_seconds=dt,yolo_hz=(last['detected_frames']-first['detected_frames'])/dt,
   face_publish_hz=(lf['processed']-face['processed'])/dt,cpu_percent_of_board=100*(1-(c2[1]-c1[1])/total),
   gap_intervals_before=face['freshness_metrics']['counters']['observed_gap_intervals'],
   gap_intervals_after=lf['freshness_metrics']['counters']['observed_gap_intervals'],
   native_completed_delta=last['dpu_schedule']['optional_diagnostics']['counters']['yunet']['native_completed']-first['dpu_schedule']['optional_diagnostics']['counters']['yunet']['native_completed'],
   final_yunet=last['dpu_schedule']['optional']['yunet'],final_freshness=lf['freshness_metrics'])
 except Exception as e:d['error']=type(e).__name__+': '+str(e)[:200]
 finally:d['complete']=True;save(d)
 print(json.dumps({'complete':d['complete'],'passed':d['passed']}))
else:
 assert sys.argv[1:]==[] and not (ROOT/'report.json').exists()
 source=Path(__file__).resolve()
 r=subprocess.run(['systemd-run','--unit=aura-slot-wait-baseline','--property=RuntimeMaxSec=90',
                   '/usr/bin/python3','-B',str(source),'--run'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
 assert r.returncode==0,r.stdout.decode(errors='replace')[-300:]
 print(json.dumps({'started':True,'report':str(ROOT/'report.json'),'read_only_business':True}))
