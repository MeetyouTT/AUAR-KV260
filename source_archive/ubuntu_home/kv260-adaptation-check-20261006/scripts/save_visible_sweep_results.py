"""Verify exported board evidence and refresh host status without board access."""
import base64,gzip,hashlib,json,datetime,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1];ev=root/'evidence'
def read(p):return json.loads(p.read_text())
def write(p,data):p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def export(name):
 p=ev/name;s=read(p/'status.json');assert s['rc']==0 and s['console_echo_restored']
 raw=(p/'result.txt').read_bytes();assert hashlib.sha256(raw).hexdigest()==s['output_sha256']
 d=json.loads(raw);data=gzip.decompress(base64.b64decode(d['gzip_base64']))
 assert len(data)==d['bytes'] and hashlib.sha256(data).hexdigest()==d['sha256']
 t=json.loads(data);write(p/'trace.json',t);return p,t
p,t=export('20261009T034221.835799Z-visible_sweep_trace_export')
r=t['result.json'];events=t['events.json'];assert r['passed'] and len(events)==r['commands']==616
assert t['error.json'] is None
holds={}
for i,e in enumerate(events,1):
 s=e['readback'];assert s['ack_seq']==i and s['target_us']==e['target_us']
 assert s['flags']==15 and s['lease_left_ms']>0 and s['reason']==0
 assert s['session']==r['final_stop']['session'] and s['epoch']==r['final_stop']['epoch']
 assert s['reference_us']==1500 and 1400<=s['width_us']<=1600
 assert r['schedule'][e['stage']][0]==e['target_us']
 if e['stage_elapsed_s']>.8:
  assert s['width_us']==e['target_us'];holds.setdefault(e['stage'],[]).append(e['stage_elapsed_s'])
assert set(holds)==set(range(10))
for stage in (1,3,6,8):assert max(holds[stage])-min(holds[stage])>3
assert t['stop.json']==r['final_stop'] and r['final_stop']['flags']==0 and r['final_stop']['lease_left_ms']==0
write(p/'HOST_TRACE_VERIFICATION.json',{'passed':True,'commands':616,'all_ten_stages_settled':True,'each_endpoint_stable_over_3s':True,'stop_verified':True})
repeat_p,repeat=export('20261009T034354.880938Z-powered_repeat_trace_export')
rr=repeat['result.json'];commands=[e for e in repeat['events.json'] if e['kind']=='COMMAND']
assert len(commands)==rr['commands']==185 and rr['stop_reason']=='FACE_QUALITY'
for i,e in enumerate(commands,1):
 s=e['accepted'];assert e['seq']==s['ack_seq']==i and s['flags']==15 and s['reason']==0
 assert s['target_us']==e['target_us'] and e['source_age_at_ack_ms']<250
 assert s['session']==rr['final_stop']['session'] and s['epoch']==rr['final_stop']['epoch']
 if i>1:assert e['frame_id']>commands[i-2]['frame_id']
box=rr['last_event']['observation']['snapshot']['tracks'][0]['box'];assert box[0]+box[2]==640
assert repeat['stop.json']==rr['final_stop'] and rr['final_stop']['flags']==0
write(repeat_p/'HOST_TRACE_VERIFICATION.json',{'passed':True,'commands':185,'right_edge_px':640,'stop_reason':'FACE_QUALITY','stop_verified':True})
final_p=ev/'20261009T034207.062919Z-newboot_vsrv_final';final=read(final_p/'result.txt');assert final['passed'] and final['stop_status']==r['final_stop']
final_execution=read(final_p/'status.json');assert final_execution['rc']==0 and final_execution['console_echo_restored']
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
project=Path('/home/ghmd/kv260-visual-servo-20261007');backup=p/'previous-host-state';backup.mkdir(exist_ok=True)
follow=read(ev/'20261009T033252.676707Z-quality_visual_direction_start'/'result.txt')
assert follow['continuous_control_passed'] and follow['duration_s']>=30 and len(follow['directions_commanded'])==3
assert read(ev/'20261009T033432.902440Z-powered_follow_trace_export'/'HOST_TRACE_VERIFICATION.json')['passed']
for name in ('CURRENT_CONTINUITY_TEST.json','CURRENT_FOLLOW_RETEST.json','LATEST_DIRECTION_RETEST.json'):
 q=project/name;shutil.copy2(q,backup/name);d=read(q)
 d.update(recorded_utc=now,bidirectional_30s_command_test_passed=True,bidirectional_command_coverage_passed=True,
  bidirectional_30s_following_passed=False,continuous_following_passed=False,physical_axis_following_confirmed=False,
  mechanical_motion_observed=True,mechanical_feedback='USER_REPORTED_MOTION_TOO_SLOW_AND_SMALL_BEFORE_ENLARGED_TEST',
  speed_tuning_performed=True,visual_controller_speed_changed=False,physical_reference_valid=False,
  fixed_visible_sweep=r,fixed_sweep_trace_verification=str(p/'HOST_TRACE_VERIFICATION.json'),
  powered_visual_trace_verification=str(ev/'20261009T033432.902440Z-powered_follow_trace_export'/'HOST_TRACE_VERIFICATION.json'),
  repeat_trace_verification=str(repeat_p/'HOST_TRACE_VERIFICATION.json'),
  final_verification={'execution':final_execution,'result':final},previous_host_state_directory=str(backup))
 for x in (follow,rr):
  if not any(y['evidence']==x['evidence'] for y in d['tests']):d['tests'].append(x)
 write(q,d)
write(project/'CURRENT_VISIBLE_SWEEP.json',{'recorded_utc':now,'result':r,'execution':read(ev/'20261009T034115.600700Z-visible_servo_sweep_start'/'status.json'),
 'trace_verification':str(p/'HOST_TRACE_VERIFICATION.json'),'final_verification':{'execution':final_execution,'result':final},
 'report':'/home/ghmd/AMD_Smart/logs/daily/2026-10-08-SERVO-VISIBLE-TEST.md'})
q=Path('/home/ghmd/kv260-realtime-vision-20261007/CURRENT_RUNTIME.json');shutil.copy2(q,backup/q.name);d=read(q)
d.update(updated_utc=now,after=final['after'],final_stop=final['stop_status'],physical_actuation_enabled=False,
 physical_reference_valid=False,physical_axis_following_confirmed=False,mechanical_motion_observed=True,
 bidirectional_30s_command_test_passed=True,continuous_following_passed=False,
 latest_fixed_visible_sweep=str(project/'CURRENT_VISIBLE_SWEEP.json'),final_verification={'execution':final_execution,'result':final})
write(q,d)
print(json.dumps({'passed':True,'sweep_commands_verified':616,'repeat_commands_verified':185,'final_stop_verified':True,'host_state_backup':str(backup)}))
