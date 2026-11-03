"""Run the unchanged bounded bench, recording the exact stop observation."""
import hashlib,sys
from pathlib import Path
BOOT='c2753755-e758-4ab6-a4b6-2929271aa723'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
root=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
assert hashlib.sha256((root/'common.py').read_bytes()).hexdigest()=='f529550d981a6114b669353db08c05174a6e45221c6385456d40896c18b0cc4a'
sys.path.insert(0,str(root));import common
common.BOOT=BOOT;common.guard();common.check_runtime()
p=Path('/home/root/aura-adaptation-20261006/timing-fix-a312fd5f10cb4705/board_direction_bench.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='8fd64a2d6cc7485dc9146f421105fcba3c2438a0b595b4425d68fd9037bdf76e'
assert hashlib.sha256((p.parent/'direction_bench.py').read_bytes()).hexdigest()=='42e17352881897c244d20463a33a600ca4f26034909c9d60ca335376ea0aec0f'
source=p.read_text()
old="   if decision['kind']=='STOP':reason=decision['reason'];break"
new="   if decision['kind']=='STOP':\n    reason=decision['reason'];events.append(dict(decision,observation=s,elapsed_s=now-start));break"
assert source.count(old)==1
source=source.replace(old,new,1)
sys.path.insert(0,str(p.parent))
exec(compile(source,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
