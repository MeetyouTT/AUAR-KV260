import json,subprocess
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
log=subprocess.check_output(['journalctl','-b','-u','aura-camera-ui.service','-n','40','--no-pager','-o','cat'],text=True)
status=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','ActiveState','-p','MainPID','-p','ExecMainStatus','-p','Result'],text=True)
print(json.dumps({'state':json.loads((root/'state.json').read_text()),'camera_unit':status,'camera_log':log[-6500:]}))
