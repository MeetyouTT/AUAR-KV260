"""Disable only the exact delay configuration installed with this backup."""
import hashlib,json,os
from pathlib import Path
def disable(root):
    backup=root/'aura-hdmi-delay5-20261021'
    meta=json.loads((backup/'before.json').read_text())
    target=root/'uEnv.txt'
    if target.is_symlink():raise RuntimeError('Refusing a symbolic link')
    if not target.exists():return 'already_absent'
    if hashlib.sha256(target.read_bytes()).hexdigest()!=meta['installed_uenv_sha256']:
        raise RuntimeError('uEnv.txt changed since install; refusing to remove it')
    saved=backup/'uEnv.disabled'
    if saved.exists():raise RuntimeError('Rollback destination already exists')
    target.rename(saved)
    os.sync()
    return 'disabled_for_next_boot'
if __name__=='__main__':
    root=Path(__file__).resolve().parent.parent
    print(json.dumps({'result':disable(root),'current_runtime_parameter_unchanged':True}))
