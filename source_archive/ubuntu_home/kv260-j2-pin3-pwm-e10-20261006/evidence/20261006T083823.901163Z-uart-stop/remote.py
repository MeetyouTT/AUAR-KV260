
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

assert active()==[APP] and fw()==FW and state()=='operating'
original=check_official_hashes()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==original['boot_id'],'boot changed'
manifest=json.loads((package/'manifest.json').read_text())
for relative,meta in manifest.items():
 p=package/relative
 assert hashlib.sha256(p.read_bytes()).hexdigest()==meta['sha256']
 if relative.startswith('lib/firmware/'):
  assert hashlib.sha256((Path('/')/relative).read_bytes()).hexdigest()==meta['sha256']
summary=Path('/sys/kernel/debug/clk/clk_summary').read_text()
lines=[x.split() for x in summary.splitlines() if x.split() and x.split()[0]=='pl0_ref']
assert len(lines)==1 and int(lines[0][1])>0
rate=int(lines[0][4]);assert abs(rate-99999001)<=99999001*.001
action=sys.argv[3]
command=['python3','-B',str(package/'board/probe.py')]
if action in ('start','stop','scratch'):command.append('--'+action)
registers=json.loads(run(command,10))
assert registers['frames_left']==0
running=bool(registers['status']&1)
if action=='start':assert running and registers['status'] in (5,7)
elif action in ('stop','scratch'):assert registers['status']==4
else:assert registers['status'] in (4,5,7)
assert registers['ip_id']=='0x50574d54' and registers['build_id']=='0x2a3aca85'
assert registers['run_frames']==0 and registers['pulse_us']==1500
assert registers['period_ticks']==1999980 and registers['pulse_ticks']==149999
print(json.dumps({'action':action,'registers':registers,'pl0_actual_hz':rate,
 'boot_id':original['boot_id'],
 'continuous_running':running,'output_register_low':not bool(registers['status'] & 2),
 'external_waveform_verified':False}))
