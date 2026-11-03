import hashlib,sys
from pathlib import Path
p=Path("/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/fixed-motion-bench-v1")
sys.path.insert(0,str(p))
assert hashlib.sha256((p/"package-manifest.json").read_bytes()).hexdigest()=="9a47a0319dc67644bf871497715da70171b39d329ec335b16b56079dc6850718"
import board_fixed_cli
sys.argv=["board_fixed_cli","--execute","--package-sha256","9a47a0319dc67644bf871497715da70171b39d329ec335b16b56079dc6850718","--reference-sha256",'f856569b2b193ad63df2789350c6f751a32cd113a0b17ab36eab2ba690e7b0c4']
board_fixed_cli.main()
