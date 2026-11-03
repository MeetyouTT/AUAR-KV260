
import base64,hashlib,json,os,re,shutil,subprocess,sys,tarfile,time
from pathlib import Path
archive=Path(sys.argv[1]);expected_hash=sys.argv[2];package=archive.parent/'unpacked'
APP='aura-pin3-pwm';OFFICIAL='kv260-benchmark-b4096';FW='aura_pin3_pwm.bit.bin'
def run(argv,timeout=45):
 p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError(str(argv)+': '+p.stdout)
 return p.stdout
def rows():
 result={}
 for line in run(['xmutil','listapps'],12).splitlines():
  f=line.split()
  if len(f)==6 and f[1] in ('XRT_FLAT','PL_FLAT'):
   result[f[0]]={'type':f[1],'slot':f[-1]}
 return result
def active():return [k for k,v in rows().items() if v['slot'].rstrip(',')=='0']
def fw():return Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
def state():return Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()
def guard():
 assert os.uname().machine=='aarch64' and os.geteuid()==0
 assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
 assert any(x.split()[:2]==['/dev/mmcblk1p2','/'] for x in Path('/proc/mounts').read_text().splitlines())
 assert run(['systemctl','is-active','dfx-mgr']).strip()=='active'
def no_clients():
 assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0','ZOCL has clients'
 for p in Path('/sys/kernel/debug/dri').glob('*/clients'):
  if p.parent.name!='0':assert len(p.read_text().splitlines())<=1,'Accelerator DRM client present'
def check_official_hashes():
 original=json.loads((archive.parent/'original-state.json').read_text())
 for p,h in original['firmware_hashes'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
 return original
guard()

assert active()==[OFFICIAL] and fw()==OFFICIAL+'.bit.bin'
check_official_hashes()
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected_hash
with tarfile.open(archive,'r:gz') as tar:
 entries=tar.getmembers();names=[x.name for x in entries]
 assert len(names)==len(set(names))==8
 manifest=json.loads(tar.extractfile('manifest.json').read())
 assert set(names)==set(manifest)|{'manifest.json'} and len(manifest)==7
 package.mkdir(exist_ok=False)
 for entry in entries:
  rel=Path(entry.name)
  assert entry.isfile() and not rel.is_absolute() and '..' not in rel.parts
  data=tar.extractfile(entry).read()
  if entry.name!='manifest.json':
   meta=manifest[entry.name]
   assert len(data)==meta['bytes'] and hashlib.sha256(data).hexdigest()==meta['sha256']
  p=package/rel;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(data)
  p.chmod(0o755 if entry.name=='board/mmio32' else 0o644)
identity=json.loads((package/'evidence/accessor_identity.json').read_text())
assert hashlib.sha256((package/'board/mmio32').read_bytes()).hexdigest()==identity['binary_sha256']
p=subprocess.run([str(package/'board/mmio32')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=5)
assert p.returncode==2 and p.stderr.strip()=='usage: mmio32 inspect|start|stop|scratch',p.stderr
print(json.dumps({'unpacked':str(package),'files_verified':len(manifest),'accessor_runtime_without_MMIO':True}))
