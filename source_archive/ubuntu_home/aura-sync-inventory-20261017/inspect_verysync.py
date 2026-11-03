"""Read only selected sync-folder metadata; never print configuration secrets."""
import json
import re
import subprocess

binary='/home/ghmd/.local/opt/verysync/verysync'
p=subprocess.run([binary,'folder','list'],stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE,text=True,timeout=8)
if p.returncode:raise RuntimeError('Folder configuration read failed; exit='+str(p.returncode))
paths=sorted(set(re.findall(r'/home/ghmd/Win共享文件[^\s"|,]*',p.stdout)))
print(json.dumps({'matching_sync_paths':paths},ensure_ascii=False,indent=2))
