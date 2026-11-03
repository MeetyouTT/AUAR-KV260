import hashlib,sys
from pathlib import Path
p=Path('/home/root/aura-adaptation-20261006/newboot-c2753755/newboot_preview_restore.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='789e07e2f3212daa6d8a1ce8754222bb57abf4578ee03dd9dff9f9a9f7b210fa'
exec(compile(p.read_bytes(),str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
