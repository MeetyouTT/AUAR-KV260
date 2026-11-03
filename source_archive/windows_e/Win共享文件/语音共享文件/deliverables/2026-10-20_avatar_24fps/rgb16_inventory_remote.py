import json,subprocess,base64,urllib.request
from pathlib import Path
unit=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
cfg=Path('/home/root/aura-pan-manual-ui-20261020/camera-fix-v3/startup/config.json')
print(json.dumps({'effective':unit,'config':json.loads(cfg.read_text()),'config_path':str(cfg),'launcher':base64.b64encode(cfg.with_name('launcher.py').read_bytes()).decode(),'state':json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))}))
