"""Rebind the audited runtime to the inventoried boot; load with PWM disabled."""
import hashlib,json,sys,time
from pathlib import Path
BOOT='c2753755-e758-4ab6-a4b6-2929271aa723'
ROOT=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert hashlib.sha256((ROOT/'common.py').read_bytes()).hexdigest()=='f529550d981a6114b669353db08c05174a6e45221c6385456d40896c18b0cc4a'
assert hashlib.sha256((ROOT/'load.py').read_bytes()).hexdigest()=='39280c42c39ca5644193cdca105f85b13ac647c78605f252793271a5223d20ae'
# Host comparison: every FDT property is unchanged; candidate overlay merges.
assert hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest()=='6bb361ca9d631acb7f7197f06a5d407a88f5a34b4095539bde471b4d30a4dc7c'
sys.path.insert(0,str(ROOT))
import common
# Explicit new-boot binding after hardware and source verification. No file edit.
common.BOOT=BOOT
common.guard();common.check_runtime()
saved=common.save
def save(name,data):
 data['boot_binding_scope']='CONTROLLED_BENCH_ONLY_NOT_PHYSICAL_CALIBRATION'
 saved('newboot-'+str(time.time_ns())+'-'+name,data)
common.save=save
p=ROOT/'load.py'
exec(compile(p.read_bytes(),str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
