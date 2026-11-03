"""Report live GUI pin changes without modifying them or printing config data."""
import hashlib,json
from pathlib import Path
G=Path('/home/root/aura-pan-current-20261024/463c9307/gui-release');c=json.loads((G/'startup/config.json').read_text());root=Path(c['runtime'])/'aura';rows=[]
for n,expected in c['component_sha256'].items():
 p=root/n;raw=p.read_bytes();actual=hashlib.sha256(raw).hexdigest()
 if actual!=expected:rows.append({'relative':n,'expected':expected,'actual':actual,'bytes':len(raw),'text':raw.decode() if n.endswith('.py') else None})
print(json.dumps({'changed':rows,'gui_stage_v5_exists':(G.parent/'gui-face-edge-v5').exists()}))
