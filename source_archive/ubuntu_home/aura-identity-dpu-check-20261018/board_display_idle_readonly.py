"""Separate DPMS blanking from hotplug status; no wake command."""
import json,os,subprocess
from pathlib import Path
env=dict(os.environ,DISPLAY=':0')
p=subprocess.run(['xset','q'],env=env,capture_output=True,text=True,timeout=4)
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'uptime':Path('/proc/uptime').read_text().split()[0],
 'display_commands_sent':0,'movement_commands_sent':0,'files_modified':0,
 'xset_query':{'rc':p.returncode,'text':p.stdout+p.stderr}}
root=Path('/sys/class/drm/card0-DP-1')
v['connector']={key:(root/key).read_text().strip() for key in ['status','enabled','dpms']}
print(json.dumps(v),flush=True)
