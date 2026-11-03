"""Identify the noisy USB slot and active capture formats, read only."""
import json,subprocess
from pathlib import Path
devices=[]
for p in Path('/sys/bus/usb/devices').iterdir():
 if ':' in p.name:continue
 value={'node':p.name}
 for n in ('busnum','devnum','idVendor','idProduct','manufacturer','product','speed','bConfigurationValue'):
  try:value[n]=(p/n).read_text().strip()
  except OSError:pass
 if 'devnum' in value:devices.append(value)
debug={}
root=Path('/sys/kernel/debug/usb/xhci')
if root.exists():
 for p in root.glob('*/devices/*'):
  for name in ('name','slot-context'):
   q=p/name
   if q.is_file():
    try:debug[str(q)]=q.read_text()[:2500]
    except OSError:pass
cards=Path('/proc/asound/cards').read_text() if Path('/proc/asound/cards').exists() else ''
pcms={}
for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'):
 try:pcms[str(p)]=p.read_text()[:800]
 except OSError:pass
commands={}
for argv in (['lsusb','-t'],['v4l2-ctl','-d','/dev/video0','--get-fmt-video','--get-parm']):
 try:r=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=3);commands[' '.join(argv)]=r.stdout[:5000]+r.stderr[:500]
 except FileNotFoundError:pass
print(json.dumps({'usb_devices':devices,'debug':debug,'cards':cards,'pcms':pcms,'commands':commands}))
