"""Read-only camera/UI freshness and process load samples, without images."""
import json,subprocess,time,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as r:return json.load(r)
rows=[]
for _ in range(12):
 start=time.monotonic();h=get(8790,'/health');u=get(8783,'/api/state');v=get(8790,'/v1/ui/status')
 rows.append({'mono':time.monotonic(),'latency_ms':round((time.monotonic()-start)*1000,1),
  'health':{k:z for k,z in h.items() if k!='identity' and k!='dpu_schedule' and not isinstance(z,dict)},
  'face':h['identity']['face_targets'],
  'schedule':{'primary':h['dpu_schedule']['primary_period_overruns'],'fenced':h['dpu_schedule']['owner_fenced']},
  'ui':{k:z for k,z in u.items() if k in ('phase','error','vision','camera','vision_status','vision_error','vision_frame','camera_error','preview','raw_frame','raw_preview')},
  'ui_runtime':u.get('ui_runtime'),'ui_layer':u.get('ui_layer'),'vision_module':v.get('modules',{}).get('vision'),
  'pan_state':u['manual_pan']['state'],'pan_readback':u['manual_pan']['readback']})
 time.sleep(max(0,.5-(time.monotonic()-start)))
logs=subprocess.check_output(['journalctl','-u','aura-camera-ui.service','-u','aura-avatar-ui.service','-n','35','--no-pager','-o','cat'],text=True)
process=subprocess.check_output(['ps','-eLo','pid,tid,pcpu,comm','--sort=-pcpu'],text=True).splitlines()[:18]
print(json.dumps({'samples':rows,'recent_logs':logs[-7000:],'cpu':process,'load':Path('/proc/loadavg').read_text().strip(),'register_writes':0}))
