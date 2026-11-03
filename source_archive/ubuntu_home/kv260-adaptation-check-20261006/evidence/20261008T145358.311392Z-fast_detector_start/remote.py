from pathlib import Path
import hashlib,sys
assert hashlib.sha256(Path('/home/root/aura-adaptation-20261006/detector-fast-7de5799a0afd4071/fast_detector_probe.py').read_bytes()).hexdigest()=='31540e898f44907c549533220234c04a9ba901b24b9a3d3429e90fcd1cff6cb9'
assert hashlib.sha256(Path('/home/root/aura-adaptation-20261006/detector-fast-7de5799a0afd4071/face_compat_fast.py').read_bytes()).hexdigest()=='ee34109e23423d99a4ea3ff75c2bf9d113329b1c8162cd02f30e7dfcfb6bfeaf'
p=Path('/home/root/aura-adaptation-20261006/detector-fast-7de5799a0afd4071/fast_detector_probe.py');sys.path.insert(0,str(p.parent));exec(compile(p.read_bytes(),str(p),"exec"),{"__name__":"__main__","__file__":str(p)})
