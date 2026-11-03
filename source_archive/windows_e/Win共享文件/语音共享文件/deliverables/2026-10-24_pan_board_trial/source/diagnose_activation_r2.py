import json,subprocess,urllib.request
from pathlib import Path
result={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'services':{}}
for unit in ['aura-camera-ui.service','aura-avatar-ui.service','aura-pan-vsrv2-1236ccf4-r2-activation.service']:
 p=subprocess.run(['systemctl','show',unit,'--property=ActiveState,SubState,MainPID,Result,ExecMainStatus'],capture_output=True,text=True)
 result['services'][unit]=dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x)
 log=subprocess.run(['journalctl','-u',unit,'-n','12','--no-pager','-o','cat'],capture_output=True,text=True)
 result[unit+'-diagnostic']=[x for x in log.stdout.splitlines() if any(t in x for t in ['Error','Traceback','assert','Runtime','Failed','checkpoint','native','VART','XRT'])][-8:]
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for port,path in [(8790,'/health'),(8783,'/api/state')]:
 try:
  with op.open('http://127.0.0.1:'+str(port)+path,timeout=2) as response:d=json.load(response)
  result[str(port)]={k:d.get(k) for k in ['pid','phase','detected_frames','detection_hz','audio_output_state']}
 except Exception as error:result[str(port)]=str(error)
print(json.dumps(result))
