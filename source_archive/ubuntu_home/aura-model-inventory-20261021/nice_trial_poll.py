import gzip,base64,hashlib,json,subprocess
from pathlib import Path
p=Path('/home/root/aura-vision-persistent-20261023/phase/28df49bc28aaf09f/report.json')
r={'unit_state':subprocess.check_output(['systemctl','show','aura-optional-phase-28df49bc28aaf09f','-p','ActiveState','--value'],text=True).strip()}
if p.exists():
 raw=p.read_bytes();d=json.loads(raw)
 if d['complete']:r.update(sha256=hashlib.sha256(raw).hexdigest(),gzip_b64=base64.b64encode(gzip.compress(raw,mtime=0)).decode())
 else:r['complete']=False
print(json.dumps(r))
