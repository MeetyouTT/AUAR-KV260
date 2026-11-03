"""One existing STOP-only check after adverse physical feedback; no ARM or reference."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='INITIALIZED_AWAITING_HUMAN'
output=ROOT/'abort-id-stop.json';assert not output.exists()
args=['/usr/bin/python3','-B',str(RELEASE/'bench_identity_stop.py'),'--execute','--confirmation','ID_STOP_ONLY',
 '--manifest',str(RELEASE/'candidate-manifest.json'),'--manifest-sha256',MANIFEST_SHA,
 '--context',str(ROOT/'wide-context.json'),'--output',str(output)]
p=subprocess.run(args,capture_output=True,text=True,timeout=10)
receipt=document(output);assert p.returncode==0 and receipt['identity_stop_passed'] is True
assert receipt['ARM_sent'] is False and receipt['COMMIT_sent'] is False
after=receipt['after_stop'];assert after['flags']==0 and after['lease_left_ms']==0 and after['active'] is False and after['armed'] is False
owners=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:argv=(proc/'cmdline').read_bytes().split(b'\0')
 except OSError:continue
 if any(arg.endswith((b'/run_face_motion.py',b'/bench_finite_step_deadline_fix.py',b'/bench_observed_80us_6s.py')) for arg in argv if arg):
  owners.append(dict(pid=int(proc.name),command_sha256=digest(proc/'cmdline')))
assert not owners
j.update(phase='PHYSICAL_ANOMALY_ABORTED_OUTPUT_CLOSED',current_stopped_readback=after,
 user_feedback='抖动、卡住或碰到限位',no_further_motion_authorized_by_this_test=True,
 direction_roundtrip_executed=False,face_follow_executed=False,abort_stop_receipt_sha256=digest(output));save(j)
print(json.dumps(dict(status=j['phase'],before=receipt.get('before'),after_stop=after,remaining_motion_owners=owners,
 camera_pid=int(systemd()['MainPID']),saved_listening_enabled=False,GUI_unavailable=True,
 ARM_sent=False,COMMIT_sent=False,REFERENCE_sent=False,physical_motion_test_passed=False,
 next_action='Read-only diagnosis; no centering or further motion')))
