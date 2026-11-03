"""Offline recenter episodes with synthetic face packets and fake hardware."""
import json
from test_recenter import Scene


def snapshot(scene):
    s=scene.session.status()
    return dict(time_s=round(scene.now,6),pulse_us=scene.device.pulse,arms=scene.device.arms,
        accepted=len(scene.device.commands),state=s['state'],reason=s['reason'],
        recenter_active=s['recenter_active'],recenter_state=s['recenter_state'],
        intent_pending=s['recenter_intent_pending'],flags=scene.device.status()['flags'])


def finish(scene,name,stages):
    before=snapshot(scene)
    final=scene.session.close()
    return dict(name=name,stages=stages,before_close=before,stopped=final['readback'],
        commands=list(scene.device.commands),events=final['events'],
        source_deadlines_preserved=all(c['deadline']<=c['stamp']+.25+1e-9 for c in scene.device.commands))


def run():
    cases=[]
    f=Scene();f.feed([.5,.6,.7,.4]*8)
    cases.append(finish(f,'inside_without_trigger',[]))
    f=Scene();f.trigger();stages=[snapshot(f)];f.feed([.76]*8);stages.append(snapshot(f))
    f.feed([.68]*3+[.60]*3+[.55]*3+[.52]*2);stages.append(snapshot(f));f.feed([.60]*8);stages.append(snapshot(f))
    cases.append(finish(f,'right_trigger_then_inside_region_then_center_hold',stages))
    f=Scene();f.feed([.30]*5+[.16]*12);stages=[snapshot(f)];f.feed([.26]*6);stages.append(snapshot(f))
    f.feed([.34]*3+[.42]*3+[.48]*2);stages.append(snapshot(f))
    cases.append(finish(f,'left_box_trigger_then_center',stages))
    f=Scene();f.trigger();f.feed([.76]*4);stages=[snapshot(f)];f.loss();stages.append(snapshot(f))
    f.tick(25);stages.append(snapshot(f));f.feed([.70]*12);stages.append(snapshot(f))
    cases.append(finish(f,'short_loss_stop_then_new_same_face_resume',stages))
    f=Scene();f.trigger();f.feed([.76]*3+[.65]*3+[.55]*3);stages=[snapshot(f)]
    f.feed([.45]*3+[.60]*5);stages.append(snapshot(f))
    cases.append(finish(f,'confirmed_crossing_completes_without_reverse_chase',stages))
    f=Scene(reference=1590);f.feed([.86]*90)
    cases.append(finish(f,'soft_limit_keeps_hardware_bounds',[snapshot(f)]))
    return dict(scope='SYNTHETIC_FACE_AND_FAKE_DEVICE_WITH_REAL_RUCKIG_MATH',board_accessed=False,
        physical_follow_verified=False,source_ttl_ms=250,anchor_ttl_ms=500,semantic_intent_hold_ms=2000,
        maximum_displacement_per_actual_source_us=4,hardware_range_us=[1400,1600],
        profile=dict(maximum_speed_us_s=30,maximum_acceleration_us_s2=120,maximum_jerk_us_s3=800,
                     gain_us_s=200,velocity_gain_us=24,target_center_ratio=.5,center_tolerance_ratio=.03),cases=cases)


if __name__=='__main__':print(json.dumps(run(),indent=2))
