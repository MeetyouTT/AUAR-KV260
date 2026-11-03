"""Read current UI/motion baseline; no MMIO, service changes or actuation."""
import base64,gzip,hashlib,json,subprocess,urllib.request
from pathlib import Path
units={}
for unit in ['aura-camera-ui.service','aura-avatar-ui.service']:
 units[unit]={k:subprocess.check_output(['systemctl','show',unit,'-p',k,'--value'],text=True).strip() for k in ['ActiveState','MainPID','WorkingDirectory','FragmentPath','ExecStart']}
root=Path(units['aura-avatar-ui.service']['WorkingDirectory'])
driver=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
artifacts={}
paths={'current-board-avatar-gtk.py':root/'tools/board_avatar_gtk.py','current-board-avatar-config.json':root/'config/board_avatar_gtk.json','current-touch-layout.json':root/'ui/board_touch_layout.json','vsrv-common.py':driver/'common.py','vsrv-driver.py':driver/'vsrv_driver.py'}
for name,p in paths.items():
 if p.is_file():
  raw=gzip.compress(p.read_bytes(),mtime=0);artifacts[name+'.gz']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
health={}
for port,path in [(8790,'/health'),(8783,'/api/state')]:
 try:
  with opener.open('http://127.0.0.1:%s%s'%(port,path),timeout=2) as response:value=json.load(response)
  health[str(port)]={k:value.get(k) for k in (['pid','detection_hz','identity_recognition','camera_error','detector_error'] if port==8790 else ['phase','playing','ui_page','ui_layer'])}
 except Exception as exc:health[str(port)]={'error':type(exc).__name__}
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'units':units,'health':health,'artifacts':artifacts}),flush=True)
