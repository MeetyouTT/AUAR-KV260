"""Add the exact import-name alias within the dedicated no-IO shadow directory."""
import hashlib,os
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-follow-shadow-live')
src=root/'follow.py';dst=root/'shadow_follow.py';expected='22fa85bed11e4a4ae5ff9db6d747fbeae474f6d871d91a169fd93404e84daf7b'
assert src.is_file() and not src.is_symlink() and hashlib.sha256(src.read_bytes()).hexdigest()==expected
assert not dst.exists() and not dst.is_symlink()
fd=os.open(str(dst),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'wb') as out:
 out.write(src.read_bytes());out.flush();os.fsync(out.fileno())
assert hashlib.sha256(dst.read_bytes()).hexdigest()==expected
print('SHADOW_IMPORT_ALIAS_SHA_OK')
