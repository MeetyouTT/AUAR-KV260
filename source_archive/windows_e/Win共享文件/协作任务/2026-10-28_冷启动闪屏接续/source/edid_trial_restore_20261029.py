import hashlib,runpy,sys
from pathlib import Path
p=Path('/home/root/aura-post-power-20261022/helpers/bd572c83085cf336/source.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='bd572c83085cf336d73c5859d37201c20f7058a92155cf0d734a2dbbdcc965ab'
sys.argv=[str(p),'--restore','/run/aura-hdmi-edid-trials/da17ffa826824b7da2c069721b4a5c84']
runpy.run_path(str(p),run_name='__main__')
