from pathlib import Path
import hashlib,sys
p=Path('/home/root/aura-adaptation-20261006/timing-single-46f0ec7fe2c24bf9/camera_single_thread_launch.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='f906a74d04c5cb1dd5a0dcded84116bf265d6b560d0ca91f2169129c54fd869d'
sys.path.insert(0,str(p.parent));exec(compile(p.read_bytes(),str(p),"exec"),{"__name__":"__main__","__file__":str(p)})
