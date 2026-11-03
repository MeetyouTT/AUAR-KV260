
import base64,hashlib,json,os,re,shutil,subprocess,sys,tarfile,time
from pathlib import Path
archive=Path(sys.argv[1]);expected_hash=sys.argv[2];package=archive.parent/'unpacked'
APP='aura-pin3-static';OFFICIAL='kv260-benchmark-b4096';FW='aura_pin3_static.bit.bin'
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

assert active()==[OFFICIAL] and fw()==OFFICIAL+'.bit.bin' and state()=='operating'
no_clients()
assert archive.is_file() and hashlib.sha256(archive.read_bytes()).hexdigest()==expected_hash
files=sorted(Path('/lib/firmware/xilinx/'+OFFICIAL).iterdir())
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
assert hashes['/lib/firmware/xilinx/'+OFFICIAL+'/'+OFFICIAL+'.bit.bin']=='7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f'
result={'active':active(),'firmware':fw(),'fpga_state':state(),'firmware_hashes':hashes,
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'vart_conf_b64':base64.b64encode(Path('/etc/vart.conf').read_bytes()).decode(),
 'all_dt_firmware_names':[p.read_bytes().rstrip(b'\0').decode() for p in Path('/proc/device-tree').rglob('firmware-name')]}
with (archive.parent/'original-state.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
