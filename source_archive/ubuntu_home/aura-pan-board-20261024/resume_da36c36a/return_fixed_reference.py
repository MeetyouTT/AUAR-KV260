import fcntl,hashlib,importlib.util,json,sys,time
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/fixed-motion-bench-v1');sys.path.insert(0,str(P))
from board_fixed_cli import preflight,R,OLD,BOOT,OPS
manifest,control=preflight('9a47a0319dc67644bf871497715da70171b39d329ec335b16b56079dc6850718')
refpath=R/'attended-fixed-reference.json';original=refpath.read_bytes();ref=json.loads(original)
assert time.monotonic()+5<ref['expires_mono_s'] and ref['user_present'] and ref['reference_us']==1420
failed=R/('fixed-trajectory-'+ref['authorization_id']+'.json');prior=json.loads(failed.read_text())
assert prior['status']=='FAILED_NO_AUTOMATIC_RETRY' and prior['result']['stop_confirmed']
expected=prior['result']['stopped_readback'];assert expected['width_us']==1416 and expected['flags']==0 and expected['lease_left_ms']==0
bench=OLD/'bench_finite_step.py';assert hashlib.sha256(bench.read_bytes()).hexdigest()==json.loads((OLD/'payload.json').read_text())['files']['bench_finite_step.py']
sys.path.extend([str(OLD),str(OLD/'driver'),str(OPS/'pan-face-edge-v5/continuous-v10r15')])
spec=importlib.util.spec_from_file_location('existing_step',bench);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
from batch_transport import BatchRegisters
from batch_driver import BatchDriver
C=OPS/'pan-face-edge-v5/continuous-v10r15';lib=C/'libvsrv_batch.so';pin=next(x['sha256'] for x in control['files'] if x['destination']==str(lib))
report={'status':'STARTING','boot_id':BOOT,'purpose':'restore initial observed reference after aborted fixed trial','physical_motion_verified':False,'events':[]}
outpath=R/'fixed-return-1420.json'
with (OPS/'operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with outpath.open('x') as out:
  try:
   with BatchRegisters(lib,pin,BOOT,manifest['runtime_files']) as io:
    d=BatchDriver(io,0x778d2512,BOOT);assert d.status()==expected
    report['result']=module.run_finite(io,d,1416,1420,report['events'])
    assert report['result']['stopped']['flags']==0 and report['result']['stopped']['width_us']==1420
   report['status']='RETURN_TO_1420_STOPPED'
  except BaseException as e:report.update(status='FAILED_NO_AUTOMATIC_RETRY',error=type(e).__name__+': '+str(e));raise
  finally:json.dump(report,out,indent=2);out.write('\n')
 with (R/'attended-fixed-reference-before-return.json').open('xb') as out:out.write(original)
 ref.update(authorization_id='attended-fixed-retry-'+str(time.monotonic_ns()),stopped_readback=report['result']['stopped'],
  source='SAME_USER_OBSERVED_REFERENCE_AFTER_BOUNDED_RETURN',continuity_return_sha256=hashlib.sha256(outpath.read_bytes()).hexdigest())
 tmp=R/'attended-fixed-reference.updated';tmp.write_text(json.dumps(ref,ensure_ascii=False,indent=2)+'\n');tmp.replace(refpath)
print(json.dumps({'status':report['status'],'stopped':report['result']['stopped'],
 'receipt_sha256':hashlib.sha256(refpath.read_bytes()).hexdigest(),'report':str(outpath)}))
