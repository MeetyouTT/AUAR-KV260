"""Read the cold-boot pan fault and loaded firmware; no MMIO or STOP writes."""
import hashlib,json,subprocess,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
m=u.get('manual_pan',{})
p=Path('/proc/device-tree/fpga-full/firmware-name')
apps=subprocess.run(['xmutil','listapps'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15)
active=[]
for line in apps.stdout.splitlines():
 f=line.split()
 if len(f)==6 and f[1] in ('XRT_FLAT','PL_FLAT') and f[-1].rstrip(',')=='0':active.append(f[0])
state=Path('/sys/class/fpga_manager/fpga0/state')
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'firmware_name':p.read_bytes().rstrip(b'\0').decode() if p.exists() else None,
 'active_apps':active,'listapps_exit':apps.returncode,
 'fpga_state':state.read_text().strip() if state.exists() else None,
 'manual_state':m.get('state'),'manual_error':m.get('error'),'manual_message':m.get('message'),
 'automatic_following':m.get('automatic_following'),'register_access_by_probe':False},ensure_ascii=False,sort_keys=True))
