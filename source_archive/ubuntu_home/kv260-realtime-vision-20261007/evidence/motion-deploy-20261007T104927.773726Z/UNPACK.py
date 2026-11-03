import os;from pathlib import Path;assert os.uname().machine=='aarch64';assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100';assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='4365d744-ddef-4325-a264-e7bb57cc9bb8';
import hashlib,gzip,json
p=Path('/home/root/aura-realtime-vision-20261007/motion-bundle-68bd0def762cc3cf0e8ba306bb417e27f3f3d3ab69ca64dd97fed0df4a85f5dc.upload')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='68bd0def762cc3cf0e8ba306bb417e27f3f3d3ab69ca64dd97fed0df4a85f5dc'
sources=json.loads(gzip.decompress(p.read_bytes()))
hashes={'vision_core.py': '9629102ced2856bbd0c120b9c5e3df36c224424165bb980b90be42350ae8a700', 'x11_window.py': '69cb8da8b16f9e10e0dd31b7c575f69c4a740989d2eb9465737a3e9882b9a24a', 'realtime_vision.py': '11e7a27b49a0ae71942f4d9b34e429cc9d4cfc8bd8a94b37cf88123cc3ca14c6', 'test_vision_core.py': '86f39de2b5484cb721cf26767381c50b5069e8253378b6bc1f81716730336834', 'motion_service.py': '369c3156e000bf001355e18cd60e7857feeb5140e832e81d45699a5042b456c8', 'test_motion_service.py': '099c4d59e13bdc886eb5135464c68242a70f40a0ef15733306609d2b6901c6e2', 'motion_replay.py': 'f987bd4b0683d05ac910a1dff0b52757914c5f673050f2e7ba91f86d44564bde', 'board_motion_launch.py': '5934dc5db04ee0f0cd599976e40e02cbec8b487dddd10c22f00fd13c3c5cb3fc'}
assert set(sources)==set(hashes)
release=Path('/home/root/aura-realtime-vision-20261007/releases/68bd0def762cc3cf')
release.mkdir(parents=True,exist_ok=False)
for name,source in sources.items():
 assert hashlib.sha256(source.encode()).hexdigest()==hashes[name]
 (release/name).write_text(source)
stage={"release":str(release),"hashes":hashes,"base":{'boot_id': '4365d744-ddef-4325-a264-e7bb57cc9bb8', 'pid': 2138, 'current_release': '/home/root/aura-realtime-vision-20261007/releases/4ffe392685dbfad1', 'hashes': {'vision_core.py': '9629102ced2856bbd0c120b9c5e3df36c224424165bb980b90be42350ae8a700', 'x11_window.py': '69cb8da8b16f9e10e0dd31b7c575f69c4a740989d2eb9465737a3e9882b9a24a', 'realtime_vision.py': '7c2108f407d9fc4705054b43dd20b71df524fb4407ac71a60889de740fdb251b', 'test_vision_core.py': '86f39de2b5484cb721cf26767381c50b5069e8253378b6bc1f81716730336834', 'board_launch.py': '66225075e8f3d9af5b6d1fdb357ce33e5a418cc85435dabac084a62a611f9bf5'}}}
Path('/home/root/aura-realtime-vision-20261007/motion-staged.json').write_text(json.dumps(stage))
print(json.dumps(stage))
