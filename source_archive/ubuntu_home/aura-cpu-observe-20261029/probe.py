"""Read-only 15-second CPU observation under the existing business workload."""
import json,time,urllib.request
from pathlib import Path

def fetch(port,path):
    try:
        with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as response:
            return json.load(response)
    except Exception as error:
        return {'probe_error':type(error).__name__}

def state():
    u=fetch(8783,'/api/state');h=fetch(8790,'/health')
    v={k:u.get(k) for k in ('phase','playing','audio_output_state')}
    for k,f in (('handsfree_dialogue','enabled'),('manual_pan','automatic_following'),('local_recording','state')):
        v[k]=u.get(k,{}).get(f)
    counters={}
    def walk(value,path=''):
        if isinstance(value,dict):
            for k,w in value.items():
                p=path+'.'+k
                if type(w) in (int,float) and k in ('pid','captured_frames','detected_frames','sface_completed','native_completed','completed','calls','overruns','primary_period_overruns','yolo_hz'):
                    counters[p]=w
                elif isinstance(w,dict):walk(w,p)
    walk(h)
    return {'ui':v,'camera_counters':counters}

def cpu():
    result={}
    for line in Path('/proc/stat').read_text().splitlines():
        parts=line.split()
        if parts and parts[0].startswith('cpu'):
            a=[int(v) for v in parts[1:9]];result[parts[0]]=(sum(a),a[3]+a[4])
    return result

def thermal():
    return {p.parent.name:int(p.read_text())/1000 for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')}

before=state();boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
began=time.monotonic();previous=cpu();samples=[]
for i in range(15):
    time.sleep(max(0,began+i+1-time.monotonic()));current=cpu();busy={}
    for k,v in current.items():
        if k in previous:
            total=v[0]-previous[k][0];idle=v[1]-previous[k][1]
            busy[k]=round(100*(total-idle)/total,3) if total>0 else None
    samples.append({'elapsed_s':round(time.monotonic()-began,3),'cpu_busy_percent':busy,'temperature_c':thermal()});previous=current
after=state()
memory={}
for line in Path('/proc/meminfo').read_text().splitlines():
    k,value=line.split(':',1)
    if k in ('MemTotal','MemAvailable','SwapTotal','SwapFree'):memory[k+'_kib']=int(value.split()[0])
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
print(json.dumps({'scope':'READ_ONLY_CURRENT_WORKLOAD_NOT_FULL_LOAD_TEST','boot_id':boot,'duration_s':round(time.monotonic()-began,3),'before':before,'after':after,'samples':samples,'memory':memory,'cpu_definition':'100% means all online CPUs busy; excludes idle and iowait; first eight /proc/stat fields avoid guest double count','audio_or_motion_commands':0}))
