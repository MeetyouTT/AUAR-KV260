import hashlib,runpy,sys
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/attended-reference-1420/execute_reference_r2.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='c91355fdcac733b8a91f8a055437f3341881b4bfea6b1053bd7a469195d45bab'
sys.argv=[str(p)]
runpy.run_path(str(p),run_name='__main__')
