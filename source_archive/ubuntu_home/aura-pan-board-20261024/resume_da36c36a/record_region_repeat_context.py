import fcntl,hashlib,json,sys,time
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/fixed-motion-visible-v2');sys.path.insert(0,str(P))
from board_fixed_cli import preflight,R,OLD,BOOT,OPS
manifest,control=preflight('6b9cddcfeb78cd49708a01b9f99e5b20f894448818849376556a6a596bc09b83')
path=R/'attended-fixed-reference.json';original=path.read_bytes();ref=json.loads(original)
trial=R/('fixed-trajectory-'+ref['authorization_id']+'.json');prior=json.loads(trial.read_text())
assert prior['status']=='FIXED_TRAJECTORY_STOPPED_OBSERVATION_PENDING' and prior['result']['stop_confirmed']
expected=prior['result']['stopped_readback'];assert expected['width_us']==expected['target_us']==1420 and expected['flags']==0 and expected['lease_left_ms']==0
C=OPS/'pan-face-edge-v5/continuous-v10r15';sys.path.extend([str(C),str(OLD/'driver')])
from batch_transport import BatchRegisters
from batch_driver import BatchDriver
lib=C/'libvsrv_batch.so';pin=next(x['sha256'] for x in control['files'] if x['destination']==str(lib))
with (OPS/'operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with BatchRegisters(lib,pin,BOOT,manifest['runtime_files']) as io:
  d=BatchDriver(io,0x778d2512,BOOT);assert d.status()==expected;stopped=d.stop()
 with (R/('attended-reference-before-region-repeat-'+str(time.monotonic_ns())+'.json')).open('xb') as out:out.write(original)
 now=time.monotonic();ref.update(authorization_id='region-visible-repeat-'+str(time.monotonic_ns()),
  authorization_recorded_mono_s=now,expires_mono_s=now+600,stopped_readback=stopped,
  source='USER_REQUESTED_REPEAT_AFTER_ORIGINAL_REGION_DISPLAY_RESTORED',observer_confirmation='用户答“可以可以，重新来”',
  last_user_feedback='没看见，我原来划定的那个区域呢',previous_completed_trial=str(trial),
  previous_completed_trial_sha256=hashlib.sha256(trial.read_bytes()).hexdigest())
 tmp=R/'attended-fixed-reference.region-repeat';tmp.write_text(json.dumps(ref,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
print(json.dumps({'status':'REGION_REPEAT_REFERENCE_CONTEXT_READY','readback':stopped,
 'receipt_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'ARM_sent':False,'COMMIT_sent':False}))
