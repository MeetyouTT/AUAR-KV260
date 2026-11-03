# USE_SESSION_COMMON
"""Explicit attended 2s initialization requested after the user reported uncertain continuity."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='WIDE_ID_STOP_CAMERA_PROGRESS_VERIFIED'
assert digest(ROOT/'bench_finite_step_wide.py')==j['initializer_sha256']=='97bbd20fca86704cf34549b663f09e9ede0e0a3a3608625f659fe987e829c1ca'
assert digest(ROOT/'wide-context.json')==j['context_sha256']
assert int(systemd()['MainPID'])==j['restored_camera_pid']
authorization=dict(boot_id=BOOT,user_mount_and_power_confirmed=True,
    user_reported_continuity='不确定，需重新建立位置参考',
    source='direct user answer in 01a195e4-58a7-72d3-b141-d5d373579f7f',
    action='existing explicit attended finite initialization',initial_us=1500,target_us=1505,duration_s=2,
    initialization_may_move_from_unknown_position=True,mechanical_angle_calibrated=False)
atomic(ROOT/'initialization-authorization.json',authorization)
output=ROOT/'finite-initialization.json';assert not output.exists()
env=dict(os.environ,PYTHONPATH=str(RELEASE))
args=['/usr/bin/python3','-B',str(ROOT/'bench_finite_step_wide.py'),'--execute',
    '--confirmation','OBSERVED_FINITE_2S','--initial-us','1500','--target-us','1505',
    '--manifest',str(RELEASE/'candidate-manifest.json'),'--manifest-sha256',MANIFEST_SHA,
    '--context',str(ROOT/'wide-context.json'),'--output',str(output)]
j['phase']='ATTENDED_INITIALIZATION_INTENT';save(j)
p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=10)
receipt=document(output)
if p.returncode!=0 or receipt.get('status')!='FINITE_ACK_AND_STOP_PASS_OBSERVATION_PENDING':
    j['phase']='INITIALIZATION_FAILED_NO_RETRY';j['initialization_receipt_sha256']=digest(output);save(j)
    print(json.dumps(dict(status=j['phase'],returncode=p.returncode,receipt=receipt)));raise SystemExit(0)
stopped=receipt['result']['stopped']
assert stopped['flags']==0 and stopped['lease_left_ms']==0 and stopped['width_us']==1505
j.update(phase='INITIALIZED_AWAITING_HUMAN_OBSERVATION',initialization_receipt_sha256=digest(output),
    current_stopped_readback=stopped);save(j)
print(json.dumps(dict(status=j['phase'],initial_us=1500,last_commanded_us=1505,events=len(receipt['events']),
    initialized_seconds=2,stopped_readback=stopped,receipt_sha256=digest(output),
    physical_observation='PENDING_USER',mechanical_angle_calibrated=False,automatic_following=False)))
