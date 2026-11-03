"""Execute the prepared, verified GUI update and preserve its report."""
import json
from pathlib import Path
import subprocess

stage=Path('/home/root/aura-ui-layers-20261016/update-38df07b20542959b')
p=subprocess.run(['python3','-B',str(stage/'payload/board_deploy.py')],
                 stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=38)
if p.returncode:
    print(json.dumps({'exit_code':p.returncode,'output':p.stdout[-8000:]}))
    raise SystemExit(p.returncode)
print(p.stdout,end='')
