"""Bounded 30-second observation of existing business; submit no model jobs."""
import json,os,subprocess,time,urllib.request
from pathlib import Path
CU=Path('/sys/devices/platform/axi/axi:zyxclmm_drm/CU.3.auto')
GP=Path('/sys/kernel/debug/mali')
OP=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def fetch(port,path):
    with OP.open('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
def state():
    u=fetch(8783,'/api/state');h=fetch(8790,'/health');s=h['dpu_schedule'];i=h['identity']
    return {'phase':u['phase'],'playing':u['playing'],'page':u.get('ui_page'),'handsfree':{k:u.get('handsfree_dialogue',{}).get(k) for k in ('enabled','state','microphone_open')},'following':u.get('manual_pan',{}).get('automatic_following'),'camera':{k:h.get(k) for k in ('pid','capture_frames','detected_frames','capture_hz','detection_hz','preview_hz')},'primary_overruns':s['primary_period_overruns'],'optional':{k:{n:v.get(n) for n in ('calls','overruns','native_completed')} for k,v in s['optional'].items()},'sface_completed':i['feature_inference']['completed'],'face_processed':i['face_targets']['processed']}
def cpu():
    return {f[0]:[int(v) for v in f[1:9]] for line in Path('/proc/stat').read_text().splitlines() if (f:=line.split()) and f[0].startswith('cpu')}
def memory():
    keys=('MemTotal','MemFree','MemAvailable','Buffers','Cached','Shmem','Slab','SReclaimable','SwapTotal','SwapFree','CmaTotal','CmaFree')
    return {k:int(v.split()[0]) for l in Path('/proc/meminfo').read_text().splitlines() for k,v in [l.split(':',1)] if k in keys}
def stat():return [int(v) for v in (CU/'stat').read_text().split()]
def gpu():
    return {n:int((GP/n).read_text()) for n in ('utilization_pp','utilization_gp','utilization_gp_pp') if (GP/n).exists()}
def busy(a,b):
    total=sum(b)-sum(a)
    return 100*(total-(b[3]+b[4]-a[3]-a[4]))/total if total else None
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert 'DPUCZDX8G' in (CU/'cu_info').read_text() and (CU/'base_paddr').read_text().strip()=='0xa0010000'
a=stat();sa=state();time.sleep(1.5);sb=state();b=stat()
assert len(a)==len(b)==8 and a[0]==b[0] and sb['camera']['detected_frames']-sa['camera']['detected_frames']>=5,'Another collector may be active; leave counters untouched'
guard=subprocess.Popen(['python3','-B','-c',"import time;from pathlib import Path;time.sleep(45);Path("+repr(str(CU/'stats_end'))+").read_text()"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
report={'boot_id':boot,'scope':'CURRENT_BUSINESS_30_SECONDS_NO_SYNTHETIC_INPUT','collector_inactive_before':True,'before':sb,'samples':[]}
try:
    (CU/'stats_begin').read_text();time.sleep(1.1)
    c0=cpu();d0=stat();previous=c0;start=time.monotonic()
    for i in range(30):
        time.sleep(max(0,start+i+1-time.monotonic()));c=cpu()
        report['samples'].append({'seconds':time.monotonic()-start,'cpu':{k:busy(previous[k],v) for k,v in c.items()},'memory_kib':memory(),'dpu':stat(),'gpu':gpu()});previous=c
    duration=time.monotonic()-start;after=state();d1=report['samples'][-1]['dpu']
    report.update(duration_s=duration,after=after,cpu_percent={k:busy(c0[k],v) for k,v in c.items()},dpu_completed=d1[0]-d0[0],gpu_memory=(GP/'gpu_memory').read_text(),cpu_count=os.cpu_count())
finally:
    (CU/'stats_end').read_text();guard.terminate();guard.wait(timeout=3)
    a=stat();sa=state();time.sleep(1.5);sb=state();b=stat()
    report['collector_stopped_after']=a[0]==b[0] and sb['camera']['detected_frames']-sa['camera']['detected_frames']>=5
    report['boot_unchanged']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
print(json.dumps(report))
