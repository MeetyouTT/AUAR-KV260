current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='USER_REQUESTED_INITIALIZATION_REPEAT_READY'
script=ROOT/'bench_finite_step_deadline_fix.py';assert digest(script)=='f23952abb189e2e826db7f78ff81296a81a4b57c17684258499227d215dc6dc4'
output=ROOT/'initialization-repeat-observed.json';assert not output.exists()
args=['/usr/bin/python3','-B',str(script),'--execute','--confirmation','OBSERVED_FINITE_2S',
 '--initial-us','1500','--target-us','1505','--manifest',str(RELEASE/'candidate-manifest.json'),
 '--manifest-sha256',MANIFEST_SHA,'--context',str(ROOT/'wide-context.json'),'--output',str(output)]
j.update(phase='USER_REQUESTED_INITIALIZATION_REPEAT_RUNNING');save(j)
p=subprocess.run(args,env=dict(os.environ,PYTHONPATH=str(RELEASE)),capture_output=True,text=True,timeout=10)
r=document(output);stopped=(r.get('result') or {}).get('stopped');ok=p.returncode==0 and r.get('status')=='FINITE_ACK_AND_STOP_PASS_OBSERVATION_PENDING'
if ok:assert stopped['flags']==0 and stopped['lease_left_ms']==0 and stopped['width_us']==1505
j.update(phase='REPEAT_INITIALIZATION_STOPPED_AWAITING_HUMAN' if ok else 'REPEAT_INITIALIZATION_FAILED_NO_RETRY',
 current_stopped_readback=stopped,repeat_initialization_sha256=digest(output));save(j)
print(json.dumps(dict(status=j['phase'],repeat_user_requested=True,repeat_count=1,returncode=p.returncode,
 reported_status=r.get('status'),error=r.get('error'),sequence_us=[1500,1505],duration_s=2,stopped=stopped,
 physical_observation_pending=True,mechanical_zero_calibrated=False)))
