"""Read the interrupted control transaction and verify independent restoration."""
import json,re,subprocess
from pathlib import Path
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
root=Path('/run/aura-screen-port-cycle-20261021')/boot
v={'boot_id':boot,'additional_power_writes':0}
p=root/'control-result.json'
v['control_result']=json.loads(p.read_text()) if p.exists() else None
v['watchdog']=subprocess.run(['systemctl','show','aura-screen-power-restore-'+boot[:8]+'.timer','-p','ActiveState','-p','SubState'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5).stdout
v['units']=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True,timeout=5)
v['usb_devices']=[{'path':p.name,'vid':(p/'idVendor').read_text().strip(),'pid':(p/'idProduct').read_text().strip(),'devnum':(p/'devnum').read_text().strip()} for p in Path('/sys/bus/usb/devices').glob('*') if (p/'idVendor').exists()]
v['edid_bytes']=len(Path('/sys/class/drm/card0-DP-1/edid').read_bytes())
kernel=subprocess.check_output(['dmesg'],text=True)
v['usb_events']=[s for s in kernel.splitlines() if re.search(r'usb.*(?:disconnect|reset|new.*device|over.current)',s,re.I)][-20:]
print(json.dumps(v),flush=True)
