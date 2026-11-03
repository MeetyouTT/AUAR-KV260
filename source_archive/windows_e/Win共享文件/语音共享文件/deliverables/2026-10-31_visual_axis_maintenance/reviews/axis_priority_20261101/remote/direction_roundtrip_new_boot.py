"""Original finite 80us round trip after user confirms initialization settled."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='INITIALIZED_AWAITING_HUMAN'
assert int(systemd()['MainPID'])==j['restored_camera_pid']
script=ROOT/'bench_observed_80us_6s.py'
assert digest(script)=='3538bef649574da5607aa54ffbfdee5e103fc4f1db1ebb468eade239500b876c'
expected=ROOT/'roundtrip-expected.json';atomic(expected,dict(boot_id=BOOT,registers=j['current_stopped_readback']))
output=ROOT/'direction-roundtrip.json';assert not output.exists()
args=['/usr/bin/python3','-B',str(script),'--execute','--confirmation','OBSERVED_80US_RETURN_6S',
 '--manifest',str(RELEASE/'candidate-manifest.json'),'--manifest-sha256',MANIFEST_SHA,
 '--context',str(ROOT/'wide-context.json'),'--expected-state',str(expected),'--output',str(output)]
j.update(phase='DIRECTION_ROUNDTRIP_INTENT',initializer_physical_settled_user_confirmed=True);save(j)
time.sleep(5)
p=subprocess.run(args,capture_output=True,text=True,timeout=12)
r=document(output);stopped=(r.get('result') or {}).get('stopped')
ok=p.returncode==0 and r.get('status')=='20US_RETURN_ACK_AND_STOP_PASS_OBSERVATION_PENDING'
if ok:assert stopped['flags']==0 and stopped['lease_left_ms']==0 and stopped['width_us']==1505
j.update(phase='DIRECTION_ROUNDTRIP_AWAITING_HUMAN' if ok else 'DIRECTION_ROUNDTRIP_FAILED_NO_RETRY',
 current_stopped_readback=stopped,direction_roundtrip_sha256=digest(output));save(j)
print(json.dumps(dict(status=j['phase'],returncode=p.returncode,reported_status=r.get('status'),error=r.get('error'),
 sequence_us=[1505,1585,1505],duration_s=6,stopped=stopped,physical_direction_pending=True,
 physical_motion_samples=len(r.get('events',[])))))
