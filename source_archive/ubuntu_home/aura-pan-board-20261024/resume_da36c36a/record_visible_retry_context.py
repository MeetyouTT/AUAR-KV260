import fcntl,hashlib,json,sys,time
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/fixed-motion-visible-v1');sys.path.insert(0,str(P))
from board_fixed_cli import preflight,R,OLD,BOOT,OPS,get
manifest,control=preflight('fe434ca4841d4aef604cfc9dd3baa98c19bcb41469b2890cf00c075ecdc4189a')
path=R/'attended-fixed-reference.json';original=path.read_bytes();ref=json.loads(original)
trial=R/('fixed-trajectory-'+ref['authorization_id']+'.json');prior=json.loads(trial.read_text())
result=prior['result'];assert prior['status']=='FAILED_NO_AUTOMATIC_RETRY' and result['error']['message']=='SUBMISSION_SPACING_NO_CATCHUP'
assert all(x['target_us']==1420 for x in result['commands'])
expected=result['stopped_readback'];assert expected['width_us']==expected['target_us']==1420 and expected['flags']==0 and expected['lease_left_ms']==0
end=time.monotonic()+3;face=None
while time.monotonic()<end:
 p=get(8790,'/v1/motion/face/observation');now=int(time.monotonic()*1000)
 if p.get('state')=='READY' and 0<=now-p.get('source_mono_ms',0)<250:
  face=dict(source_frame_id=p['source_frame_id'],source_mono_ms=p['source_mono_ms'],received_mono_ms=now);break
 time.sleep(.05)
assert face is not None,'No fresh face at the attended camera; no retry context recorded'
C=OPS/'pan-face-edge-v5/continuous-v10r15';sys.path.extend([str(C),str(OLD/'driver')])
from batch_transport import BatchRegisters
from batch_driver import BatchDriver
lib=C/'libvsrv_batch.so';pin=next(x['sha256'] for x in control['files'] if x['destination']==str(lib))
with (OPS/'operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with BatchRegisters(lib,pin,BOOT,manifest['runtime_files']) as io:
  d=BatchDriver(io,0x778d2512,BOOT);assert d.status()==expected;stopped=d.stop()
  assert stopped['flags']==0 and stopped['lease_left_ms']==0 and stopped['width_us']==1420
 with (R/'attended-fixed-reference-before-visible-r2.json').open('xb') as out:out.write(original)
 now=time.monotonic();ref.update(authorization_id='attended-visible-r2-'+str(time.monotonic_ns()),
  authorization_recorded_mono_s=now,expires_mono_s=now+600,stopped_readback=stopped,
  source='CONTINUE_ALREADY_REQUESTED_VISIBLE_TEST_AFTER_TIMER_REPAIR',
  retry_basis='Previous attempt issued only 1420 holds and stopped; same requested 15us test and setup, current fresh face, no new user confirmation claimed',
  prior_failed_trial=str(trial),prior_failed_trial_sha256=hashlib.sha256(trial.read_bytes()).hexdigest(),current_fresh_face=face)
 tmp=R/'attended-fixed-reference.visible-r2';tmp.write_text(json.dumps(ref,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
 s=json.loads((R/'state.json').read_text());s.update(phase='ATTENDED_VISIBLE_RETRY_PREPARED_OUTPUT_STOPPED',current_last_command_us=1420,
  current_stopped_readback=stopped,physical_reference_receipt=str(path),automatic_following=False)
 (R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'status':'VISIBLE_R2_CONTEXT_RECORDED_OUTPUT_OFF','readback':stopped,
 'receipt_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'fresh_face':face,'ARM_sent':False,'COMMIT_sent':False}))
