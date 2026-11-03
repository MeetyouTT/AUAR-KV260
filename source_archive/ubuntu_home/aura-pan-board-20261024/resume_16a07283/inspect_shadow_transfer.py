import hashlib,json
from pathlib import Path
S=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/shadow-v10r2')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='16a07283-9e14-45e6-816d-3bda4cf333a7'
print(json.dumps({'files':{str(p.relative_to(S)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in S.rglob('*') if p.is_file()}}))
