"""Read existing status and firmware identity before touching motion hardware."""
import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
def get(port,path):
 try:
  with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
 except Exception as e:return {'error':type(e).__name__}
def run(a):
 p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8);return {'rc':p.returncode,'text':p.stdout[-18000:]}
u=get(8783,'/api/state');h=get(8790,'/health')
d={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().split()[0],'ui':{k:u.get(k) for k in ['phase','audio_output_state','playing','portrait_offload','avatar_display']},'manual_pan':u.get('manual_pan'),'handsfree':{k:u.get('handsfree_dialogue',{}).get(k) for k in ['enabled','microphone_open','state','reason','error']},'camera':{k:h.get(k) for k in ['pid','capture_hz','detection_hz','capture_frames','detected_frames','camera_error','detector_error','identity_recognition']},'identity':{k:h.get('identity',{}).get(k) for k in ['ready','backend','error']},'services':run(['systemctl','show','aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts','-p','ExecStart']),'fpga':{},'xclbins':{},'device_tree':{}}
for p in Path('/sys/class/fpga_manager').glob('*'):
 d['fpga'][p.name]={k:(p/k).read_text().strip() for k in ['name','state'] if (p/k).exists()}
fw=Path('/proc/device-tree/fpga-full/firmware-name')
d['firmware_name']=fw.read_bytes().rstrip(b'\0').decode() if fw.exists() else None
for p in Path('/sys/bus/platform/devices').glob('*'):
 for name in ['xclbinid','xclbin_uuid']:
  q=p/name
  if q.exists():
   try:d['xclbins'][str(q)]=q.read_text().strip()
   except OSError:pass
for p in Path('/proc/device-tree').rglob('*'):
 if any(k in p.name.lower() for k in ['servo','vsrv','motion']):d['device_tree'][str(p)]={k:(p/k).read_bytes().hex() for k in ['compatible','reg'] if (p/k).exists()}
d['iomem_motion_lines']=[s for s in Path('/proc/iomem').read_text().splitlines() if any(k in s.lower() for k in ['a001','a000','servo','vsrv','motion'])]
print(json.dumps(d))
