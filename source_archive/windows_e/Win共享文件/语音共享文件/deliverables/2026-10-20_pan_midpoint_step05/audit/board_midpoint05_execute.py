"""Execute one user-requested finite 1450us correction after preparation and a start cue."""
import base64,contextlib,gzip,hashlib,io,json,os,subprocess,sys,time,traceback,urllib.request
from pathlib import Path
BOOT='3e1add36-b917-4289-91dc-699348528782'
TX=Path('/home/root/aura-pan-follow-20261020/midpoint-step-05')
RAW=gzip.decompress(base64.b64decode('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'))
SHA='d0a83fabfc1a66825fe2425ac54f292945941da934a8bd1a9b58526a58c1ddee'
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
 'authorization':'User saw the larger movement, reported residual right bias and requested another correction; one 1450us hold for2s from1470us',
 'test_scope':'MIDPOINT1450-2S','field_feedback':'还是朝右','previous_test_point_us':1470,'before':before,'automatic_following_enabled':False,
 'gui_at_start':gui_at_start,'identity_state_at_start':identity_state}
(TX/'authorization.json').write_text(json.dumps(report,indent=2)+'\n')
namespace={'__name__':'frozen_bench','__file__':str(script)}
exec(compile(RAW,str(script),'exec'),namespace)
sys.argv=[str(script),'--execute','--confirmation','MIDPOINT1450-2S','--output',str(TX/'bench.json')]
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
