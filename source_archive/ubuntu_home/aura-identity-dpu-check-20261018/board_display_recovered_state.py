"""Read only a possible hotplug recovery state; no modeset or reset."""
import base64,hashlib,json,os,re,subprocess
from pathlib import Path
env=dict(os.environ,DISPLAY=':0')
def run(args):
    try:
        p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=5)
        return {'rc':p.returncode,'text':(p.stdout+p.stderr)[-14000:]}
    except Exception as exc:return {'error':type(exc).__name__}
raw=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
   'uptime':Path('/proc/uptime').read_text().split()[0],
   'display_commands_sent':0,'movement_commands_sent':0,'files_modified':0,
   'edid_bytes':len(raw),'edid_sha256':hashlib.sha256(raw).hexdigest(),
   'edid_base64':base64.b64encode(raw).decode()}
v['xrandr']=run(['xrandr','--verbose'])
v['drm_state']=run(['cat','/sys/kernel/debug/dri/0/state'])
p=Path('/var/log/Xorg.0.log')
if p.exists():v['xorg_recent_display']=[line for line in p.read_text(errors='replace').splitlines()
    if re.search(r'edid|modeline|mode |hpd|connected|disconnected',line,re.I)][-65:]
print(json.dumps(v),flush=True)
