"""Final STOP-only receipt for host migration; never run a queued motion test."""
current_guard();wide_active();verify_wide_files()
j=state()
context=document(ROOT/'wide-context.json')
assert context['boot_id']==BOOT and context['fdt_sha256']==digest('/sys/firmware/fdt')
assert context['firmware_name']==firmware()
assert digest(RELEASE/'bench_identity_stop.py')=='c9e91f74336c1e73d7c60408739abc8537b80066eb666a1a79e32b81d7d267aa'

def motion_owners():
 values=[]
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:argv=(proc/'cmdline').read_bytes().split(b'\0')
  except OSError:continue
  if any(arg.endswith((b'/run_face_motion.py',b'/bench_finite_step_deadline_fix.py',b'/bench_observed_80us_6s.py')) for arg in argv if arg):
   values.append(dict(pid=int(proc.name),command_sha256=digest(proc/'cmdline')))
 return values

owners_before=motion_owners();assert not owners_before
output=ROOT/('migration-id-stop-'+str(time.time_ns())+'.json')
args=['/usr/bin/python3','-B',str(RELEASE/'bench_identity_stop.py'),'--execute','--confirmation','ID_STOP_ONLY',
 '--manifest',str(RELEASE/'candidate-manifest.json'),'--manifest-sha256',MANIFEST_SHA,
 '--context',str(ROOT/'wide-context.json'),'--output',str(output)]
p=subprocess.run(args,capture_output=True,text=True,timeout=10)
assert p.returncode==0
receipt=document(output)
assert receipt['identity_stop_passed'] is True
assert receipt['ARM_sent'] is False and receipt['COMMIT_sent'] is False
after=receipt['after_stop']
assert after['flags']==0 and after['lease_left_ms']==0 and after['active'] is False and after['armed'] is False
owners_after=motion_owners();assert not owners_after
camera=systemd();health=get_json(8790,'/health')
camera_pid=int(camera['MainPID']);assert camera_pid==health['pid']
stat_text=Path('/proc/'+str(camera_pid)+'/stat').read_text()
camera_birth=int(stat_text.rsplit(')',1)[1].split()[19])
gui_raw=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState,SubState,Job'],capture_output=True,text=True,timeout=4)
gui=dict(x.split('=',1) for x in gui_raw.stdout.splitlines() if '=' in x)
repeat_path=ROOT/'initialization-repeat-observed.json'
result=dict(status='FROZEN_FOR_5090_MIGRATION_OUTPUT_CLOSED',utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
 boot_id=BOOT,previous_phase=j['phase'],firmware=firmware(),fdt_sha256=context['fdt_sha256'],
 vart_configuration=Path('/etc/vart.conf').read_text().strip(),startup_sha256=digest(BUSINESS/'startup/config.json'),
 stop_receipt_path=str(output),stop_receipt_sha256=digest(output),before_stop=receipt.get('before'),after_stop=after,
 ARM_sent=False,COMMIT_sent=False,REFERENCE_sent=False,remaining_motion_owners=owners_after,
 camera=dict(pid=camera_pid,birth_ticks=camera_birth,command_sha256=digest('/proc/'+str(camera_pid)+'/cmdline'),
  active_state=camera.get('ActiveState'),capture_frames=health.get('capture_frames'),detected_frames=health.get('detected_frames'),
  camera_error=health.get('camera_error'),detector_error=health.get('detector_error'),
  identity_ready=health.get('identity',{}).get('ready'),identity_error=health.get('identity',{}).get('error')),
 gui=gui,persisted_listening_enabled=False,
 repeat_executed=repeat_path.exists(),repeat_sha256=digest(repeat_path) if repeat_path.exists() else None,
 direction_roundtrip_executed=False,face_follow_executed=False,physical_observation_status='NOT_OBSERVED',
 mechanical_zero_calibrated=False,persistent_wide_boot_configuration_verified=False,
 further_motion_authorized=False,device_commands_frozen_after_this_receipt=True)
j.update(phase=result['status'],current_stopped_readback=after,migration_freeze=result);save(j)
atomic(ROOT/'migration-freeze.json',result)
print(json.dumps(result,allow_nan=False))
