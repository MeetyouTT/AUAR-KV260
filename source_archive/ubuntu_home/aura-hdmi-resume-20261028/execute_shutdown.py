import hashlib,runpy,sys
from pathlib import Path
p=Path('/home/root/aura-post-power-20261022/helpers/71eed27c50dd12b9/source.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='71eed27c50dd12b921ce4fe5ff4b9facb8151d9dee6376df48da254beb7fc55c'
sys.argv=[str(p),'--shutdown'];runpy.run_path(str(p),run_name='__main__')
