"""Compare requested-velocity changes under synthetic face-position jitter."""
import argparse,json,sys
from dataclasses import replace
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--controller-root',required=True);p.add_argument('--single-pass',action='store_true')
a=p.parse_args();sys.path.insert(0,a.controller_root)
from test_recenter import Scene,profile
f=Scene(reference=1430);s=f.session
if a.single_pass:
 s.config=replace(profile(),single_pass_recenter=True,smooth_recenter_stop=True,maximum_speed_us_s=40.,velocity_gain_us=0.)
 s.controller=s.fresh()
f.trigger();f.feed([.69]*3)
speeds=[];phases=[]
for center in [.68,.70,.69,.705,.675,.695]*5:
 f.feed([center]);speeds.append(round(s.controller.requested_speed,4));phases.append(getattr(s.controller,'recenter_phase',None))
jitter=dict(requested_speed_changes=sum(a!=b for a,b in zip(speeds,speeds[1:])),requested_speed_total_variation_us_s=round(sum(abs(a-b) for a,b in zip(speeds,speeds[1:])),4),minimum_requested_speed_us_s=min(speeds),maximum_requested_speed_us_s=max(speeds))
f.feed([.64]*4+[.56]*4+[.52]*12)
result=dict(scope='synthetic face samples; actual controller/host Ruckig and fake PWM; not mechanical smoothness',mode='single_pass' if a.single_pass else 'per_image_feedback',jitter_window=jitter,completed=s.controller.recenter_completed,phase=getattr(s.controller,'recenter_phase',None),arms=f.device.arms,fatal=s.fatal,motor_commands_sent=0)
s.close();print(json.dumps(result))
