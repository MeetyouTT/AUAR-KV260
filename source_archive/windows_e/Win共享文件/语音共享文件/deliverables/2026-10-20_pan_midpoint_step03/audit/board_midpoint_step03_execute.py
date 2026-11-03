"""Run one bounded reverse calibration with a verified previous hardware context."""
import base64,contextlib,gzip,hashlib,io,json,os,subprocess,sys,time,traceback,urllib.request
from pathlib import Path
BOOT='3e1add36-b917-4289-91dc-699348528782'
TX=Path('/home/root/aura-pan-follow-20261020/midpoint-step-03')
RAW=gzip.decompress(base64.b64decode('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'))
SHA='a1cb5d9731ca63d5386f55a3e561632e93c84fa0c3d0bc19006770251404be18'
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
gui_at_start={k:gui.get(k) for k in ['phase','playing']}
gui_at_start['automatic_state']=gui.get('automatic_conversation',{}).get('state')
identity_state=get(8790,'/v1/ui/status').get('modules',{}).get('identity',{}).get('state')
assert identity_state not in ['ENROLLING','SAMPLING'], 'Identity sampling in progress; no axis test'
TX.mkdir(parents=True,exist_ok=False);os.chmod(TX,0o700)
script=TX/'midpoint1490_bench.py'
with script.open('xb') as f:f.write(RAW)
report={'status':'STARTING','boot_id':BOOT,'test_script_sha256':SHA,
 'authorization':'Continue calibration after user reports increased pulse moves farther right; reverse via 1500us to 1490us; epoch 3; two 2s holds',
 'test_scope':'MIDPOINT1490-4S','field_feedback':'更偏右了','previous_test_point_us':1520,'before':before,'automatic_following_enabled':False,
 'gui_at_start':gui_at_start,'identity_state_at_start':identity_state}
(TX/'authorization.json').write_text(json.dumps(report,indent=2)+'\n')
namespace={'__name__':'frozen_bench','__file__':str(script)}
exec(compile(RAW,str(script),'exec'),namespace)
sys.argv=[str(script),'--execute','--confirmation','MIDPOINT1490-4S','--output',str(TX/'bench.json')]
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
