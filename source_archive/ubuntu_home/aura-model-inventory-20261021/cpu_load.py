"""Sample CPU use and existing camera telemetry for 15 seconds."""
import json,os,time,urllib.request
from pathlib import Path
hz=os.sysconf('SC_CLK_TCK');ncpu=os.cpu_count()
def snap():
    cpu={}
    for s in Path('/proc/stat').read_text().splitlines():
        if s.startswith('cpu'):
            a=s.split();v=list(map(int,a[1:9]));cpu[a[0]]=(sum(v),v[3],v[4])
    procs={}
    for p in Path('/proc').glob('[0-9]*'):
        try:
            s=(p/'stat').read_text();a=s.split(') ')[1].split();name=s.split('(',1)[1].rsplit(')',1)[0]
            args=(p/'cmdline').read_bytes().decode(errors='replace').split('\0')
            scripts=[Path(x).name for x in args if x.endswith('.py')]
            procs[p.name]=(int(a[11])+int(a[12]),int(a[19]),scripts[0] if scripts else name)
        except (OSError,IndexError):pass
    return time.monotonic(),cpu,procs
first=snap();samples=[]
for i in range(16):
    if i:time.sleep(max(0,first[0]+i-time.monotonic()))
    try:
        with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=1) as r:v=json.load(r)
        samples.append({k:v.get(k) for k in ['pid','detected_frames','detection_hz','last_inference_ms','camera_error','detector_error','observation_age_ms']})
    except Exception as e:samples.append({'error':str(e)})
last=snap();duration=last[0]-first[0];cpus={}
for k,b in last[1].items():
    a=first[1][k];total=b[0]-a[0]
    cpus[k]={'busy_percent':100*(total-(b[1]-a[1])-(b[2]-a[2]))/total,'iowait_percent':100*(b[2]-a[2])/total}
ps=[]
for pid,b in last[2].items():
    a=first[2].get(pid)
    if a and a[1]==b[1]:
        pct=100*(b[0]-a[0])/hz/duration
        ps.append({'pid':int(pid),'name':b[2],'percent_of_one_core':pct,'percent_of_board':pct/ncpu})
out={'duration_seconds':duration,'logical_cpus':ncpu,'cpu':cpus,'processes':sorted(ps,key=lambda x:x['percent_of_one_core'],reverse=True)[:12],'camera_samples':samples,'dpu_interfaces':{}}
for d in Path('/sys/bus/platform/drivers/zocl').glob('*'):
    if not d.is_dir():continue
    for p in d.iterdir():
        if any(t in p.name for t in ['cu_stat','custat','kds','scheduler','xclbin']):
            try:out['dpu_interfaces'][str(p)]=p.read_text()[:6000]
            except (OSError,UnicodeError):pass
p=Path('/sys/kernel/debug/tracing/available_filter_functions')
if p.exists():out['trace_functions']=[s for s in p.read_text().splitlines() if any(t in s.lower() for t in ['zocl','kds_','cu_hls'])][:70]
out['meminfo']=[s for s in Path('/proc/meminfo').read_text().splitlines() if s.split(':')[0] in ['MemTotal','MemAvailable','SwapTotal','SwapFree']]
print(json.dumps(out),flush=True)
