ROOT='/home/root/aura-native-coldboot-20261024/verification/ee3db5fa3068e4a1'
import json,subprocess
from pathlib import Path
root=Path(ROOT);p=root/'report.json'
result={'report_exists':p.exists(),'root':ROOT}
if p.exists():result['report']=json.loads(p.read_text())
print(json.dumps(result))
