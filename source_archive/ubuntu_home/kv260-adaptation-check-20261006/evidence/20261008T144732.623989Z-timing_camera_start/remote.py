from pathlib import Path
import hashlib,sys
assert hashlib.sha256(Path('/home/root/aura-adaptation-20261006/timing-fix-a312fd5f10cb4705/board_direction_bench.py').read_bytes()).hexdigest()=='8fd64a2d6cc7485dc9146f421105fcba3c2438a0b595b4425d68fd9037bdf76e'
assert hashlib.sha256(Path('/home/root/aura-adaptation-20261006/timing-fix-a312fd5f10cb4705/direction_bench.py').read_bytes()).hexdigest()=='42e17352881897c244d20463a33a600ca4f26034909c9d60ca335376ea0aec0f'
assert hashlib.sha256(Path('/home/root/aura-adaptation-20261006/timing-fix-a312fd5f10cb4705/camera_timing_launch.py').read_bytes()).hexdigest()=='a211f9ea4c77f63d7f6e5429e79a7c9eca65c7bb8e3287f58fb26e3010757887'
p=Path('/home/root/aura-adaptation-20261006/timing-fix-a312fd5f10cb4705/camera_timing_launch.py');sys.path.insert(0,str(p.parent));exec(compile(p.read_bytes(),str(p),"exec"),{"__name__":"__main__","__file__":str(p)})
