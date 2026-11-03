import hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
root=Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce/runtime')
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
       for p in sorted(root.rglob('*.py')) if p.is_file() and not p.is_symlink()}
print(json.dumps({'scope':'read-only exact GUI Python source hashes, no config/audio/identity data',
 'root':str(root),'count':len(files),'files':files}))
