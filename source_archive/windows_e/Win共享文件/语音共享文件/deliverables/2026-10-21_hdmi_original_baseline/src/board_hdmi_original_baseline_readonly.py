"""Read original-kernel and USB-hub recovery state after manual power-on."""
import hashlib,json,subprocess,urllib.request
from pathlib import Path
def run(a):
 p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=6)
 return {'rc':p.returncode,'text':p.stdout[-5000:]}
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'version':Path('/proc/version').read_text().strip(),'cmdline':Path('/proc/cmdline').read_text().strip(),'initial_aux_parameter_exists':Path('/sys/module/zynqmp_dpsub/parameters/initial_aux_delay_ms').exists(),'files_modified':0,'movement_commands_sent':0}
v['uenv_sha256']=hashlib.sha256(Path('/boot/uEnv.txt').read_bytes()).hexdigest()
v['usb_devices']=[]
for p in Path('/sys/bus/usb/devices').glob('*'):
 if (p/'idVendor').exists():v['usb_devices'].append({'bus_path':p.name,**{k:(p/k).read_text().strip() for k in ['idVendor','idProduct','product'] if (p/k).exists()}})
p=Path('/sys/bus/i2c/devices/1-002d')
v['hub_control']={'exists':p.exists(),'name':(p/'name').read_text().strip() if (p/'name').exists() else None,'driver':str((p/'driver').resolve()) if (p/'driver').exists() else None}
v['video_devices']=[p.name for p in Path('/dev').glob('video*')]
raw=Path('/sys/class/drm/card0-DP-1/edid').read_bytes();v['edid_bytes']=len(raw);v['edid_sha256']=hashlib.sha256(raw).hexdigest()
v['units']=run(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts','-p','ExecStart'])
v['display']=run(['env','DISPLAY=:0','xrandr','--current'])
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for name,url,keys in [('gui','http://127.0.0.1:8783/api/state',['phase','ui_page','error','avatar_display']),('camera','http://127.0.0.1:8790/health',['capture_frames','capture_hz','detection_hz','camera_error','detector_error'])]:
 try:
  with op.open(url,timeout=2) as r:s=json.load(r)
  v[name]={k:s.get(k) for k in keys}
 except Exception as e:v[name]={'unavailable':str(e)}
print(json.dumps(v),flush=True)
