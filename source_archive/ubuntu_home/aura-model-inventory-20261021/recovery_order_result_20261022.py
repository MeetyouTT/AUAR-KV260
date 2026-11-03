import json
from pathlib import Path
root=Path('/home/root/aura-audio-recovery-20261021/a0572918fbcedf0c')
p=root/'result.json'
print(json.dumps({'exists':p.exists(),'result':json.loads(p.read_text()) if p.exists() else None}))
