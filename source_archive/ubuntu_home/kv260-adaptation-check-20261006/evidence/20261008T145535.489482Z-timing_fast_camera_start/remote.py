from pathlib import Path
import hashlib,sys
p=Path('/home/root/aura-adaptation-20261006/timing-fast-camera-9e1be1f23ce94ae7/camera_fast_launch.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='498b972e9cb3cda962c40b1a0900aa0c16e02ed337c5368aaf5c054bf39e4bb9'
sys.path.insert(0,str(p.parent));exec(compile(p.read_bytes(),str(p),"exec"),{"__name__":"__main__","__file__":str(p)})
