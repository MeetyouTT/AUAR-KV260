import json,subprocess
from pathlib import Path
root=Path('/home/root/aura-native-coldboot-20261024/c6b338dc8423086d');p=root/'shutdown.json'
r={'report_exists':p.exists()}
if p.exists():r['report']=json.loads(p.read_text())
r['controller']=subprocess.check_output(['systemctl','show','aura-native-cold-shutdown-c6b338dc8423086d.service','-p','ActiveState','-p','MainPID','-p','Result'],text=True)
print(json.dumps(r))
