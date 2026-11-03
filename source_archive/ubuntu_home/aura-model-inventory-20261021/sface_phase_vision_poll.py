import base64,gzip,hashlib,json,subprocess
from pathlib import Path
p=Path('/home/root/aura-sface-recovery-20261023/phase/22f127ccbe6465f7/report.json')
r={'unit_state':subprocess.check_output(['systemctl','show','aura-optional-phase-22f127ccbe6465f7','-p','ActiveState','--value'],text=True).strip()}
if p.exists():
 d=json.loads(p.read_text())
 if d['complete']:
  raw=p.read_bytes();r['sha256']=hashlib.sha256(raw).hexdigest();r['gzip_b64']=base64.b64encode(gzip.compress(raw,mtime=0)).decode()
 else:r['complete']=False;r['pid']=d['pid']
else:r['own_journal']=subprocess.check_output(['journalctl','-u','aura-optional-phase-22f127ccbe6465f7','-n','20','--no-pager','-o','cat'],text=True)
print(json.dumps(r))
