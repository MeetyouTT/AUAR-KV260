import os;from pathlib import Path;assert os.uname().machine=='aarch64';assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100';
import hashlib,gzip,json
p=Path('/home/root/aura-realtime-vision-20261007/bundle-fcc207d4b226988f4a9b80434195e806c0e06c754808b6633ac6f58d08d9c009.upload')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='fcc207d4b226988f4a9b80434195e806c0e06c754808b6633ac6f58d08d9c009'
sources=json.loads(gzip.decompress(p.read_bytes()))
hashes={'vision_core.py': '9629102ced2856bbd0c120b9c5e3df36c224424165bb980b90be42350ae8a700', 'x11_window.py': '69cb8da8b16f9e10e0dd31b7c575f69c4a740989d2eb9465737a3e9882b9a24a', 'realtime_vision.py': 'd6f074bb51b1fd057c731ea59072c1ad4983ad9a99c3dd99877230246d1a4f28', 'test_vision_core.py': '86f39de2b5484cb721cf26767381c50b5069e8253378b6bc1f81716730336834', 'board_launch.py': '66225075e8f3d9af5b6d1fdb357ce33e5a418cc85435dabac084a62a611f9bf5'}
assert set(sources)==set(hashes)
release=Path('/home/root/aura-realtime-vision-20261007/releases/fcc207d4b226988f')
release.mkdir(parents=True,exist_ok=False)
for name,source in sources.items():
 assert hashlib.sha256(source.encode()).hexdigest()==hashes[name]
 (release/name).write_text(source)
Path('/home/root/aura-realtime-vision-20261007/staged.json').write_text(json.dumps({"release":str(release),"hashes":hashes}))
print(json.dumps({"release":str(release),"hashes":hashes}))
