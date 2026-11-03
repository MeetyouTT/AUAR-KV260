"""Inspect the current camera source closure without importing it or reading gallery records."""
import hashlib
import json
from pathlib import Path
import stat

boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot == 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
ops = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
meta = json.loads((ops/'meta.json').read_text())
aura = Path(meta['candidate_root'])/'aura'
run = ops/('native-run-'+boot+'-229296')
paths = [ops/'pan-face-edge-v5/face-source-v17/deployment-manifest.json',
    ops/'pan-face-edge-v5/native-operator-v1/native_entry_operator.py',
    aura/'board/vision/native_startup.py', aura/'board/vision/source_protection.py',
    aura/'board/vision/native_binding.py', run/'config.json', Path(meta['candidate_config'])]
files=[]
for path in paths:
    try:
        st=path.lstat();assert stat.S_ISREG(st.st_mode) and st.st_size<=160000
        raw=path.read_bytes()
        files.append(dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),content=raw.decode('utf-8')))
    except FileNotFoundError:
        files.append(dict(path=str(path),unavailable=True))
print(json.dumps(dict(boot=boot,aura=str(aura),files=files,source_imported=False,gallery_read=False)))
