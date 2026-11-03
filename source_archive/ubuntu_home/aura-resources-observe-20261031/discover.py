"""Read only hardware, service and API metadata; omit user content."""
import json,subprocess,urllib.request
from pathlib import Path

def read(p):
    try:return Path(p).read_text().strip()
    except OSError as e:return {'error':type(e).__name__}
def api(port,path):
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
    except Exception as e:return {'probe_error':type(e).__name__}
u=api(8783,'/api/state');h=api(8790,'/health')
ui={k:u.get(k) for k in ('phase','playing','audio_output_state')}
for k in ('handsfree_dialogue','manual_pan','local_recording','board_business','automatic_listening'):
    v=u.get(k,{})
    ui[k]={n:v[n] for n in ('enabled','state','microphone_open','automatic_following','pending','capture_process','frontend_process','revision') if n in v} if isinstance(v,dict) else v
gpu={str(p):read(p) for p in Path('/sys/kernel/debug/mali').glob('*') if p.name in ('version','utilization_pp','utilization_gp','utilization_gp_pp','gpu_memory')}
cus={}
for p in Path('/sys/devices/platform').glob('**/CU.*'):
    if p.is_dir():cus[str(p)]={n:read(p/n) for n in ('cu_info','base_paddr','stat')}
services={}
for unit in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service'):
    p=subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','MainPID','-p','ControlGroup'],stdout=subprocess.PIPE,text=True,timeout=5)
    services[unit]=p.stdout
result={'boot_id':read('/proc/sys/kernel/random/boot_id'),'ui':ui,'ui_top_keys':list(u),'health_top_keys':list(h),'services':services,'gpu':gpu,'compute_units':cus,'meminfo':read('/proc/meminfo'),'cpu_online':read('/sys/devices/system/cpu/online'),'devfreq':list(str(p) for p in Path('/sys/class/devfreq').glob('*')),'thermal':{str(p):read(p) for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')}}
print(json.dumps(result))
