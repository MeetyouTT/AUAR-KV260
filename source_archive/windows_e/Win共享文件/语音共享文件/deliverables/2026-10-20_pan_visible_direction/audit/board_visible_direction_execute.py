"""Run one finite visible direction sweep with prior-context and STOP guards."""
import base64,contextlib,gzip,hashlib,io,json,os,subprocess,sys,time,traceback,urllib.request
from pathlib import Path
BOOT='3e1add36-b917-4289-91dc-699348528782'
TX=Path('/home/root/aura-pan-follow-20261020/visible-direction-01')
RAW=gzip.decompress(base64.b64decode('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'))
SHA='c058b361e5e0ef31b4435bd397d43460dd087ab3371e81376b09101e47865240'
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
script=TX/'visible_sweep_bench.py'
with script.open('xb') as f:f.write(RAW)
report={'status':'STARTING','boot_id':BOOT,'test_script_sha256':SHA,
 'authorization':'User requested retest and reported movement too small; one finite visible sweep 1460..1540us,6s,final1490us',
 'test_scope':'VISIBLE1460-1540-6S','field_feedback':'转动有点小，没看清','previous_test_point_us':1490,'before':before,'automatic_following_enabled':False,
 'gui_at_start':gui_at_start,'identity_state_at_start':identity_state}
(TX/'authorization.json').write_text(json.dumps(report,indent=2)+'\n')
namespace={'__name__':'frozen_bench','__file__':str(script)}
exec(compile(RAW,str(script),'exec'),namespace)
sys.argv=[str(script),'--execute','--confirmation','VISIBLE1460-1540-6S','--output',str(TX/'bench.json')]
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
