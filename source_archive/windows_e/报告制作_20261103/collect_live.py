from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,sys,hashlib,time
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
def remote(code,timeout=30):
 r=subprocess.run(['ssh','-o','BatchMode=yes','aura-kv260','python3 -'],input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if r.returncode:print(r.stderr.decode(errors='replace')[:1500])
 return r.stdout
code=r'''import json,urllib.request,sys
try:
 d=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=8))
 print(json.dumps(d,ensure_ascii=False))
except Exception as e:print(json.dumps({'error':str(e)}))
'''
raw=remote(code);d=json.loads(raw)
print('GUI top keys',list(d));(ROOT/'tmp_gui.json').write_bytes(raw)
# Screenshot captures the current X11 root; it does not navigate or change UI.
code=r'''import os,sys
os.environ['DISPLAY']=':0'
import gi
gi.require_version('Gdk','3.0')
from gi.repository import Gdk
w=Gdk.get_default_root_window()
pix=Gdk.pixbuf_get_from_window(w,0,0,w.get_width(),w.get_height())
ok,data=pix.save_to_bufferv('png',[],[])
sys.stdout.buffer.write(data)
'''
raw=remote(code)
if raw.startswith(b'\x89PNG'):
 (ROOT/'figures/board_x11_live.png').write_bytes(raw)
 print('screenshot',len(raw))
else:print('screenshot failed',raw[:100])
code=r'''from pathlib import Path
import json,time,urllib.request,subprocess,threading
def health(port,path):
 try:return json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3))
 except Exception as e:return {'error':str(e)}
def cpu():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
def sample():
 m={a:int(b.strip().split()[0]) for a,b in (s.split(':',1) for s in Path('/proc/meminfo').read_text().splitlines())}
 h=health(8790,'/health')
 return {'t':time.monotonic(),'cpu':cpu(),'mem_total_kib':m['MemTotal'],'mem_available_kib':m['MemAvailable'],
 'camera':{k:h.get(k) for k in ['capture_frames','detected_frames','preview_frames','capture_hz','detection_hz','capture_age_ms','observation_age_ms','last_inference_ms','native_primary_deferred','motion_command_emitted','camera_error','detector_error']},
 'schedule':h.get('dpu_schedule',{}),'identity':{k:v for k,v in h.get('identity',{}).items() if k in ['status','model','completed','count']}}
ping={}
def measure_ping():
 r=subprocess.run(['ping','-n','-c','30','-i','0.2','-W','2','192.168.50.1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 ping.update({'returncode':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace')})
th=threading.Thread(target=measure_ping);th.start()
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
first=health(8783,'/api/state')
rows=[];start=time.monotonic()
for i in range(61):
 target=start+i
 if target>time.monotonic():time.sleep(target-time.monotonic())
 rows.append(sample())
th.join()
last=health(8783,'/api/state')
def selected(o):
 allowed=['page','current_page','state','mode','ui_state','listening','listening_enabled','handsfree','pan','motion','startup','production','readiness','audio','speaker','camera','render','native_yuki_egl','performance']
 return {k:v for k,v in o.items() if k in allowed}
out={'boot_id':boot,'boot_id_end':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'board_os_time':subprocess.getoutput('date -u +%FT%TZ'),'monotonic_duration_s':rows[-1]['t']-rows[0]['t'],
 'scope':'read-only natural workload; no service, model, page, listening or motion command changes',
 'gui_start_keys':list(first),'gui_end_keys':list(last),'gui_start':selected(first),'gui_end':selected(last),'samples':rows,'ping':ping}
print(json.dumps(out,ensure_ascii=False))
'''
t0=datetime.now(timezone.utc).isoformat();raw=remote(code,90);t1=datetime.now(timezone.utc).isoformat()
d=json.loads(raw);d.update(host_start_utc=t0,host_end_utc=t1)
(ROOT/'evidence/live_board_samples.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
print('duration',d['monotonic_duration_s']);print(d['ping']['stdout'][-350:]);print('first sample',json.dumps(d['samples'][0],ensure_ascii=False)[:1100])
