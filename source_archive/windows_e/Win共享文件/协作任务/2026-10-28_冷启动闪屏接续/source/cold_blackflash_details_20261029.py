"""Bounded read-only cold-boot evidence; no reinitialization."""
import hashlib,json,subprocess,time
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='50b4fef1-9748-43c7-92bf-3040db8c994e'
def read(p):
    try:return Path(p).read_text().strip()
    except OSError as e:return {'error':type(e).__name__}
def usb():
    d={}
    for p in Path('/sys/bus/usb/devices').glob('*'):
        if (p/'idVendor').exists():d[p.name]={k:read(p/k) for k in ['idVendor','idProduct','product','devnum','busnum','authorized']}
    return d
def kernel():
    p=subprocess.run(['dmesg'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=4)
    return [v for v in p.stdout.splitlines() if any(k in v.lower() for k in ['usb disconnect','new full-speed','new high-speed','new super','descriptor','underflow','hpd','train','dpsub','dpdma','displayport','drm','hdmi'])][-65:]
marker=Path('/run/aura-display-startup.json')
d={'boot_id':read('/proc/sys/kernel/random/boot_id'),'startup_marker':json.loads(marker.read_text()) if marker.exists() else None,'power_on_delay_ms':read('/sys/module/zynqmp_dpsub/parameters/power_on_delay_ms'),'samples':[],'kernel_before':kernel()}
for i in range(7):
    d['samples'].append({'monotonic':time.monotonic(),'usb':usb(),'dpms':read('/sys/class/drm/card0-DP-1/dpms')})
    if i<6:time.sleep(1)
d['kernel_after']=kernel()
log=Path('/var/log/Xorg.0.log')
d['xorg_lines']=[v for v in log.read_text(errors='replace').splitlines() if any(k in v.lower() for k in ['1024','edid','modeline','warning','error','depth'])][-35:] if log.exists() else []
p=Path('/home/root/aura-device-skills-20261028/0cd7c3445a84475098b938d5b97175e0/startup/config.json');c=json.loads(p.read_text())
d['gui_config_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
d['display_config']={k:v for k,v in c.items() if any(t in k for t in ['display','retrain','edid','output'])}
print(json.dumps(d))
