"""Read cached display/USB state without display, AUX, USB or splitter commands."""
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
def read(p):
    try:
        return Path(p).read_text().strip()
    except OSError:
        return None

v = {'collected_utc':datetime.now(timezone.utc).isoformat(),
     'boot_id':read('/proc/sys/kernel/random/boot_id'),
     'uptime':read('/proc/uptime'), 'display_control_commands':0,
     'aux_transactions':0, 'usb_control_requests':0,
     'splitter_commands':0, 'movement_commands':0}
v['connectors'] = {}
for p in Path('/sys/class/drm').glob('card*-DP-*'):
    e = (p/'edid').read_bytes()
    v['connectors'][p.name] = {k:read(p/k) for k in ['status','enabled','dpms','modes']}
    v['connectors'][p.name].update(edid_bytes=len(e), edid_sha256=hashlib.sha256(e).hexdigest())
v['drm_state'] = read('/sys/kernel/debug/dri/0/state')
c = read('/sys/kernel/debug/clk/clk_summary') or ''
v['clocks'] = [s.strip() for s in c.splitlines() if s.split() and s.split()[0] in ['dp_video_ref','dpdma_ref','dp_aclk']]
p = subprocess.run(['env','DISPLAY=:0','xset','q'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
v['dpms_query'] = {'rc':p.returncode,'text':'\n'.join(s.strip() for s in p.stdout.splitlines() if re.search(r'Monitor is|DPMS is|Standby:',s))}
p = subprocess.run(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','ActiveState','-p','MainPID','-p','NRestarts'],stdout=subprocess.PIPE,text=True,timeout=5)
v['units'] = p.stdout.strip()
v['usb'] = {p.name:{k:read(p/k) for k in ['idVendor','idProduct','product','busnum','devnum']} for p in Path('/sys/bus/usb/devices').glob('*') if (p/'idVendor').exists()}
v['protected_hashes'] = {n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in ['/boot/uEnv.txt','/etc/X11/xorg.conf']}
v['fbdev_emulation'] = read('/sys/module/drm_kms_helper/parameters/fbdev_emulation')
v['xorg_initial_modes'] = [s.strip() for s in (read('/var/log/Xorg.0.log') or '').splitlines() if 'initial mode' in s.lower()]
print(json.dumps(v),flush=True)
