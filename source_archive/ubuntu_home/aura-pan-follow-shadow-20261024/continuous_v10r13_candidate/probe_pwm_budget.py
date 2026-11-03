"""Synthetic software replay with a 20ms output latch and independent source clock."""
import hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
HERE=Path(__file__).parent
from continuous_session import ContinuousSession
from continuous_face_control import EdgeConfig
from trajectory import Trajectory
from common.motion_observation import PROTOCOL
from pwm_fake_device import PWMDevice


def replay(period_ms=200,phase_ms=0,duration_s=8):
    now=[1.+phase_ms/1000.];device=PWMDevice(lambda:now[0]);fid=0
    p=HERE.parent/'ps_trajectory_v1/libaura_trajectory_compat_host.so'
    trajectory=Trajectory(p,hashlib.sha256(p.read_bytes()).hexdigest())
    cfg=EdgeConfig(left_ratio=.1,confirm_frames=2,maximum_correction_us=None,
        maximum_speed_us_s=20.,minimum_edge_speed_us_s=6.,velocity_gain_us=12.,prearm_confirmed_face=True)
    session=ContinuousSession(device,'boot',cfg,lambda p:SimpleNamespace(reference_us=p),
        trajectory=trajectory,clock=lambda:now[0],allow_fixture=True,polarity=1)
    start=now[0];next_source=start;end=start+duration_s;states=Counter();samples=[]
    while now[0]<end:
        if now[0]>=next_source-1e-8:
            fid+=1;stamp=int(now[0]*1000);box=[576.,100.,64.,80.]
            packet=dict(protocol_version=PROTOCOL,source_kind='fixture',target_kind='face',board_boot_id='boot',
                service_epoch='service',camera_epoch='camera',state='READY',source_frame_id=fid,source_mono_ms=stamp,
                deadline_mono_ms=stamp+250,frame_width=640,frame_height=480,mirror_horizontal=True,
                target=dict(track_id=1,track_generation=1,box=box,score=.95))
            session.step(packet);next_source+=period_ms/1000.
        now[0]+=.02;v=session.tick();states[v['reason']]+=1
        samples.append(dict(now=now[0],pva=list(session.pva),reason=v['reason'],width=device.pulse,target=device.accepted_target_us))
    session.close()
    return dict(period_ms=period_ms,phase_ms=phase_ms,arms=device.arms,finishes=device.finishes,
        commands=len(device.commands),pulse_range=[min(p['pulse'] for p in device.pulses),max(p['pulse'] for p in device.pulses)],
        reason_ticks=dict(states),fatal=session.fatal,samples=samples)


if __name__=='__main__':
    outputs=[replay(period_ms=p,phase_ms=phase) for p in (100,160,180,200,220) for phase in (0,7,13)]
    print(json.dumps([{k:v for k,v in r.items() if k!='samples'} for r in outputs],indent=2))
