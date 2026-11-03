import base64,hashlib,json,subprocess,urllib.request
from pathlib import Path
def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
 return {'returncode':p.returncode,'output':p.stdout[-2500:]}
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
report={'status':'READ_ONLY_PAN_FOLLOW_PRECHECK','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'fpga_state':Path('/sys/class/fpga_manager/fpga0/state').read_text().strip(),
 'firmware_name':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
 'vsrv_lock_exists':Path('/run/aura-vsrv.lock').exists(),'motion_command_emitted':False,'artifacts':{}}
for unit in ['aura-camera-ui.service','aura-avatar-ui.service']:
 report[unit]=run(['systemctl','show',unit,'-p','ActiveState','-p','MainPID','-p','WorkingDirectory','--value'])
for name,port,path in [('camera',8790,'/health'),('ui',8783,'/api/state')]:
 try:
  with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as r:value=json.load(r)
  keys=['pid','camera_epoch','service_epoch','identity_recognition','camera_error','detector_error','observation_age_ms','detection_hz'] if name=='camera' else ['ui_page','phase','playing','automatic_conversation']
  report[name]={k:value.get(k) for k in keys}
 except Exception as exc:report[name]={'error':str(exc)}
working=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','WorkingDirectory','--value'],text=True).strip()
p=Path(working)/'board/vision/ui_camera_service.py';raw=p.read_bytes()
report['artifacts']['actual-camera-service.py']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
print(json.dumps(report),flush=True)
