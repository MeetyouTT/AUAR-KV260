"""Bind the user's observed direction and swap button mapping without movement."""
import hashlib,json,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/463c9307');o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get():
 with o.open(base+'/api/state',timeout=3) as r:return json.load(r)
u=get();m=u['manual_pan'];r=m['readback'];hist=m.get('history',[])[-2:]
assert m['state']=='READY' and m['pulse_us']==1425 and r['flags']==0 and r['lease_left_ms']==0
assert len(hist)==2 and [(x['direction'],x['initial_us'],x['target_us'],x['final_us']) for x in hist]==[('right',1425,1445,1445),('left',1445,1425,1425)]
assert all(x['failure'] is None and x['completion']=='FULL_PULSE_FINISH' for x in hist)
proof={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'status':'HUMAN_DIRECTION_CONFIRMED',
 'feedback_verbatim':'实际向左，向右','button_sequence':['right','left'],'pulse_sequence_us':[1425,1445,1425],
 'increase_pulse_physical_direction':'left','decrease_pulse_physical_direction':'right',
 'left_button_pulse_sign':1,'axis_camera_mirrored_control_polarity':1,'camera_mounting_source':'user previously reported camera rotates with axis',
 'mechanical_zero_verified':False,'command_history':hist,'new_physical_commands_sent':0}
p=R/'direction-calibration.json'
assert not p.exists();p.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
if m['left_sign']==-1:
 req=urllib.request.Request(base+'/api/command',data=json.dumps({'type':'pan_reverse'}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(req,timeout=3) as response:assert json.load(response).get('ok')
time.sleep(.3);after=get()['manual_pan'];a=after['readback']
assert after['left_sign']==1 and after['state']=='READY' and all(a[k]==r[k] for k in ('flags','lease_left_ms','epoch','ack_seq','width_us'))
s=json.loads((R/'state.json').read_text());s.update(direction_verified=True,direction_evidence_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),button_left_sign=1);(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'direction_verified':True,'left_button_pulse_sign':1,'visual_control_polarity_for_mirrored_axis_camera':1,'flags':a['flags'],'lease_ms':a['lease_left_ms'],'movement_commands_sent':0}))
