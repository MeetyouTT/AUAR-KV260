import json
from pathlib import Path
roots=[Path('/etc/init.d'),Path('/etc/systemd/system'),Path('/lib/systemd/system'),Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura/board/vision')]
hits=[]
for root in roots:
 for p in root.rglob('*'):
  if not p.is_file() or p.is_symlink() or p.stat().st_size>120000:continue
  try:text=p.read_text()
  except (UnicodeError,OSError):continue
  lines=[{'line':i,'text':s[:400]} for i,s in enumerate(text.splitlines(),1) if 'loadapp' in s or 'kv260-benchmark-b4096' in s or 'vart.conf' in s]
  if lines:hits.append({'path':str(p),'lines':lines})
print(json.dumps({'read_only':True,'hits':hits}))
