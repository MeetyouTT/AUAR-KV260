"""Preserve the incomplete, pre-write backup after verifying both live originals."""
import hashlib,json,os
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='bec99c5a-5292-4a3e-b180-c52187d6c47b'
p=Path('/boot/aura-native-firstmode-20261021')
assert not p.is_symlink()
assert {f.name for f in p.iterdir()}=={'xorg.before','xorg.installed','uenv.before','uenv.installed','manifest.json'}
m=json.loads((p/'manifest.json').read_text())
for item in m['targets']:
    original=(p/item['before_file']).read_bytes()
    target=Path(item['path'])
    assert not target.is_symlink()
    assert hashlib.sha256(original).hexdigest()==item['before_sha256']
    assert target.read_bytes()==original,'Active configuration was changed; stop'
q=p.with_name(p.name+'-incomplete-a715d0d551032aee')
assert not q.exists()
p.rename(q)
os.sync()
print(json.dumps({'active_configurations_unchanged':True,'incomplete_backup_preserved':str(q),'services_restarted':0}))
