"""Read exact display bindings and DRM owners before considering reinitialization."""
import json,re,subprocess,urllib.request
from pathlib import Path
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'driver_writes':0}
v['devices']={}
for name in ['fd4a0000.display','xlnx-drm.0','fd4c0000.dma-controller']:
 p=Path('/sys/bus/platform/devices')/name
 d=p/'driver'
 v['devices'][name]={'exists':p.exists(),'driver':str(d.resolve()) if d.exists() else None,'driver_controls':{k:(d/k).exists() for k in ['bind','unbind']},'children':[q.name for q in p.glob('*') if q.is_dir()][:35]}
v['drm_devices']={}
for p in Path('/sys/class/drm').glob('card[0-9]'):
 v['drm_devices'][p.name]={'device':str((p/'device').resolve()),'driver':str((p/'device/driver').resolve())}
v['owners']=[]
for proc in Path('/proc').glob('[0-9]*'):
 try:
  names={str(p.resolve()) for p in (proc/'fd').glob('*') if str(p.resolve()).startswith(('/dev/dri/','/dev/mali','/dev/fb'))}
  if names:v['owners'].append({'pid':int(proc.name),'name':(proc/'comm').read_text().strip(),'devices':sorted(names)})
 except OSError:pass
v['units']=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','ActiveState','-p','MainPID','-p','NRestarts','-p','ExecStart'],text=True,timeout=5)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=2) as r:d=json.load(r)
v['gui']={k:d.get(k) for k in ['phase','playing','error','ui_page']}
v['edid_bytes']=len(Path('/sys/class/drm/card0-DP-1/edid').read_bytes())
v['touch_present']=Path('/sys/bus/usb/devices/1-1.1').exists()
print(json.dumps(v),flush=True)
