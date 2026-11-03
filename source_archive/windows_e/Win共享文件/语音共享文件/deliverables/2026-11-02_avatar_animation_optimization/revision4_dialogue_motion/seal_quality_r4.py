from common import *
from PIL import Image
import numpy as np
def main():
    adapter=load(HERE/'validation/ADAPTER_TESTS.json');audit=load(HERE/'board_results/build/dialogue_state_actions.json')
    legacy=load(HERE/'board_results/build/legacy_policy_physics.json');build=load(HERE/'board_results/build/BUILD_RECEIPT.json')
    assert adapter['status']==audit['status']==legacy['status']=='PASS'
    assert adapter['candidate_adapter_sha256']==sha(HERE/'candidate/runtime/tools/native_yuki.py')
    for name,h in build['source_files'].items():assert sha(HERE/'candidate/native'/name)==h
    assert len(audit['state_pose_cases'])==28 and len(audit['reactions'])==4
    old=load(HERE/'validation/PERFORMANCE_R3.json');new=load(HERE/'validation/PERFORMANCE_R4.json')
    assert old['actual_completed_fps']>15.5 and new['actual_completed_fps']>15.5 and new['complete_frame_ms']['p95']<62.5
    preview=load(HERE/'board_results/previews/after_R4/report.json');final=preview['records'][-1]
    assert final['motion_gestures_started']==final['motion_gestures_completed']==4
    assert max(abs(row['motion_values']['aura_arm_left']) for row in preview['records'])<=4.00001
    visual=load(HERE/'validation/VISUAL_REVIEW.json');assert visual['render_capture_reviewed'] is True
    before=np.asarray(Image.open(HERE/'board_results/previews/before_R3/0000.png'))
    after=np.asarray(Image.open(HERE/'board_results/previews/after_R4/0000.png'))
    first_difference=int(np.any(before!=after,axis=-1).sum())
    assert first_difference==0
    assert sha(HERE/'baseline/native/secondary_motion.hpp')==sha(HERE/'candidate/native/secondary_motion.hpp')
    quality=dict(schema='aura-dialogue-state-motion-R4-quality-1',release_gate_passed=True,human_screen_acceptance=False,
       original_audio_eye_owner_policy_passed=True,adapter_tests=adapter['tests'],native_state_pose_cases=28,
       native_dialogue_frames=audit['frames'],lower_arm_absmax_deg=audit['lower_arm_absmax_deg'],
       lower_arm_peak_speed_deg_s=audit['lower_arm_peak_speed_deg_s'],new_reactions=len(audit['reactions']),
       first_frame_differing_pixels=first_difference,shoulder_binding_and_R3_legacy_source_unchanged=True,
       render_capture_review=visual,performance=dict(R3_fps=old['actual_completed_fps'],R4_fps=new['actual_completed_fps'],
       R3_p95_complete_ms=old['complete_frame_ms']['p95'],R4_p95_complete_ms=new['complete_frame_ms']['p95'],
       seconds_each=old['timeline_seconds'],readback_in_timed_loop=False,speedup_claimed=False),
       audio_devices_opened=False,model_service_calls=0,camera_restarts=0,axis_commands=0)
    save(HERE/'release/QUALITY_GATE.json',quality);save(HERE/'validation/QUALITY_GATE.json',quality);print(json.dumps(quality))
if __name__=='__main__':main()
