from pathlib import Path
import hashlib,sys
assert hashlib.sha256(Path('/home/root/aura-adaptation-20261006/direction-bench-a115f32fb2e5a3e0/camera_direction_status_launch.py').read_bytes()).hexdigest()=='07f8661e2c5b59e21f49f64163f9ccfac4d6d3c2eef80b56e9d14d87c691163b'
p=Path('/home/root/aura-adaptation-20261006/direction-bench-a115f32fb2e5a3e0/camera_direction_status_launch.py');sys.path.insert(0,str(p.parent));exec(compile(p.read_bytes(),str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
