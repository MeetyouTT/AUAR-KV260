import hashlib,sys
from pathlib import Path
p=Path("/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/fixed-motion-bench-v2")
sys.path.insert(0,str(p))
assert hashlib.sha256((p/"package-manifest.json").read_bytes()).hexdigest()=="c36cc7a0c2f0d3bea609bd88e6d6cbc01b1d03e6446d5ac46b743e4490404f8b"
import board_fixed_cli
sys.argv=["board_fixed_cli","--execute","--package-sha256","c36cc7a0c2f0d3bea609bd88e6d6cbc01b1d03e6446d5ac46b743e4490404f8b","--reference-sha256",'7709502ab38aedcf5377089ee04a528fbc43b9dc0c2601a1d4c4ec1d68f84fb5']
board_fixed_cli.main()
