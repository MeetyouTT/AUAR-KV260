"""Observe a user-operated HDMI comparison without controlling the display."""
import hashlib,json,socket,time
from pathlib import Path
root=Path('/sys/class/drm/card0-DP-1')
def state():
 b=(root/'edid').read_bytes()
 d={'edid_bytes':len(b),'edid_sha256':hashlib.sha256(b).hexdigest() if b else None}
 for k in ['status','enabled','dpms']:d[k]=(root/k).read_text().strip()
 text=Path('/sys/kernel/debug/dri/0/state').read_text()
 d['scanout']=[x.strip() for x in text.splitlines() if x.strip().startswith(('active=','enable=','mode:'))]
 return d
start=time.monotonic();before=state();changes=[];events=[];previous=before
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
s=socket.socket(socket.AF_NETLINK,socket.SOCK_DGRAM,15);s.bind((0,1));s.settimeout(.2)
while time.monotonic()-start<60:
 try:
  raw=s.recv(16384).decode(errors='replace').split('\0');d=dict(x.split('=',1) for x in raw if '=' in x)
  if d.get('SUBSYSTEM') in ['drm','usb']:
   events.append({'at':round(time.monotonic()-start,3),**{k:d.get(k) for k in ['SUBSYSTEM','ACTION','HOTPLUG','DEVPATH']}})
 except socket.timeout:pass
 current=state()
 if current!=previous:changes.append({'at':round(time.monotonic()-start,3),'state':current});previous=current
s.close()
print(json.dumps({'boot_id':boot,'before':before,'after':state(),'changes':changes,'events':events,'elapsed_seconds':round(time.monotonic()-start,3),'files_modified':0,'display_commands_sent':0,'movement_commands_sent':0}),flush=True)
