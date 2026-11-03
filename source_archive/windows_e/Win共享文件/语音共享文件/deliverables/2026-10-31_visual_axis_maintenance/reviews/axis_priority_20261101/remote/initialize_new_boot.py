"""Original previously tested two-second initialization; no automatic repeat."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='BOUNDED_ORIGINAL_STAGED_NO_MOTION'
script=ROOT/'bench_finite_step_deadline_fix.py'
assert digest(script)=='f23952abb189e2e826db7f78ff81296a81a4b57c17684258499227d215dc6dc4'
output=ROOT/'initialization.json';assert not output.exists()
args=['/usr/bin/python3','-B',str(script),'--execute','--confirmation','OBSERVED_FINITE_2S',
 '--initial-us','1500','--target-us','1505','--manifest',str(RELEASE/'candidate-manifest.json'),
 '--manifest-sha256',MANIFEST_SHA,'--context',str(ROOT/'wide-context.json'),'--output',str(output)]
j.update(phase='INITIALIZATION_INTENT',physical_initial_position_known=False);save(j)
time.sleep(5)
p=subprocess.run(args,env=dict(os.environ,PYTHONPATH=str(RELEASE)),capture_output=True,text=True,timeout=10)
r=document(output);stopped=(r.get('result') or {}).get('stopped')
ok=p.returncode==0 and r.get('status')=='FINITE_ACK_AND_STOP_PASS_OBSERVATION_PENDING'
if ok:assert stopped['flags']==0 and stopped['lease_left_ms']==0 and stopped['width_us']==1505
j.update(phase='INITIALIZED_AWAITING_HUMAN' if ok else 'INITIALIZATION_FAILED_NO_RETRY',current_stopped_readback=stopped,initialization_sha256=digest(output));save(j)
print(json.dumps(dict(status=j['phase'],returncode=p.returncode,reported_status=r.get('status'),error=r.get('error'),
 sequence_us=[1500,1505],duration_s=2,stopped=stopped,physical_observation_pending=True,mechanical_zero_calibrated=False)))
