# USE_SESSION_COMMON
"""Run one attended 20s follow session, then verify STOP before exporting numeric telemetry."""
import signal
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='BOUNDED_FACE_TEST_PREPARED'
root=Path(j['first_follow_controller'])
assert digest(root/'deployment-manifest.json')==j['first_follow_manifest_sha256']
manifest=document(root/'deployment-manifest.json')
assert all(digest(r['destination'])==r['sha256'] for r in manifest['files'])
assert digest(ROOT/'current-direction-human.json')==j['direction_evidence_sha256']
h=get_json(8790,'/health')
assert h['pid']==j['restored_camera_pid'] and h['mirror_horizontal'] is True
assert h['camera_error']==h['detector_error']==h['identity']['error']=='' and h['identity']['ready'] is True
assert h['dpu_schedule']['owner_fenced'] is False
output=ROOT/'first-face-follow.json';assert not output.exists()
args=['/usr/bin/python3','-B',str(root/'run_face_motion.py'),
 '--manifest',str(RELEASE/'candidate-manifest.json'),'--manifest-sha256',MANIFEST_SHA,
 '--context',str(ROOT/'wide-context.json'),'--app-root',str(BUSINESS/'runtime/aura'),
 '--output',str(output),'--direction-evidence',str(ROOT/'current-direction-human.json'),
 '--human-evidence',str(ROOT/'first-follow-human.json'),'--zone-settings',str(ROOT/'first-follow-zone.json'),
 '--confirmation','FACE_ZONE_CONTINUOUS','--duration','20']
j.update(phase='FIRST_FACE_TEST_START_INTENT');save(j)
time.sleep(5)
with (ROOT/'first-face-follow.stdout').open('xb') as out,(ROOT/'first-face-follow.stderr').open('xb') as err:
 child=subprocess.Popen(args,stdout=out,stderr=err)
 j.update(first_follow_child_pid=child.pid,phase='FIRST_FACE_TEST_RUNNING');save(j)
 try:child.wait(timeout=32)
 except subprocess.TimeoutExpired:
  child.send_signal(signal.SIGTERM)
  try:child.wait(timeout=4)
  except subprocess.TimeoutExpired:
   j.update(phase='FIRST_FACE_TEST_STOP_UNCONFIRMED');save(j)
   print(json.dumps(dict(status=j['phase'],child_pid=child.pid,another_owner_forbidden=True)));raise SystemExit(0)
report=document(output)
result=report.get('result',{});stopped=result.get('stopped') or result.get('readback') or {}
safe=stopped.get('flags')==0 and stopped.get('lease_left_ms')==0
j.update(phase='FIRST_FACE_TEST_STOPPED' if safe else 'FIRST_FACE_TEST_REQUIRES_STOP_CHECK',
 first_follow_report_sha256=digest(output),first_follow_returncode=child.returncode,
 current_stopped_readback=stopped if safe else j['current_stopped_readback']);save(j)
fields=('state','reason','commands_accepted','segments','minimum_pulse_us','maximum_pulse_us','pulse_us',
 'full_pulse_visual_stops','visual_center_completions','hardware_ramp_commits','target_lock','elapsed_s')
print(json.dumps(dict(status=j['phase'],controller_status=report.get('status'),returncode=child.returncode,
 error_present=bool(report.get('error')),error=report.get('error'),range_us=report.get('range_us'),
 result={key:result.get(key) for key in fields},stopped=stopped,input_summary=report.get('input_summary'),
 report_sha256=j['first_follow_report_sha256'],submission_timing=report.get('submission_timing'),
 observations=report.get('observation_trace',[]),telemetry=report.get('telemetry'))))
