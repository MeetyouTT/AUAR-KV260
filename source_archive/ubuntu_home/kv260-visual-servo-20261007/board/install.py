"""Install a unique, verified bench app; keep the baseline unchanged."""
from common import *
import tarfile
guard()
assert active()==[BASELINE] and firmware()==BASELINE+'.bit.bin'
import ctypes
lib=ctypes.CDLL(str(ROOT/'libvsrv.so'));lib.vsrv_open.argtypes=[ctypes.c_char_p,ctypes.POINTER(ctypes.c_void_p)]
handle=ctypes.c_void_p()
assert lib.vsrv_open(BOOT.encode(),ctypes.byref(handle))==1 and not handle.value,'Native guard must refuse baseline before MMIO'
assert hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest()==MANIFEST['base_dt_sha256']
no_clients()
archive=ROOT.parent/'firmware.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==MANIFEST['firmware_archive_sha256']
official=Path('/lib/firmware/xilinx')/BASELINE
snapshot={'firmware_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in official.iterdir() if p.is_file()},
 'vart_conf':Path('/etc/vart.conf').read_text(),'preview':json.loads(Path('/home/root/aura-realtime-vision-20261007/current.json').read_text())}
assert snapshot['firmware_hashes']==MANIFEST['baseline_hashes']
with (ROOT/'baseline-snapshot.json').open('x') as f:json.dump(snapshot,f,indent=2)
dest=Path('/lib/firmware/xilinx')/APP;assert not dest.exists()
with tarfile.open(archive,'r:gz') as t:
 entries=t.getmembers();assert {x.name for x in entries}==set(MANIFEST['runtime_files'])|{'manifest.json'}
 dest.mkdir()
 for e in entries:
  assert e.isfile() and not Path(e.name).is_absolute() and '..' not in Path(e.name).parts
  if e.name=='manifest.json':continue
  assert Path(e.name).parent==Path('lib/firmware/xilinx')/APP
  d=t.extractfile(e).read();assert hashlib.sha256(d).hexdigest()==MANIFEST['runtime_files'][e.name]
  with (dest/Path(e.name).name).open('xb') as f:f.write(d);f.flush();os.fsync(f.fileno())
check_runtime()
deadline=time.monotonic()+8
while APP not in rows() and time.monotonic()<deadline:time.sleep(.2)
assert rows()[APP]=='-1' and active()==[BASELINE]
save('installed',{'passed':True,'application':APP,'motion_emitted':False,'official_unchanged':True,'native_wrong_firmware_guard_passed':True})
