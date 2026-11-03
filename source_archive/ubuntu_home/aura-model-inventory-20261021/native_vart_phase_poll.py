import base64,gzip,hashlib,json,subprocess
from pathlib import Path
p=Path('/home/root/aura-native-wait-20261023/vart-phase/0b69843e8b7c38fa/report.json')
r={'unit_state':subprocess.check_output(['systemctl','show','aura-vart-phase-0b69843e8b7c38fa','-p','ActiveState','--value'],text=True).strip()}
if p.exists():
 raw=p.read_bytes();r.update(report_sha256=hashlib.sha256(raw).hexdigest(),report_gzip_b64=base64.b64encode(gzip.compress(raw,mtime=0)).decode())
else:r['report_missing']=True
print(json.dumps(r))
