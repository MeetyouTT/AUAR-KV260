"""Execute one user-requested finite 1470us correction after preparation and a start cue."""
import base64,contextlib,gzip,hashlib,io,json,os,subprocess,sys,time,traceback,urllib.request
from pathlib import Path
BOOT='3e1add36-b917-4289-91dc-699348528782'
TX=Path('/home/root/aura-pan-follow-20261020/midpoint-step-04')
RAW=gzip.decompress(base64.b64decode('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'))
SHA='9b12dd9c4357b011e202ec2635f81db967ca17ad59f752460c303e3edac0ec88'
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
try:
 gui=get(8783,'/api/state')
except Exception as gui_exc:
 gui={'phase':'STATUS_UNAVAILABLE','playing':None,'automatic_conversation':{'state':'UNKNOWN'}}
gui_at_start={k:gui.get(k) for k in ['phase','playing']}
gui_at_start['automatic_state']=gui.get('automatic_conversation',{}).get('state')
identity_state=get(8790,'/v1/ui/status').get('modules',{}).get('identity',{}).get('state')
assert identity_state not in ['ENROLLING','SAMPLING'], 'Identity sampling in progress; no axis test'
TX.mkdir(parents=True,exist_ok=False);os.chmod(TX,0o700)
script=TX/'midpoint_step_bench.py'
with script.open('xb') as f:f.write(RAW)
report={'status':'STARTING','boot_id':BOOT,'test_script_sha256':SHA,
 'authorization':'User saw the larger movement, reported residual right bias and requested another correction; one 1470us hold for2s from1490us',
 'test_scope':'MIDPOINT1470-2S','field_feedback':'看清了，现在还有点向右偏转，再转一下','previous_test_point_us':1490,'before':before,'automatic_following_enabled':False,
 'gui_at_start':gui_at_start,'identity_state_at_start':identity_state}
(TX/'authorization.json').write_text(json.dumps(report,indent=2)+'\n')
namespace={'__name__':'frozen_bench','__file__':str(script)}
exec(compile(RAW,str(script),'exec'),namespace)
sys.argv=[str(script),'--execute','--confirmation','MIDPOINT1470-2S','--output',str(TX/'bench.json')]
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
