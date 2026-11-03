"""Run exactly the frozen, user-authorized two-second first-position test once."""
import base64,contextlib,gzip,hashlib,io,json,os,subprocess,sys,time,traceback,urllib.request
from pathlib import Path
BOOT='3e1add36-b917-4289-91dc-699348528782'
TX=Path('/home/root/aura-pan-follow-20261020/first-pulse-01')
RAW=gzip.decompress(base64.b64decode('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'))
SHA='919a590181e649680d91c734724892a84d5a17469bb66320efb89db804bc5d51'
assert hashlib.sha256(RAW).hexdigest()==SHA
assert os.uname().machine=='aarch64' and os.geteuid()==0
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()=='aura-visual-servo-b4096-v1.bit.bin'
assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
assert Path('/etc/vart.conf').read_text()=='firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-v1/aura-visual-servo-b4096-v1.xclbin\n'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as r:return json.load(r)
def unit(unit):
 return {k:subprocess.check_output(['systemctl','show',unit,'-p',k,'--value'],text=True,timeout=5).strip()
         for k in ['ActiveState','MainPID','WorkingDirectory']}
def health():
 v=get(8790,'/health')
 assert not v['camera_error'] and not v['detector_error'] and v['identity_recognition']
 return {k:v.get(k) for k in ['pid','detected_frames','observation_age_ms','detection_hz','identity_recognition','camera_error','detector_error']}
before={u:unit(u) for u in ['aura-camera-ui.service','aura-avatar-ui.service']}
before['camera']=health()
gui=get(8783,'/api/state')
assert gui['phase']=='IDLE' and not gui['playing']
assert gui.get('automatic_conversation',{}).get('state')=='STOPPED'
TX.mkdir(parents=True,exist_ok=False);os.chmod(TX,0o700)
script=TX/'first_pulse_bench.py'
with script.open('xb') as f:f.write(RAW)
report={'status':'STARTING','boot_id':BOOT,'test_script_sha256':SHA,
 'authorization':'User explicitly requested immediate test after first-position clearance explanation',
 'authorized_test':'INIT1500-PM4-2S','before':before,'automatic_following_enabled':False}
(TX/'authorization.json').write_text(json.dumps(report,indent=2)+'\n')
namespace={'__name__':'frozen_bench','__file__':str(script)}
exec(compile(RAW,str(script),'exec'),namespace)
sys.argv=[str(script),'--execute','--confirmation','INIT1500-PM4-2S','--output',str(TX/'bench.json')]
captured=io.StringIO();start=time.monotonic()
try:
 with contextlib.redirect_stdout(captured):namespace['main']()
 report['status']='FINITE_FIRST_PULSE_TEST_FINISHED'
except BaseException as exc:
 report['status']='FINITE_FIRST_PULSE_TEST_FAILED'
 report['error']=type(exc).__name__+': '+str(exc)
 (TX/'failure-traceback.txt').write_text(traceback.format_exc())
report['script_elapsed_s']=round(time.monotonic()-start,3)
if (TX/'bench.json').exists():
 report['bench']=json.loads((TX/'bench.json').read_text())
try:
 import common
 from vsrv_driver import VSRVDriver
 with common.open_registers() as registers:
  driver=VSRVDriver(registers,0x14da0e60,BOOT)
  final=driver.status()
  assert not final['active'] and not final['armed'] and final['lease_left_ms']==0
  report['independent_final_readback']=final
except BaseException as exc:report['final_readback_error']=type(exc).__name__+': '+str(exc)
report['after']={u:unit(u) for u in ['aura-camera-ui.service','aura-avatar-ui.service']}
try:report['after']['camera']=health()
except Exception as exc:report['after']['camera_error']=str(exc)
(TX/'result.json').write_text(json.dumps(report,indent=2)+'\n')
summary={k:v for k,v in report.items() if k!='bench'}
if 'bench' in report:
 b=report['bench']
 summary['bench']={k:v for k,v in b.items() if k!='events'}
 summary['bench']['commands_accepted']=len(b['events'])
 summary['bench']['target_pulses_us']=sorted(set(e['target_us'] for e in b['events']))
print(json.dumps(summary),flush=True)
