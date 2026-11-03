import base64,gzip,hashlib,json,subprocess
from pathlib import Path
p=Path('/home/root/aura-sface-recovery-20261023/promotion/4bcbe0999c62a348/report.json')
unit='aura-sface-recovery-promotion-4bcbe0999c62a348'
r={'state':subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','-p','ExecMainStatus'],text=True).strip()}
if p.exists():
 b=p.read_bytes();r['sha256']=hashlib.sha256(b).hexdigest();r['gzip_b64']=base64.b64encode(gzip.compress(b,mtime=0)).decode()
else:r['own_journal']=subprocess.check_output(['journalctl','-u',unit,'-n','22','--no-pager','-o','cat'],text=True)
print(json.dumps(r))
