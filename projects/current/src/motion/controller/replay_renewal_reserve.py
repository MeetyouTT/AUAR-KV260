"""A new image precedes a delayed tick while the previous lease has 70ms."""
import argparse,json,sys

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--controller-root',required=True)
a=p.parse_args();sys.path.insert(0,a.controller_root)
from test_recenter import Scene
f=Scene();f.trigger();s=f.session;f.device.deadline=f.now+.070
before=len(f.device.commands);arms=f.device.arms
packet=f.packet(.76);s.step(packet);renewed=len(f.device.commands)>before
f.now+=.080;s.tick()
result=dict(scope='synthetic; fake PWM; no camera or MMIO',old_lease_remaining_ms=70,
 actual_control_delay_ms=80,new_face_age_at_arrival_ms=60,
 renewed_before_delay=renewed,active_after_delay=s.active,
 reason=s.reason,flags=f.device.status()['flags'],new_arms=f.device.arms-arms,
 original_source_deadline_respected=all(c['deadline']<=c['stamp']+c['freshness_s'] for c in f.device.commands),
 motor_commands_sent=0)
s.close();print(json.dumps(result))
