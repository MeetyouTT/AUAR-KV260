
import json,subprocess,urllib.request
from pathlib import Path
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
def run(args):return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8).stdout
report={'status':'POST_ROLLBACK_DIAGNOSE','units':{}}
for unit in ['aura-camera-ui.service','aura-avatar-ui.service']:
 text=run(['journalctl','-u',unit,'--since','8 minutes ago','-n','160','--no-pager','-o','cat'])
 # Keep only startup errors and traceback lines; omit conversation content.
 lines=[line for line in text.splitlines() if any(s in line for s in ['Traceback','Error','FAILED','error','File "','Exception','Mismatch','mismatch','No such','Started','Starting','Terminated'])]
 report['units'][unit]={'state':run(['systemctl','is-active',unit]).strip(),'working_directory':run(['systemctl','show',unit,'-p','WorkingDirectory','--value']).strip(),'startup_errors':lines[-30:]}
for name,port,path in [('camera',8790,'/health'),('ui',8783,'/api/state')]:
 try:
  with urllib.request.urlopen('http://127.0.0.1:%d%s'%(port,path),timeout=3) as response:value=json.load(response)
  fields=['pid','identity_recognition','camera_error','detector_error','identity','dpu_schedule'] if name=='camera' else ['ui_page','phase','playing','audio_output_state','automatic_conversation']
  report[name]={k:value.get(k) for k in fields}
 except Exception as exc:report[name]={'error':str(exc)[:160]}
print(json.dumps(report),flush=True)
