"""Export finite no-PWM test results and coordinates; never images/identity data."""
import base64,gzip,hashlib,json,subprocess,urllib.request
from pathlib import Path

base=Path('/home/root/aura-pan-follow-20261020')
value={'status':'READ_ONLY_AXIS_FINAL_EXPORT','artifacts':{},'transactions':{}}
for number in (1,2,3):
 key='axis-%02d'%number
 root=base/('activation-'+key)
 if not (root/'result.json').exists():continue
 value['transactions'][key]=json.loads((root/'result.json').read_text())['status']
 for name in ['result.json','joint-loaded.json','live-source.jsonl','live-shadow.jsonl','live-shadow.jsonl.summary.json','failure-traceback.txt']:
  path=root/name
  if not path.exists():continue
  raw=path.read_bytes();data=gzip.compress(raw,mtime=0) if name.endswith('.jsonl') else raw
  dest=key+'-'+name+('.gz' if name.endswith('.jsonl') else '')
  value['artifacts'][dest]={'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
def out(args):return subprocess.check_output(args,text=True,timeout=5).strip()
value['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
value['firmware']=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
value['fpga_state']=Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()
value['vart_conf']=Path('/etc/vart.conf').read_text()
for unit in ['aura-camera-ui.service','aura-avatar-ui.service']:
 value[unit]={key:out(['systemctl','show',unit,'-p',key,'--value']) for key in ['ActiveState','MainPID','WorkingDirectory']}
value['camera_motion_entry_active']='tools/board_camera_motion.py' in out(['systemctl','show','aura-camera-ui.service','-p','ExecStart','--value'])
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for name,port,path,keys in [
 ('camera',8790,'/health',['identity_recognition','camera_error','detector_error','detected_frames','observation_age_ms','detection_hz','camera_epoch','service_epoch']),
 ('gui',8783,'/api/state',['ui_page','phase','playing','automatic_conversation']),
 ('motion',8790,'/v1/motion/observation',['protocol_version','source_kind','state','source_frame_id','source_mono_ms','deadline_mono_ms'])]:
 try:
  with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as r:state=json.load(r)
  value[name]={k:state.get(k) for k in keys}
 except Exception as exc:value[name]={'error':str(exc)}
print(json.dumps(value),flush=True)
