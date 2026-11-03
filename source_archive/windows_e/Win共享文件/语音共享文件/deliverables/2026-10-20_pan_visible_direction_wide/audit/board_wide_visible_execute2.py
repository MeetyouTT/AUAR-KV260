"""Execute one user-requested wider finite sweep after preparation and a start cue."""
import base64,contextlib,gzip,hashlib,io,json,os,subprocess,sys,time,traceback,urllib.request
from pathlib import Path
BOOT='3e1add36-b917-4289-91dc-699348528782'
TX=Path('/home/root/aura-pan-follow-20261020/visible-direction-wide-01')
RAW=gzip.decompress(base64.b64decode('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'))
SHA='85e66459ccdd8cf3009a6666d879de87c3afe843548936d216996767a9640815'
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
script=TX/'wide_sweep_bench.py'
with script.open('xb') as f:f.write(RAW)
report={'status':'STARTING','boot_id':BOOT,'test_script_sha256':SHA,
 'authorization':'User explicitly requested larger movement; one bounded 1420..1580us sweep,9s,final1490us',
 'test_scope':'VISIBLE1420-1580-9S','field_feedback':'动作再大一点','previous_test_point_us':1490,'before':before,'automatic_following_enabled':False,
 'gui_at_start':gui_at_start,'identity_state_at_start':identity_state}
(TX/'authorization.json').write_text(json.dumps(report,indent=2)+'\n')
namespace={'__name__':'frozen_bench','__file__':str(script)}
exec(compile(RAW,str(script),'exec'),namespace)
sys.argv=[str(script),'--execute','--confirmation','VISIBLE1420-1580-9S','--output',str(TX/'bench.json')]
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
