import json
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/readonly-monitor-20261026')
out=[]
for p in sorted(P.glob('gui-v2-*/status.json')):
 s=json.loads(p.read_text());out.append(dict(output=str(p.parent),status=s))
print(json.dumps({'monitors':out,'motor_commands_sent':0}))
