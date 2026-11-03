import base64,gzip,hashlib,json,subprocess
from pathlib import Path
p=Path('/home/root/aura-admission-floor-20261023/promotion/e4e58625c0520683/report.json')
unit='aura-sface-recovery-promotion-e4e58625c0520683'
r={'state':subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','-p','ExecMainStatus'],text=True).strip()}
if p.exists():
 raw=p.read_bytes();r['sha256']=hashlib.sha256(raw).hexdigest();r['gzip_b64']=base64.b64encode(gzip.compress(raw,mtime=0)).decode()
else:r['own_journal']=subprocess.check_output(['journalctl','-u',unit,'-n','22','--no-pager','-o','cat'],text=True)
print(json.dumps(r))
