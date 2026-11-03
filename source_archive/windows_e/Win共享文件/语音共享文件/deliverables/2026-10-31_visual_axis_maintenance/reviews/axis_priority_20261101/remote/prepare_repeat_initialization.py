"""Prepare only the user-requested identical repeat; no stage rollback or ARM."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='PHYSICAL_ANOMALY_ABORTED_OUTPUT_CLOSED'
assert digest(ROOT/'bench_finite_step_deadline_fix.py')=='f23952abb189e2e826db7f78ff81296a81a4b57c17684258499227d215dc6dc4'
sys.path.insert(0,str(RELEASE/'driver'))
from vsrv_driver import VSRVDriver
from vsrv_transport import NativeRegisters
manifest=document(RELEASE/'candidate-manifest.json')
with NativeRegisters(RELEASE/'driver/libvsrv.so',manifest['payload_files']['libvsrv.so'],BOOT,manifest['runtime_files']) as io:
 rb=VSRVDriver(io,0x10282601,BOOT).status()
assert rb['flags']==0 and rb['lease_left_ms']==0 and rb['active'] is False and rb['armed'] is False
output=ROOT/'initialization-repeat-observed.json';assert not output.exists()
atomic(ROOT/'initialization-user-correction.json',dict(user_quote='刚刚没有注意，再一次',
 previous_feedback_status='NOT_OBSERVED_NOT_CONFIRMED_ANOMALY',repeat_user_requested=True,repeat_count=1,
 original_initialization_sha256=j['initialization_sha256'],only_identical_2second_protocol=True))
j.update(phase='USER_REQUESTED_INITIALIZATION_REPEAT_READY',physical_anomaly_not_confirmed=True,
 prior_physical_feedback='NOT_OBSERVED',repeat_user_requested=True,current_stopped_readback=rb);save(j)
print(json.dumps(dict(status='REPEAT_READY',reference_protocol_sha256='f23952abb189e2e826db7f78ff81296a81a4b57c17684258499227d215dc6dc4',
 sequence_us=[1500,1505],duration_s=2,output=str(output),stopped=rb,ARM_sent=False,COMMIT_sent=False)))
