import fcntl,hashlib,json,sys,time
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/fixed-motion-bench-v2');sys.path.insert(0,str(P))
from board_fixed_cli import preflight,R,OLD,BOOT,OPS
manifest,control=preflight('c36cc7a0c2f0d3bea609bd88e6d6cbc01b1d03e6446d5ac46b743e4490404f8b')
path=R/'attended-fixed-reference.json';original=path.read_bytes();ref=json.loads(original)
trial=R/('fixed-trajectory-'+ref['authorization_id']+'.json');prior=json.loads(trial.read_text())
assert prior['status']=='FIXED_TRAJECTORY_STOPPED_OBSERVATION_PENDING'
expected=prior['result']['stopped_readback'];assert expected['width_us']==expected['target_us']==1420 and expected['flags']==0 and expected['lease_left_ms']==0
C=OPS/'pan-face-edge-v5/continuous-v10r15';sys.path.extend([str(C),str(OLD/'driver')])
from batch_transport import BatchRegisters
from batch_driver import BatchDriver
lib=C/'libvsrv_batch.so';pin=next(x['sha256'] for x in control['files'] if x['destination']==str(lib))
with (OPS/'operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with BatchRegisters(lib,pin,BOOT,manifest['runtime_files']) as io:
  device=BatchDriver(io,0x778d2512,BOOT);current=device.status();assert current==expected
  stopped=device.stop();assert stopped['flags']==0 and stopped['lease_left_ms']==0 and stopped['width_us']==1420
 with (R/'attended-fixed-reference-before-visible.json').open('xb') as out:out.write(original)
 now=time.monotonic()
 ref.update(authorization_id='attended-visible-'+str(time.monotonic_ns()),authorization_recorded_mono_s=now,
  expires_mono_s=now+600,stopped_readback=stopped,source='SAME_CALIBRATED_SETUP_AND_COMPLETE_RETURN_PWM_WITH_CURRENT_USER_FEEDBACK',
  latest_user_feedback='幅度太小或没看清',physical_observation_of_previous_small_motion='INCONCLUSIVE',
  next_test={'duration_s':5,'sequence_us':[1420,1405,1420],'speed_us_s':10,'same_approved_bounds_us':[1402,1420]},
  current_position_basis='Original user-observed 1420 reference plus completed command return; no new mechanical angle measurement',
  previous_completed_trial=str(trial),previous_completed_trial_sha256=hashlib.sha256(trial.read_bytes()).hexdigest())
 tmp=R/'attended-fixed-reference.visible';tmp.write_text(json.dumps(ref,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
print(json.dumps({'status':'VISIBLE_TEST_REFERENCE_CONTINUITY_RECORDED_OUTPUT_OFF','readback':stopped,
 'receipt_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'next_sequence_us':[1420,1405,1420],
 'ARM_sent':False,'COMMIT_sent':False,'original_reference_observation_time_preserved':True}))
