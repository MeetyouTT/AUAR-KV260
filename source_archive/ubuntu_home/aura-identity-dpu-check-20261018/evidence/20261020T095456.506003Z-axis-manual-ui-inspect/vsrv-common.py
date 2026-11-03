import hashlib,json,subprocess,time,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MANIFEST=json.loads((ROOT/'payload_manifest.json').read_text())
APP='aura-visual-servo-b4096-v1';BASELINE='kv260-benchmark-b4096'
BOOT='f7a3ff07-fc20-4804-af12-c314a7a1847a'
def guard():
 assert os.uname().machine=='aarch64' and os.geteuid()==0
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
 for name,digest in MANIFEST['payload_files'].items():
  assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
def run(argv,timeout=45,env=None):
 p=subprocess.run(argv,capture_output=True,text=True,timeout=timeout,env=env)
 assert p.returncode==0,(argv,p.stdout,p.stderr)
 return p.stdout
def rows():
 return {f[0]:f[-1].rstrip(',') for f in (s.split() for s in run(['xmutil','listapps'],12).splitlines()) if len(f)==6 and f[1] in ('XRT_FLAT','PL_FLAT')}
def active():return [k for k,v in rows().items() if v=='0']
def firmware():return Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
def runtime_hashes():return {'/'+k:v for k,v in MANIFEST['runtime_files'].items()}
def check_runtime():
 for p,d in runtime_hashes().items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==d,p
def no_clients():
 assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0'
 for p in Path('/sys/kernel/debug/dri').glob('*/clients'):
  if p.parent.name!='0':assert len(p.read_text().splitlines())<=1,p.read_text()
def open_registers():
 guard();check_runtime();assert active()==[APP] and firmware()==APP+'.bit.bin'
 from vsrv_transport import NativeRegisters
 return NativeRegisters(ROOT/'libvsrv.so',MANIFEST['payload_files']['libvsrv.so'],BOOT,runtime_hashes())
def save(name,data):
 data['boot_id']=BOOT;(ROOT/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps(data,indent=2),flush=True)
