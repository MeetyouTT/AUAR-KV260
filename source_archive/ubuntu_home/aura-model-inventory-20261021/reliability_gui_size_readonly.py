import json
from pathlib import Path
root=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/runtime/aura')
files=list(root.rglob('*'))
rows=[p for p in files if p.is_file() and '__pycache__' not in p.parts]
print(json.dumps({'read_only':True,'files':len(rows),'bytes':sum(p.stat().st_size for p in rows),
 'links':[{'relative':str(p.relative_to(root)),'directory':p.is_dir()} for p in files if p.is_symlink()],
 'large_files':[{'relative':str(p.relative_to(root)),'bytes':p.stat().st_size} for p in rows if p.stat().st_size>10000000]}))
