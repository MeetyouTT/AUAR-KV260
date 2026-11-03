
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

assert active()==[] and rows()[APP]['type']=='PL_FLAT'
output=run(['xmutil','loadapp',APP])
assert 'loaded to slot 0' in output and 'Error' not in output,output
assert active()==[APP] and fw()==FW and state()=='operating'
assert len(list(Path('/sys/kernel/config/device-tree/overlays').iterdir()))==1
summary=Path('/sys/kernel/debug/clk/clk_summary').read_text()
clock_rows=[line.split() for line in summary.splitlines() if line.split() and line.split()[0]=='pl0_ref']
assert len(clock_rows)==1 and int(clock_rows[0][1])>0
rate=int(clock_rows[0][4]);assert abs(rate-99999001)<=99999001*.001
text=run(['python3','-B',str(package/'board/probe.py')],10);registers=json.loads(text)
expected={'ip_id':'0x50574d54','abi':'0x10000','build_id':'0x3eaeabab','status':4,
 'period_ticks':9999900,'pulse_ticks':9999900,'frames_left':0,'clock_hz':99999001,'run_frames':0,'pulse_us':100000}
assert registers==expected,registers
result={'active':active(),'firmware':fw(),'fpga_state':state(),'pl0_actual_hz':rate,
 'mode':'static-high','duty_percent':100,
 'registers':registers,'start_sent':False,'output_register_low':True,'load_output':output}
(archive.parent/'loaded-idle.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
