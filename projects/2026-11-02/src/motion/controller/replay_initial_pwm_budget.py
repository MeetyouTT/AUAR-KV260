"""Paired synthetic replay: accepted target versus actual 20ms latch outputs.

No physical angle, inertia, human-follow quality or hardware verification is
inferred from this model. Run --compare to compare frozen r12 with this r14.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent


def replay(candidate,anchor,library=None):
    sys.path.insert(0,str(candidate))
    from continuous_face_control import EdgeConfig
    from continuous_session import ContinuousSession
    from trajectory import Trajectory
    from common.motion_observation import PROTOCOL
    from pwm_fake_device import PWMDevice
    lib=library or HERE.parent/'ps_trajectory_v1/libaura_trajectory_compat_host.so'
    trajectory=Trajectory(lib,hashlib.sha256(lib.read_bytes()).hexdigest())
    now=[1.];device=PWMDevice(lambda:now[0]);fid=0
    config=EdgeConfig(left_ratio=.1,confirm_frames=2,maximum_correction_us=None,
        prearm_confirmed_face=True,maximum_speed_us_s=20.,minimum_edge_speed_us_s=6.,velocity_gain_us=12.)
    session=ContinuousSession(device,'boot',config,lambda p:SimpleNamespace(reference_us=p),
        trajectory=trajectory,clock=lambda:now[0],allow_fixture=True)
    for center in [.79]*3+[.808]*5:
        fid+=1;stamp=round(now[0]*1000)
        packet=dict(protocol_version=PROTOCOL,source_kind='fixture',target_kind='face',board_boot_id='boot',
            service_epoch='service',camera_epoch='camera',state='READY',source_frame_id=fid,
            source_mono_ms=stamp,deadline_mono_ms=stamp+250,face_detection_mono_ms=anchor,
            frame_width=640,frame_height=480,mirror_horizontal=True,
            target=dict(track_id=1,track_generation=1,box=[center*640-40,100.,80.,80.],score=.95))
        session.step(packet)
        for _ in range(4):now[0]+=.02;session.tick()
    first=device.commands[0] if device.commands else None
    result=dict(candidate=candidate.name,anchor_ms=anchor,commands=len(device.commands),
        first_lease_ms=round((first['deadline']-first['now'])*1000) if first else None,
        pulse_outputs=len(device.pulses),changed_width_outputs=sum(p['pulse']!=1469 for p in device.pulses),
        final_width_us=device.pulse,final_target_us=device.accepted_target_us,
        initial_pwm_budget_waits=getattr(session,'initial_pwm_budget_waits',0),
        fatal=session.fatal,events=list(session.events),physical_verified=False)
    session.close();return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate-root',type=Path,default=HERE);p.add_argument('--anchor',type=int,default=947)
    p.add_argument('--baseline-root',type=Path,default=HERE.parent/'continuous_v10r12_candidate')
    p.add_argument('--trajectory-library',type=Path)
    p.add_argument('--compare',action='store_true');args=p.parse_args()
    if not args.compare:
        print(json.dumps(replay(args.candidate_root,args.anchor,args.trajectory_library)));return
    pairs=[]
    for anchor in (947,952,960,1000):
        results=[]
        for candidate in (args.baseline_root,args.candidate_root):
            command=[sys.executable,'-B',str(Path(__file__).resolve()),
                '--candidate-root',str(candidate),'--anchor',str(anchor)]
            if args.trajectory_library:command+=['--trajectory-library',str(args.trajectory_library)]
            raw=subprocess.check_output(command,text=True)
            results.append(json.loads(raw))
        before,after=results
        if anchor<1000:
            assert before['commands']==1 and before['changed_width_outputs']==0
            assert after['commands']==0 and after['pulse_outputs']==0
        else:
            assert before['commands']==after['commands']==1
            assert before['changed_width_outputs']==after['changed_width_outputs']>0
        assert not before['fatal'] and not after['fatal']
        pairs.append(dict(anchor_ms=anchor,before=before,after=after))
    print(json.dumps(dict(scope='synthetic Ruckig plus 20ms PWM latch, no hardware',
        paired_scenarios=pairs,passed=True),indent=2))


if __name__=='__main__':main()
