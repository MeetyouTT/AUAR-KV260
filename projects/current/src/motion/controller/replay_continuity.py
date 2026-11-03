"""Paired synthetic replay against a frozen controller, without hardware."""
import argparse
from collections import Counter
from dataclasses import replace
import json
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controller-root',required=True)
    parser.add_argument('--smooth-center-stop',action='store_true')
    args=parser.parse_args();sys.path.insert(0,args.controller_root)
    from test_recenter import Scene,profile
    f=Scene(reference=1430);s=f.session
    if args.smooth_center_stop:
        s.config=replace(profile(),smooth_recenter_stop=True);s.controller=s.fresh()
    f.trigger()
    for _ in range(10):
        f.feed([.76]*5)
        p=f.packet(state='UNCONFIRMED')
        p['face_tracking']=dict(version=11,error='',reason='UNCONFIRMED_DETECTION')
        s.step(p);f.tick(2)
    events=Counter(e['reason'] for e in s.events)
    gaps=dict(arms=f.device.arms,stops=f.device.finishes,
              changed_targets=s.motion_updates,events=dict(events),
              brief_face_gaps=getattr(s,'brief_face_gaps',None),
              brief_face_recoveries=getattr(s,'brief_face_recoveries',None),
              fatal=s.fatal)
    s.close()
    f=Scene()
    if args.smooth_center_stop:
        f.session.config=replace(profile(),smooth_recenter_stop=True)
        f.session.controller=f.session.fresh()
    f.trigger();f.feed([.76]*3+[.65]*3+[.55]*3)
    before=list(f.session.pva);f.session.step(f.packet(.52));after=list(f.session.pva)
    center=dict(velocity_before_us_s=before[1],velocity_after_observation_us_s=after[1],
                velocity_discontinuity_us_s=abs(after[1]-before[1]),
                acceleration_discontinuity_us_s2=abs(after[2]-before[2]),
                state=f.session.state,reason=f.session.reason)
    f.session.close()
    print(json.dumps(dict(scope='synthetic; existing controller and host Ruckig, fake PWM',
                          motor_commands_sent=0,gap_replay=gaps,center_arrival=center)))


if __name__=='__main__':main()
