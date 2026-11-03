import hashlib,sys
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/fixed-motion-visible-v1')
sys.path.insert(0,str(p))
assert hashlib.sha256((p/"package-manifest.json").read_bytes()).hexdigest()=='fe434ca4841d4aef604cfc9dd3baa98c19bcb41469b2890cf00c075ecdc4189a'
import board_fixed_cli
sys.argv=["board_fixed_cli","--execute","--package-sha256",'fe434ca4841d4aef604cfc9dd3baa98c19bcb41469b2890cf00c075ecdc4189a',"--reference-sha256",'f4d5cb88a216fc5f5adf14c8baa843829f621fc12baa71a425874bb9a7bf9291']
board_fixed_cli.main()
