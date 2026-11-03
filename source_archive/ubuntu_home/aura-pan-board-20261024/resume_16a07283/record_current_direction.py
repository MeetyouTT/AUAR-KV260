import hashlib,json,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1'
s=json.loads((R/'state.json').read_text());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert s['phase']=='DIRECTION_TRIAL_STOPPED_OBSERVATION_PENDING' and boot==s['boot']
trial=Path(s['direction_trial']);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(trial)==s['direction_trial_sha256']
t=json.loads(trial.read_text());assert t['result']['commanded_sequence_us']==[1445,1465,1445]
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as response:u=json.load(response)
m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']==t['result']['stopped']
p=R/'direction-calibration.json';assert not p.exists()
proof=dict(boot_id=boot,status='HUMAN_DIRECTION_CONFIRMED',feedback_verbatim='先向右、再向左返回，已停住',
 pulse_sequence_us=[1445,1465,1445],trial_sha256=sha(trial),increase_pulse_physical_direction='right',decrease_pulse_physical_direction='left',
 left_button_pulse_sign=-1,axis_camera_mirrored_control_polarity=-1,mechanical_zero_verified=False,
 camera_mounting_source='user previously confirmed camera rotates with axis',new_physical_commands_sent=0)
with p.open('x') as f:json.dump(proof,f,ensure_ascii=False,indent=2);f.write('\n')
s.update(phase='CURRENT_BOOT_DIRECTION_CONFIRMED_OUTPUT_STOPPED',direction_verified=True,direction_evidence_sha256=sha(p),button_left_sign=-1,
 axis_camera_mirrored_control_polarity=-1,automatic_following=False)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'direction':proof,'readback':m['readback'],'live_manual_left_sign':m['left_sign'],
 'follow_readback_source':(G/'runtime/aura/board/motion/follow_readback.py').read_text(),
 'manual_source_sha256':sha(G/'runtime/aura/board/motion/manual.py'),'motor_commands_sent':0}))
