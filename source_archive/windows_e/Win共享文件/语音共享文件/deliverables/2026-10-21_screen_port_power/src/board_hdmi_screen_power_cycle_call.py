"""Invoke the exact independently probed USB power helper once."""
import hashlib,runpy,sys
from pathlib import Path
p=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/helpers/de0d44f234155d81/source.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='de0d44f234155d81cf18e8ec65916b9221b7b401d4eb74bbae3124d9c39341db'
sys.argv=[str(p),'cycle']
runpy.run_path(str(p),run_name='__main__')
