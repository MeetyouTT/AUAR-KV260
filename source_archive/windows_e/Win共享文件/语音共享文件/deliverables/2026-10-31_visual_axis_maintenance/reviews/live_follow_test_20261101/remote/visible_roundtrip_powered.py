# USE_SESSION_COMMON
"""One explicitly requested repeat after the user corrected the missing servo power."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='STOPPED_PHYSICAL_RESPONSE_NOT_CONFIRMED'
assert int(systemd()['MainPID'])==j['restored_camera_pid']
script=ROOT/'bench_observed_80us_6s.py'
assert digest(script)==j['visible_script_sha256']=='3538bef649574da5607aa54ffbfdee5e103fc4f1db1ebb468eade239500b876c'
expected=ROOT/'visible-expected-state-powered.json'
atomic(expected,dict(boot_id=BOOT,registers=j['current_stopped_readback']))
output=ROOT/'visible-80us-roundtrip-powered.json';assert not output.exists()
atomic(ROOT/'visible-powered-authorization.json',dict(boot=BOOT,
    user_correction='忘记上电了，重新哎',user_ready='已上电，现在可以看',
    previous_feedback_superseded_by_power_correction=True,
    sequence_us=[1505,1585,1505],duration_s=6,wait_before_s=5,automatic_repeat=False))
args=['/usr/bin/python3','-B',str(script),'--execute','--confirmation','OBSERVED_80US_RETURN_6S',
 '--manifest',str(RELEASE/'candidate-manifest.json'),'--manifest-sha256',MANIFEST_SHA,
 '--context',str(ROOT/'wide-context.json'),'--expected-state',str(expected),'--output',str(output)]
j.update(phase='VISIBLE_POWERED_REPEAT_INTENT',prior_feedback_corrected_as_servo_unpowered=True);save(j)
time.sleep(5)
p=subprocess.run(args,capture_output=True,text=True,timeout=12)
r=document(output)
assert p.returncode==0 and r['status']=='20US_RETURN_ACK_AND_STOP_PASS_OBSERVATION_PENDING'
assert r['result']['commanded_sequence_us']==[1505,1585,1505] and r['result']['excursion_us']==80
stopped=r['result']['stopped'];assert stopped['flags']==0 and stopped['lease_left_ms']==0 and stopped['width_us']==1505
j.update(phase='VISIBLE_POWERED_REPEAT_AWAITING_HUMAN',powered_repeat_receipt_sha256=digest(output),
    current_stopped_readback=stopped);save(j)
print(json.dumps(dict(status=j['phase'],sequence_us=[1505,1585,1505],commands=len(r['events']),
    actual_width_range_us=[min(e['width_us'] for e in r['events']),max(e['width_us'] for e in r['events'])],
    stopped_readback=stopped,receipt_sha256=digest(output),physical_observation='PENDING_USER')))
