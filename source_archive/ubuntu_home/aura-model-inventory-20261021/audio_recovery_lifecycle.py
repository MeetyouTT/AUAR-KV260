import base64,gzip,hashlib,json,subprocess
from pathlib import Path
out={'units':{},'sources':{}}
for n in ['aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service']:
 out['units'][n]=subprocess.check_output(['systemctl','cat',n],timeout=4).decode()
p=Path('/proc')/subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
args=(p/'cmdline').read_bytes().decode().split('\0');out['supervisor_args']=args
for a in args:
 q=Path(a)
 if a.endswith('.py') and q.is_file():out['sources'][a]={'sha256':hashlib.sha256(q.read_bytes()).hexdigest(),'gzbase64':base64.b64encode(gzip.compress(q.read_bytes())).decode()}
print(json.dumps(out))
