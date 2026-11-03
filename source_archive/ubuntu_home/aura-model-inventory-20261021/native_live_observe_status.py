import json,subprocess
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
print(json.dumps({'state':json.loads((root/'state.json').read_text()),
 'unit':subprocess.check_output(['systemctl','show','aura-native-observe60-be72669aa53de735.service','-p','ActiveState','-p','Result','-p','MainPID','-p','ExecMainStatus'],text=True),
 'log':subprocess.check_output(['journalctl','-b','-u','aura-native-observe60-be72669aa53de735.service','-n','25','--no-pager','-o','cat'],text=True)[-4000:]}))
