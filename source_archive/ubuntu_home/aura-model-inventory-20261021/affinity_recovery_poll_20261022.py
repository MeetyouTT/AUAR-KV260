import json
from pathlib import Path
p=Path('/home/root/aura-audio-recovery-20261021/dda47b13d83c2110/result.json')
print(json.dumps({'exists':p.is_file(),'result':json.loads(p.read_text()) if p.is_file() else None}))
