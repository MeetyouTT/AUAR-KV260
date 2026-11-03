ROOT='/home/root/aura-native-acceptance-20261024/e6b226031b0ce5e1'
import json,subprocess
from pathlib import Path
root=Path(ROOT);p=root/'report.json'
result={'report_exists':p.exists(),'root':ROOT}
if p.exists():result['report']=json.loads(p.read_text())
result['service']=subprocess.check_output(['systemctl','show','aura-self-acceptance-'+root.name+'.service','-p','ActiveState','-p','MainPID','-p','Result'],text=True)
print(json.dumps(result))
