from pathlib import Path
import hashlib
p=Path('/home/root/aura-adaptation-20261006/visible-sweep-code-76e468d155715f8d/visible_servo_sweep.py')
s=p.read_bytes()
assert hashlib.sha256(s).hexdigest()=='76e468d155715f8d63cc570546149bd80b4215db8426cfc85762f0c4f5b5048e'
exec(compile(s,str(p),'exec'))
