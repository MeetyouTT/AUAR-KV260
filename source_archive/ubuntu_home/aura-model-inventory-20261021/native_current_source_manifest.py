import hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
root=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-vision-recovery-c76110abefc304bb/aura')
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
       for p in sorted(root.rglob('*.py')) if p.is_file() and not p.is_symlink()}
print(json.dumps({'scope':'read-only complete Python source manifest; no model/config/database contents',
 'root':str(root),'files':files,'count':len(files)}))
