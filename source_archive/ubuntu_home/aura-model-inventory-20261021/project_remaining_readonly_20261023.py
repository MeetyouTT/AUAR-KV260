"""Read-only project status; no images, audio, names or database contents."""
import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path

BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
UNIT='a29082bae1d382d7a43505d5a1d3a51fa2203081423755900e9d72836385e343'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()==UNIT
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
services={}
for name in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service'):
 s=subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','NRestarts','-p','Result'],timeout=4).decode()
 services[name]=dict(line.split('=',1) for line in s.splitlines() if '=' in line)
h=get(8790,'/health');i=h.get('identity') or {};f=i.get('face_targets') or {}
ui=get(8783,'/api/state');pan=ui.get('manual_pan') or {}
def stat():
 c=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));p={}
 for q in Path('/proc').iterdir():
  if not q.name.isdigit():continue
  try:
   a=(q/'stat').read_text().rsplit(')',1)[1].split();p[int(q.name)]=(int(a[1]),int(a[11])+int(a[12]),int(a[19]))
  except (OSError,ValueError,IndexError):pass
 return c,p
a,pa=stat();start=time.monotonic();time.sleep(3);b,pb=stat();duration=time.monotonic()-start
total=sum(b)-sum(a);idle=(b[3]+b[4])-(a[3]+a[4]);groups={}
for name,s in services.items():
 ids={int(s['MainPID'])}
 while True:
  extra={pid for pid,v in pb.items() if v[0] in ids}-ids
  if not extra:break
  ids.update(extra)
 valid=[pid for pid in ids if pid in pa and pid in pb and pa[pid][2]==pb[pid][2]]
 groups[name]={'pids':sorted(ids),'cpu_percent_of_board':100*sum(pb[pid][1]-pa[pid][1] for pid in valid)/total}
out={'read_only':True,'boot':BOOT,'unit_sha256':UNIT,'board_uptime_s':float(Path('/proc/uptime').read_text().split()[0]),
 'services':services,'camera':{k:h.get(k) for k in ('pid','capture_hz','detection_hz')},
 'schedule':h.get('dpu_schedule'),'identity':{'backend':i.get('backend'),'ready':i.get('ready'),'has_error':bool(i.get('error')),
 'feature_inference':i.get('feature_inference')},
 'faces':{k:f.get(k) for k in ('backend','source_age_ms','freshness_metrics')},
 'ui':{k:ui.get(k) for k in ('phase','playing','paused','audio_output_state')},
 'manual_pan':{k:pan.get(k) for k in ('state','ready','enabled','reason','fault')},
 'cpu_sample':{'duration_s':duration,'cpu_percent_of_board':100*(total-idle)/total,'process_groups':groups}}
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()==UNIT
print(json.dumps(out))
