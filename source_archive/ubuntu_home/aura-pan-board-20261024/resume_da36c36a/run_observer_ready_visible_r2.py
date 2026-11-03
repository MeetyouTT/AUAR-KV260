import hashlib,sys
from pathlib import Path
p=Path("/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/fixed-motion-visible-v2")
sys.path.insert(0,str(p))
assert hashlib.sha256((p/"package-manifest.json").read_bytes()).hexdigest()=="6b9cddcfeb78cd49708a01b9f99e5b20f894448818849376556a6a596bc09b83"
import board_fixed_cli
sys.argv=["board_fixed_cli","--execute","--package-sha256","6b9cddcfeb78cd49708a01b9f99e5b20f894448818849376556a6a596bc09b83","--reference-sha256",'a31816e6f9b9bbe77f07a7e268d176003a4f729e4256574b4ed821c030bb9095']
board_fixed_cli.main()
