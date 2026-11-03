import contextlib,hashlib,io,json,sys,time
from pathlib import Path
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
P=F/'fixed-motion-visible-v2';R=Path('/home/root/aura-pan-current-20261024/da36c36a')
assert hashlib.sha256((F/'preview-motion-v1/preview_motion.py').read_bytes()).hexdigest()=='324e13111c2412831e9d7f09240116cc53cfcbde21f3bea71f7fdefabaf12a17'
assert hashlib.sha256((P/'package-manifest.json').read_bytes()).hexdigest()=='6b9cddcfeb78cd49708a01b9f99e5b20f894448818849376556a6a596bc09b83'
sys.path[:0]=[str(P),str(F/'preview-motion-v1')]
import board_fixed_cli
from preview_motion import PreviewMotionObserver
board_fixed_cli.preflight('6b9cddcfeb78cd49708a01b9f99e5b20f894448818849376556a6a596bc09b83')
receipt=R/'attended-fixed-reference.json';raw=receipt.read_bytes();ref=json.loads(raw)
assert ref['source']=='USER_REQUESTED_REPEAT_AFTER_ORIGINAL_REGION_DISPLAY_RESTORED'
trial=R/('fixed-trajectory-'+ref['authorization_id']+'.json');assert not trial.exists()
observer=PreviewMotionObserver(duration_s=9.,interval_s=.25).start();ready=observer.wait_baseline(timeout_s=2.)
failure=None;report={};observed={}
try:
 sys.argv=['board_fixed_cli','--execute','--package-sha256','6b9cddcfeb78cd49708a01b9f99e5b20f894448818849376556a6a596bc09b83',
  '--reference-sha256',hashlib.sha256(raw).hexdigest()]
 with contextlib.redirect_stdout(io.StringIO()):board_fixed_cli.main()
except BaseException as error:failure=error
finally:
 if trial.exists() and trial.stat().st_size:
  report=json.loads(trial.read_text())
 stopped=(report.get('result') or {}).get('stopped_readback') or {}
 if stopped.get('flags')==0 and stopped.get('lease_left_ms')==0:
  time.sleep(.3)
  observed=observer.close_after_stop(stopped,timeout_s=1.)
 else:
  observer.stop_event.set();observed=observer.snapshot();observed['no_join_before_confirmed_motor_stop']=True
 observed.update(baseline_ready=ready,control_report_path=str(trial),control_status=report.get('status'),
  control_started_mono_s=(report.get('result') or {}).get('started_mono_s'),
  control_completed_mono_s=(report.get('result') or {}).get('completed_mono_s'))
 output=trial.with_suffix('.preview-motion.json')
 with output.open('x') as out:json.dump(observed,out,indent=2);out.write('\n')
print(json.dumps({'status':report.get('status','CONTROL_REPORT_UNAVAILABLE'),'control_report':str(trial),
 'observer_report':str(output),'result':report.get('result'),'preview_motion':observed,
 'error':type(failure).__name__+': '+str(failure) if failure else None}))
if failure is not None:raise failure
