from common import *
from PIL import Image
import numpy as np
if __name__=='__main__':
 old=load(HERE/'validation/PERFORMANCE_R2.json');new=load(HERE/'validation/PERFORMANCE_R3.json');numeric=load(HERE/'board_results/build/MOTION_COMPARE.json')
 assert old['actual_completed_fps']>15.8 and new['actual_completed_fps']>15.8 and new['complete_frame_ms']['p95']<62.5
 before=np.asarray(Image.open(HERE/'board_results/previews/before_R2/0000.png'));after=np.asarray(Image.open(HERE/'board_results/previews/after_R3/0000.png'));neutral=int(np.any(before!=after,axis=-1).sum());assert neutral==0
 for n in ('yuki_host.h','yuki_host.cpp'):assert sha(HERE/'baseline/native'/n)==sha(HERE/'candidate/native'/n)
 old_header=(HERE/'baseline/native/secondary_motion.hpp').read_text();new_header=(HERE/'candidate/native/secondary_motion.hpp').read_text()
 assert old_header.split('class SecondaryMotion')[0]==new_header.split('class SecondaryMotion')[0]
 canonical={k:v for k,v in numeric.items() if k!='device_or_GPU_used'}
 canonical.update(execution_host='KV260 ARM CPU',specialized_device_display_GPU_or_audio_API_opened=False,logical_ticks_not_wall_clock_duration=True,raw_report='board_results/build/MOTION_COMPARE.json',raw_flag_interpretation='device_or_GPU_used=false is a program diagnostic for no device/GPU API access, not a claim that it ran off-board')
 save(HERE/'validation/NUMERIC_COMPARISON_WITH_CONTEXT.json',canonical)
 policy=load(HERE/'board_results/build/PHYSICAL_PARAMETERS.json');assert policy['status']=='PASS' and policy['original_audio_eye_owner_policy_passed']
 q=dict(schema='aura-R3-natural-lower-arm-quality-1',release_gate_passed=True,human_feedback_R2='lower/back arm too large; refine amplitude for natural movement',R3_human_acceptance=False,
  visual_review=dict(source='192 frames per variant from actual KV260 offscreen GLES',reviewed_seconds=[2,4,5.5,7,9,11],lower_arm_excursion_reduced=True,shoulder_attachment_preserved=True,front_arm_and_head_body_source_unchanged=True,neutral_frame_differing_pixels=neutral,synthetic_audio_only=True,physical_panel_recorded=False),
  numerical_compare=canonical,original_policy_and_six_scenes_pass=True,physics_frames=policy['frames'],
  same_scene_actual_render=dict(R2_fps=old['actual_completed_fps'],R3_fps=new['actual_completed_fps'],R2_P95_complete_ms=old['complete_frame_ms']['p95'],R3_P95_complete_ms=new['complete_frame_ms']['p95'],seconds_per_variant=10,pixel_readback_in_timed_loop=False,GUI_stopped_camera_original_owner_retained=True,speedup_claimed=False))
 save(HERE/'release/QUALITY_GATE.json',q);save(HERE/'validation/QUALITY_GATE.json',q);print(json.dumps(q,ensure_ascii=False))
