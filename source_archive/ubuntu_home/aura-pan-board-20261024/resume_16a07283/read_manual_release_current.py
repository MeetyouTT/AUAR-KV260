import hashlib,json
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');A=R/'gui-manual-bound-v1/runtime/aura'
c=json.loads((A/'config/pan_manual.local.json').read_text());p=Path(c['release_manifest'])
assert hashlib.sha256(p.read_bytes()).hexdigest()==c['release_manifest_sha256']
source=A/'board/motion/manual_release.py'
print(json.dumps({'release':json.loads(p.read_text()),'root':str(p.parent),
 'source':source.read_text(),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'motor_commands_sent':0}))
