
import base64,hashlib,json,os,re,shutil,subprocess,sys,tarfile,time
from pathlib import Path
archive=Path(sys.argv[1]);expected_hash=sys.argv[2];package=archive.parent/'unpacked'
APP='aura-square10';OFFICIAL='kv260-benchmark-b4096';FW='aura_square10.bit.bin'
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

assert active()==[APP] and fw()==FW and state()=='operating'
original=check_official_hashes()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==original['boot_id']
manifest=json.loads((package/'manifest.json').read_text())
for relative,meta in manifest.items():
 assert hashlib.sha256((package/relative).read_bytes()).hexdigest()==meta['sha256']
 if relative.startswith('lib/firmware/'):
  assert hashlib.sha256((Path('/')/relative).read_bytes()).hexdigest()==meta['sha256']
samples=[];started=time.monotonic()
for index in range(48):
 before=time.monotonic()-started
 values=json.loads(run([str(package/'board/mmio32'),'inspect'],5))
 after=time.monotonic()-started
 assert values['build_id']=='0x79b89dfe' and values['status'] in (5,7)
 assert values['period_ticks']==9999900 and values['pulse_ticks']==4999950
 samples.append({'before_seconds':before,'after_seconds':after,'status':values['status']})
 time.sleep(.01)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==original['boot_id']
print(json.dumps({'boot_id':original['boot_id'],'firmware':FW,'samples':samples,
 'output_logic_levels_seen':sorted(set((s['status']>>1)&1 for s in samples)),
 'writes_performed':False,'external_voltage_measured':False}))
