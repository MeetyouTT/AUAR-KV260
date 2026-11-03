"""Restore only our added follow-config field through the copied config alias."""
import hashlib,json,os
from pathlib import Path
G=Path('/home/root/aura-pan-current-20261024/463c9307/gui-release');cfg=json.loads((G/'startup/config.json').read_text())
p=Path(cfg['runtime'])/'aura/config/pan_manual.local.json';old=p.read_bytes();d=json.loads(old)
assert hashlib.sha256(old).hexdigest()=='af3ec15c176bda002a796b0cc092afcf99b78fb8d5347bff753351cf74deeb74'
assert d.pop('face_follow_config')=='/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v4/runtime/aura/config/pan_face.local.json'
raw=(json.dumps(d,indent=2)+'\n').encode();expected=cfg['component_sha256']['config/pan_manual.local.json'];assert hashlib.sha256(raw).hexdigest()==expected
resolved=p.resolve();tmp=resolved.with_name(resolved.name+'.restore-face-pin');assert not tmp.exists()
with tmp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
assert p.read_bytes()==old;os.replace(tmp,resolved)
root=Path(cfg['runtime'])/'aura';assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==v for n,v in cfg['component_sha256'].items())
print(json.dumps({'original_254_pins_restored':True,'alias_file':p.is_symlink(),'alias_parent':p.parent.is_symlink(),'register_writes':0}))
