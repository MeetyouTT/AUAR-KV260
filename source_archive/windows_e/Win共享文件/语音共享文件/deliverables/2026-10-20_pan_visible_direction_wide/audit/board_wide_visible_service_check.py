"""Read current service availability without restarting anything."""
import json,subprocess,urllib.request
from pathlib import Path
def unit(name):
 return {k:subprocess.check_output(['systemctl','show',name,'-p',k,'--value'],text=True,timeout=5).strip()
         for k in ['ActiveState','SubState','MainPID','WorkingDirectory']}
value={'transaction_exists':Path('/home/root/aura-pan-follow-20261020/visible-direction-wide-01').exists(),
 'camera_unit':unit('aura-camera-ui.service'),'gui_unit':unit('aura-avatar-ui.service')}
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for name,port,path,keys in [('camera',8790,'/health',['identity_recognition','camera_error','detector_error','detection_hz']),
 ('gui',8783,'/api/state',['phase','playing','automatic_conversation'])]:
 try:
  with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as r:state=json.load(r)
  value[name]={k:state.get(k) for k in keys}
 except Exception as exc:value[name]={'error':type(exc).__name__+': '+str(exc)}
print(json.dumps(value),flush=True)
