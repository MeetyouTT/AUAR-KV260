import json,time
from pathlib import Path
out={'read_only':True,'mono':time.monotonic(),'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'usb':[]}
for p in Path('/sys/bus/usb/devices').glob('*'):
 if (p/'idVendor').is_file() and (p/'idProduct').is_file():
  vid=(p/'idVendor').read_text().strip();pid=(p/'idProduct').read_text().strip()
  if vid=='17ef' or (p/'product').is_file() and any(x in (p/'product').read_text().lower() for x in ('camera','audio','mcp')):
   out['usb'].append({'path':str(p),'vendor':vid,'product_id':pid,'devnum':(p/'devnum').read_text().strip(),'product':(p/'product').read_text().strip() if (p/'product').is_file() else None})
print(json.dumps(out))
