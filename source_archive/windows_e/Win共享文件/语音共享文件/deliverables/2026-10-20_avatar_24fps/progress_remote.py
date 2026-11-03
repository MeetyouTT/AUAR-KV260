import json,subprocess
from pathlib import Path
p=Path('/home/root/aura-render24-20261020/candidate-45f9f5cd2aaa')
print(json.dumps({'logs':{n:(p/n).read_text()[-2500:] for n in ('pixels.log','tests.log','verification.json') if (p/n).exists()},'processes':subprocess.getoutput('ps -eo pid,pcpu,etime,args --sort=-pcpu | head -7')}))
