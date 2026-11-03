"""Inspect safe counter metadata and filtered application status."""
import json,urllib.request
from pathlib import Path
def read(p):
    try:return Path(p).read_text().strip()
    except OSError as e:return {'error':type(e).__name__}
def fetch(port,path):
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
u=fetch(8783,'/api/state');h=fetch(8790,'/health')
def meta(v):
    if not isinstance(v,dict):return None
    return {k:w for k,w in v.items() if isinstance(w,(int,float,bool)) or (k in ('state','phase','backend','revision','mode','kind','status','owner') and isinstance(w,str))}
identity=h.get('identity',{});sched=h.get('dpu_schedule',{})
result={'gpu_debug_nodes':[p.name for p in Path('/sys/kernel/debug/mali').iterdir()],
 'mali_parameters':{p.name:read(p) for p in Path('/sys/module/mali/parameters').glob('*') if any(k in p.name.lower() for k in ('util','freq','power','poll','profil'))},
 'identity':{k:meta(identity.get(k)) for k in ('face_targets','feature_inference','face_detector','status')},
 'schedule':meta(sched),'schedule_keys':list(sched),'optional':{k:meta(v) for k,v in sched.get('optional',{}).items()},
 'ui':{k:meta(u.get(k)) for k in ('handsfree_dialogue','local_recording','board_processing','board_business','runtime_faults','avatar_renderer','avatar_display','native_canvas','automatic_conversation')},
 'cpu_frequency_khz':{p.parent.name:read(p) for p in Path('/sys/devices/system/cpu').glob('cpu*/cpufreq/scaling_cur_freq')}}
print(json.dumps(result))
