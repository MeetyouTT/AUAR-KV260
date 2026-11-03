import base64,hashlib,json,re,subprocess,urllib.request
from pathlib import Path
raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True)
config=Path(re.search(r'--config (/[^ ;]+)',raw).group(1));a=Path(json.loads(config.read_text())['runtime'])/'aura'
p=a/'tools/board_avatar_pan.py';data=p.read_bytes();o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
print(json.dumps({'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'module_base64':base64.b64encode(data).decode(),
 'main_manual_fields':sorted(u['manual_pan']),'face_follow_state':u['manual_pan'].get('face_follow'),
 'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))
