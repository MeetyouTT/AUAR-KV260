"""Run one bounded midpoint calibration step to a historically board-tested target."""
import base64,contextlib,gzip,hashlib,io,json,os,subprocess,sys,time,traceback,urllib.request
from pathlib import Path
BOOT='3e1add36-b917-4289-91dc-699348528782'
TX=Path('/home/root/aura-pan-follow-20261020/midpoint-step-02')
RAW=gzip.decompress(base64.b64decode('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'))
SHA='f3e019c4c7769e306443e2060b969442e9667149ac42081a251e913697742a2a'
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
script=TX/'midpoint1520_bench.py'
with script.open('xb') as f:f.write(RAW)
report={'status':'STARTING','boot_id':BOOT,'test_script_sha256':SHA,
 'authorization':'Continue user-authorized calibration after 1504us produced almost no visible change; bounded 16us step to 1520us; new epoch 2',
 'test_scope':'MIDPOINT1520-2S','field_feedback':'几乎没有变化','previous_test_point_us':1504,'before':before,'automatic_following_enabled':False}
(TX/'authorization.json').write_text(json.dumps(report,indent=2)+'\n')
namespace={'__name__':'frozen_bench','__file__':str(script)}
exec(compile(RAW,str(script),'exec'),namespace)
sys.argv=[str(script),'--execute','--confirmation','MIDPOINT1520-2S','--output',str(TX/'bench.json')]
captured=io.StringIO();start=time.monotonic()
try:
 with contextlib.redirect_stdout(captured):namespace['main']()
 report['status']='FINITE_MIDPOINT_STEP_FINISHED'
except BaseException as exc:
 report['status']='FINITE_MIDPOINT_STEP_FAILED'
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
