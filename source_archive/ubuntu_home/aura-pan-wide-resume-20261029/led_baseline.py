import json
from pathlib import Path
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'leds':{p.name:{n:(p/n).read_text().strip() for n in ['brightness','trigger'] if (p/n).exists()} for p in Path('/sys/class/leds').glob('*')}}))
