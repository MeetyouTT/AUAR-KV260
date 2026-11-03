"""Discover supported DPU query interfaces without inference or configuration changes."""
import json,shutil,subprocess,urllib.request
from pathlib import Path
out={}
for name,args in [('query',['xdputil','query']),('status',['xdputil','status'])]:
    if shutil.which(args[0]):
        try:
            p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=12)
            out[name]={'rc':p.returncode,'text':p.stdout[-16000:]}
        except Exception as e:out[name]={'error':str(e)}
out['interfaces']={}
for root in ['/sys/bus/platform/drivers/zocl','/sys/class/drm','/sys/kernel/debug/tracing/events']:
    r=Path(root)
    if not r.exists():continue
    for p in r.glob('**/*'):
        if len(p.parts)-len(r.parts)>4:continue
        if any(x in p.name.lower() for x in ['custat','cu_stat','kds','stat','dpu','zocl','xrt','available_events']):
            out['interfaces'][str(p)]=p.read_text()[:4000] if p.is_file() and p.stat().st_size<8192 else 'directory_or_large'
out['tools']={n:shutil.which(n) for n in ['vaitrace','xrt-smi','xbutil','perf','trace-cmd']}
try:
    with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as r:d=json.load(r)
    out['camera']={k:d.get(k) for k in ['pid','detection_hz','last_inference_ms','camera_error','detector_error','detector']}
except Exception as e:out['camera']={'error':str(e)}
print(json.dumps(out),flush=True)
