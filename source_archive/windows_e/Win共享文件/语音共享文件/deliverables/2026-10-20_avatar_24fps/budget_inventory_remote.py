import json,subprocess,base64,urllib.request,re
from pathlib import Path
unit=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
cfg=Path(re.search(r'--config (\S+) ',subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True)).group(1))
print(json.dumps({'effective':unit,'config':json.loads(cfg.read_text()),'config_path':str(cfg),'launcher':base64.b64encode(cfg.with_name('launcher.py').read_bytes()).decode(),'state':json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))}))
