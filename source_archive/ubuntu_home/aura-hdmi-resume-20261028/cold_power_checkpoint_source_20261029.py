import hashlib,json
from pathlib import Path
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');meta=json.loads((ops/'meta.json').read_text())
root=Path(meta['candidate_root'])/'aura/board/vision';d={}
for p in root.glob('*.py'):
    lines=p.read_text().splitlines();selected=set()
    for i,line in enumerate(lines):
        if 'source_unit_sha256' in line or 'source_unit_sha' in line:selected.update(range(max(0,i-5),min(len(lines),i+7)))
    if selected:d[str(p)]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'lines':'\n'.join(str(i+1)+': '+lines[i] for i in sorted(selected))}
print(json.dumps(d))
