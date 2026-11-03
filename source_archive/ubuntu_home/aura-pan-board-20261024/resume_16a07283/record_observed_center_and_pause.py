"""Record user observations only. No hardware library or motion command."""
import hashlib,json,os,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot=='16a07283-9e14-45e6-816d-3bda4cf333a7'
s=json.loads((R/'state.json').read_text());assert s['phase']=='CURRENT_BOOT_RELATIVE_20US_STOPPED_OBSERVATION_PENDING'
trial=R/'relative-20us-no-init.json';digest=hashlib.sha256(trial.read_bytes()).hexdigest();assert digest==s['trial_sha256']
t=json.loads(trial.read_text());r=t['result']['stopped'];assert r['flags']==0 and r['lease_left_ms']==0 and r['width_us']==1445
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as stream:u=json.load(stream)
assert not u['manual_pan']['automatic_following'] and u['manual_pan']['state']=='FAULT'
human=dict(status='HUMAN_OBSERVED_20US_RETURN_CONFIRMED',boot_id=boot,trial_sha256=digest,
 movement_and_return_stop_observed=True,feedback_verbatim='看到了小幅度来回，已经停住',
 center_reference_us=1420,center_reference_source='USER_REPORTED',current_last_command_us=1445,
 center_command_applied=False,direction_verified=False,external_waveform_verified=False)
with (R/'relative-20us-human-observation.json').open('x') as f:json.dump(human,f,ensure_ascii=False,indent=2);f.write('\n')
center=dict(board_boot_id=boot,center_reference_us=1420,source='USER_REPORTED',
 operator_pause_requested=True,last_command_us=1445,center_command_applied=False,
 mechanical_angle_measured=False,external_waveform_verified=False)
with (R/'center-reference.json').open('x') as f:json.dump(center,f,indent=2);f.write('\n')
s.update(phase='USER_PAUSED_OUTPUT_STOPPED_20US_OBSERVED_CENTER_1420',user_paused_motion=True,
 physical_response_accepted=True,physical_response_scope='one relative 20us return only',
 physical_motion_tests_halted=True,center_reference_us=1420,center_reference_source='USER_REPORTED',
 current_last_command_us=1445,center_command_applied=False,automatic_following=False,
 human_feedback_correction='100deg was return to center, not the relative 20us increment',
 physical_follow_validated=False)
tmp=R/'state.record';tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,R/'state.json')
print(json.dumps({'status':s['phase'],'human_observation':human,'center':center,
 'manual_state':u['manual_pan']['state'],'MMIO_opened':False,'motor_commands_sent':0,'automatic_following':False}))
