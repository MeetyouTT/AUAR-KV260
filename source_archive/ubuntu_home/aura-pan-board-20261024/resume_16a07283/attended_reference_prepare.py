import hashlib,runpy
from pathlib import Path
pins={'/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/attended-reference-1420/manual_release.py': '8e8c8ca3d9f86b702c34ff74ce5685a27a3cd6379d22a231739c9f78ccff44e5', '/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/attended-reference-1420/prepare_reference.py': 'a675127adfe212eb30e4c2c6a852108a60a0b5cae9a391cef48af287ee8ee86b', '/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/attended-reference-1420/execute_reference.py': '5e84805565e38dd725f7d552a7768c86b21a9df573c99cdb16308519c3505a95'}
assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in pins.items())
runpy.run_path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/attended-reference-1420/prepare_reference.py',run_name='__main__')
