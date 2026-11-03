"""Observe DRM hotplug and Xorg changes without forcing a connector reprobe."""
import json,socket,subprocess,time
from pathlib import Path
log=Path('/var/log/Xorg.0.log');offset=log.stat().st_size
def connector():
 p=Path('/sys/class/drm/card0-DP-1');raw=(p/'edid').read_bytes()
 import hashlib
 return {'edid_bytes':len(raw),'edid_sha256':hashlib.sha256(raw).hexdigest() if raw else None,**{k:(p/k).read_text().strip() for k in ['status','enabled','dpms']}}
def interrupts():return [s for s in Path('/proc/interrupts').read_text().splitlines() if any(k in s.lower() for k in ['dpdma','zynqmp','display','fd4a','fd4c'])]
def processes():
 result=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   name=(p/'comm').read_text().strip()
   if name in ['xrandr','xset']:result.append({'pid':p.name,'argv':(p/'cmdline').read_bytes().decode().replace('\0',' ')})
  except OSError:pass
 return result
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'before':connector(),'interrupts_before':interrupts(),'events':[],'display_processes':[]}
s=socket.socket(socket.AF_NETLINK,socket.SOCK_DGRAM,15);s.bind((0,1));s.settimeout(.2)
started=time.monotonic()
while time.monotonic()-started<6:
 try:
  raw=s.recv(16384).decode(errors='replace').split('\0');fields=dict(x.split('=',1) for x in raw if '=' in x)
  if fields.get('SUBSYSTEM')=='drm' or fields.get('HOTPLUG')=='1':v['events'].append({'at':round(time.monotonic()-started,3),'fields':fields})
 except socket.timeout:pass
 v['display_processes'].extend(processes())
s.close();v['after']=connector();v['interrupts_after']=interrupts()
with log.open() as stream:stream.seek(offset);v['new_xorg_log']=stream.read()[-10000:]
v['elapsed_seconds']=round(time.monotonic()-started,3);v.update(display_commands_sent=0,files_modified=0,movement_commands_sent=0)
print(json.dumps(v),flush=True)
