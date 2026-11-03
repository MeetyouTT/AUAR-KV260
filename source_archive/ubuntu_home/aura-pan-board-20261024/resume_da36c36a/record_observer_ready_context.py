import fcntl,hashlib,json,sys,time
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/fixed-motion-visible-v2');sys.path.insert(0,str(P))
from board_fixed_cli import preflight,R,OLD,BOOT,OPS,get
manifest,control=preflight('6b9cddcfeb78cd49708a01b9f99e5b20f894448818849376556a6a596bc09b83')
path=R/'attended-fixed-reference.json';original=path.read_bytes();ref=json.loads(original)
trial=R/('fixed-trajectory-'+ref['authorization_id']+'.json');prior=json.loads(trial.read_text())
result=prior['result'];assert prior['status']=='FAILED_NO_AUTOMATIC_RETRY' and result['error']['message']=='SUBMISSION_SPACING_NO_CATCHUP'
assert all(x['target_us']==1420 for x in result['commands'])
expected=result['stopped_readback'];assert expected['width_us']==expected['target_us']==1420 and expected['flags']==0 and expected['lease_left_ms']==0
face=None
C=OPS/'pan-face-edge-v5/continuous-v10r15';sys.path.extend([str(C),str(OLD/'driver')])
from batch_transport import BatchRegisters
from batch_driver import BatchDriver
lib=C/'libvsrv_batch.so';pin=next(x['sha256'] for x in control['files'] if x['destination']==str(lib))
with (OPS/'operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with BatchRegisters(lib,pin,BOOT,manifest['runtime_files']) as io:
  d=BatchDriver(io,0x778d2512,BOOT);assert d.status()==expected;stopped=d.stop()
  assert stopped['flags']==0 and stopped['lease_left_ms']==0 and stopped['width_us']==1420
 with (R/('attended-fixed-reference-before-observer-ready-'+str(time.monotonic_ns())+'.json')).open('xb') as out:out.write(original)
 now=time.monotonic();ref.update(authorization_id='observer-ready-r2-'+str(time.monotonic_ns()),
  authorization_recorded_mono_s=now,expires_mono_s=now+600,stopped_readback=stopped,
  source='USER_OBSERVER_READY_CONFIRMED',observer_confirmation='用户答“好了”，回应是否仍在设备旁能观察转轴',
  retry_basis='Previous attempt issued only 1420 holds and stopped; same requested 15us test and setup; user now confirmed ready to observe; fixed test is independent of face detection',
  prior_failed_trial=str(trial),prior_failed_trial_sha256=hashlib.sha256(trial.read_bytes()).hexdigest(),current_fresh_face=face)
 tmp=R/'attended-fixed-reference.visible-r2';tmp.write_text(json.dumps(ref,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
 s=json.loads((R/'state.json').read_text());s.update(phase='ATTENDED_VISIBLE_RETRY_PREPARED_OUTPUT_STOPPED',current_last_command_us=1420,
  current_stopped_readback=stopped,physical_reference_receipt=str(path),automatic_following=False)
 (R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'status':'VISIBLE_R2_CONTEXT_RECORDED_OUTPUT_OFF','readback':stopped,
 'receipt_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'fresh_face':face,'ARM_sent':False,'COMMIT_sent':False}))
