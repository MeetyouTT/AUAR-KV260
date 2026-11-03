import json,subprocess
from pathlib import Path
out={'usb':[],'xhci_debug':{},'camera_processes':[]}
for p in Path('/sys/bus/usb/devices').glob('*'):
 if ':' in p.name:
  if (p/'driver').exists():out.setdefault('usb_interfaces',{})[p.name]=(p/'driver').resolve().name
  continue
 if not (p/'devnum').exists():continue
 record={'path':p.name}
 for n in ['busnum','devnum','speed','idVendor','idProduct','manufacturer','product','bDeviceClass']:
  if (p/n).exists():record[n]=(p/n).read_text().strip()
 out['usb'].append(record)
for p in Path('/sys/kernel/debug/usb/xhci').glob('*'):
 out['xhci_debug'][str(p)]=[str(x.relative_to(p)) for x in p.glob('devices/*')]
 for q in p.glob('devices/*/slot-context'):
  try:out.setdefault('slot_contexts',{})[str(q)]=q.read_text()[:1200]
  except OSError:pass
out['camera_unit']=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','-p','ActiveState','-p','NRestarts'],timeout=5).decode()
out['meminfo']=[s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith(('MemAvailable:','CmaTotal:','CmaFree:'))]
print(json.dumps(out))
