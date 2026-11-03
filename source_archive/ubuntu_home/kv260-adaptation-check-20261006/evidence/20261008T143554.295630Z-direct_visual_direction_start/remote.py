from pathlib import Path
import hashlib,sys
assert hashlib.sha256(Path('/home/root/aura-adaptation-20261006/direct-observation-59ebcba44e16f4ff/board_direction_bench.py').read_bytes()).hexdigest()=='1618643f138e236cb4855540c172846dfac4ebe992ad8d521d5aef0be7b927b5'
assert hashlib.sha256(Path('/home/root/aura-adaptation-20261006/direct-observation-59ebcba44e16f4ff/direction_bench.py').read_bytes()).hexdigest()=='42e17352881897c244d20463a33a600ca4f26034909c9d60ca335376ea0aec0f'
assert hashlib.sha256(Path('/home/root/aura-adaptation-20261006/direct-observation-59ebcba44e16f4ff/camera_observation_launch.py').read_bytes()).hexdigest()=='8131c6fa7aa8703510dae050123a10f20db933a567fdc6807693e2e572162aa8'
p=Path('/home/root/aura-adaptation-20261006/direct-observation-59ebcba44e16f4ff/board_direction_bench.py');sys.path.insert(0,str(p.parent));exec(compile(p.read_bytes(),str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
