"""Restore the previously bootable kernel selection, preserving both files."""
import hashlib,json,os
from pathlib import Path
root=Path(__file__).resolve().parent
meta=json.loads((root/'before.json').read_text())
target=root.parent/'uEnv.txt'
assert not target.is_symlink()
assert hashlib.sha256(target.read_bytes()).hexdigest()==meta['candidate_uenv_sha256'], 'uEnv changed; inspect it first'
original=(root/'uEnv.before').read_bytes()
assert hashlib.sha256(original).hexdigest()==meta['old_uenv_sha256']
saved=root/'uEnv.candidate.disabled'
assert not saved.exists()
with saved.open('xb') as f:f.write(target.read_bytes())
temporary=root.parent/'uEnv.aura-rollback.pending'
with temporary.open('xb') as f:
 f.write(original);f.flush();os.fsync(f.fileno())
temporary.replace(target);os.sync()
assert target.read_bytes()==original
print(json.dumps({'restored_previous_boot_selection':True,'effective_after_next_boot':True}))
